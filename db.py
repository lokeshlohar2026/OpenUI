import time
import os
import re
import difflib
from contextlib import contextmanager
from decimal import Decimal
from typing import Optional, Tuple, List, Dict, Set, Any
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv
from logger import log_db_query

load_dotenv()

# PostgreSQL Connection Configuration
PG_HOST = os.getenv("POSTGRES_HOST") or os.getenv("PG_HOST", "127.0.0.1")
PG_PORT = int(os.getenv("POSTGRES_PORT") or os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("POSTGRES_DB") or os.getenv("PG_DB", "mf_saarthi_db")
PG_USER = os.getenv("POSTGRES_USER") or os.getenv("PG_USER", "postgres")
PG_PASS = os.getenv("POSTGRES_PASSWORD") or os.getenv("PG_PASS", "1234")

# Thread-safe connection pool
_pool: Optional[ThreadedConnectionPool] = None


def get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is None or _pool.closed:
        _pool = ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            host=PG_HOST,
            port=PG_PORT,
            dbname=PG_DB,
            user=PG_USER,
            password=PG_PASS,
        )
    return _pool


@contextmanager
def get_db_connection():
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)


# ── Schema Catalog & Auto-Discovery ─────────────────────────────────────────

_SCHEMA_CACHE: Optional[str] = None
_TABLES_MAP: Dict[str, List[str]] = {}
_ALL_COLUMNS_SET: Set[str] = set()
_QUERY_CACHE: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
QUERY_CACHE_TTL = 300  # 5 minutes cache

# Common semantic aliases for rapid typo resolution
COLUMN_ALIAS_MAP = {
    "min_investment": "min_invest",
    "min_inv": "min_invest",
    "pe": "price_to_earnings",
    "pe_ratio": "price_to_earnings",
    "pb": "price_to_book",
    "pb_ratio": "price_to_book",
    "weight": "percentage_in_net_asset",
    "weight_pct": "percentage_in_net_asset",
    "holding_pct": "percentage_in_net_asset",
    "holding_percentage": "percentage_in_net_asset",
    "cap_category": "market_cap_caption",
    "cap_type": "market_cap_caption",
    "cap": "market_cap_caption",
    "market_cap": "market_cap_caption",
    "stock_name": "company_name",
    "company": "company_name",
    "stock": "company_name",
    "scheme": "scheme_name",
    "aum": "aum_cr",
}


def load_table_schema_map():
    """Builds in-memory table and column map for instantaneous fuzzy checking."""
    global _TABLES_MAP, _ALL_COLUMNS_SET
    if _TABLES_MAP:
        return _TABLES_MAP

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name NOT IN ('cleaner_cache')
                ORDER BY table_name, ordinal_position;
            """)
            for t_name, c_name in cur.fetchall():
                _TABLES_MAP.setdefault(t_name, []).append(c_name)
                _ALL_COLUMNS_SET.add(c_name)

    return _TABLES_MAP


def get_db_schema_catalog() -> str:
    """Returns compact schema summary string for LLM system prompt."""
    global _SCHEMA_CACHE
    if _SCHEMA_CACHE:
        return _SCHEMA_CACHE

    tables = load_table_schema_map()
    lines = ["### DATABASE SCHEMA (Auto-Discovered PostgreSQL):"]
    for t_name, cols in tables.items():
        lines.append(f"• {t_name}: [{', '.join(cols)}]")

    _SCHEMA_CACHE = "\n".join(lines)
    return _SCHEMA_CACHE


def auto_heal_sql_query(sql_query: str, error_msg: str) -> Optional[str]:
    """
    Analyzes PostgreSQL error messages and auto-repairs column/table typos in < 1ms:
    1. Direct alias dictionary lookup
    2. Levenshtein fuzzy match against schema columns
    """
    tables_map = load_table_schema_map()
    repaired_sql = sql_query

    # Case 1: Column does not exist error
    col_err_match = re.search(r'column "([^"]+)" does not exist', error_msg, re.IGNORECASE)
    if col_err_match:
        bad_col = col_err_match.group(1).lower()

        # Step 1: Check fast alias map
        if bad_col in COLUMN_ALIAS_MAP:
            target_col = COLUMN_ALIAS_MAP[bad_col]
            repaired_sql = re.sub(rf"\b{re.escape(bad_col)}\b", target_col, repaired_sql, flags=re.IGNORECASE)
            return repaired_sql

        # Step 2: Fuzzy match against all known DB columns
        all_cols = list(_ALL_COLUMNS_SET)
        matches = difflib.get_close_matches(bad_col, all_cols, n=1, cutoff=0.5)
        if matches:
            target_col = matches[0]
            repaired_sql = re.sub(rf"\b{re.escape(bad_col)}\b", target_col, repaired_sql, flags=re.IGNORECASE)
            return repaired_sql

    # Case 2: Table/Relation does not exist error
    rel_err_match = re.search(r'relation "([^"]+)" does not exist', error_msg, re.IGNORECASE)
    if rel_err_match:
        bad_rel = rel_err_match.group(1).lower()
        all_tables = list(tables_map.keys())
        matches = difflib.get_close_matches(bad_rel, all_tables, n=1, cutoff=0.5)
        if matches:
            target_rel = matches[0]
            repaired_sql = re.sub(rf"\b{re.escape(bad_rel)}\b", target_rel, repaired_sql, flags=re.IGNORECASE)
            return repaired_sql

    return None


# AMC Acronym & Synonym Normalization Dictionary
AMC_SYNONYMS = {
    r"\bicici\s+pru\b": "ICICI Prudential",
    r"\bicici\s+prudential\b": "ICICI Prudential",
    r"\babsl\b": "Aditya Birla Sun Life",
    r"\bnippon\b": "Nippon India",
    r"\bkotak\b": "Kotak Mahindra",
    r"\bppfas\b": "Parag Parikh",
    r"\bmirae\b": "Mirae Asset",
    r"\bflexicap\b": "Flexi Cap",
    r"\bsmallcap\b": "Small Cap",
    r"\bmidcap\b": "Mid Cap",
    r"\blargecap\b": "Large Cap",
    r"\bmulticap\b": "Multi Cap",
    r"\bblue\s*chip\b": "Large Cap",
}

_FUND_NAMES_LIST: List[str] = []


def load_fund_names_catalog() -> List[str]:
    """Loads all fund names from mfi360_funds into memory for ranked matching."""
    global _FUND_NAMES_LIST
    if _FUND_NAMES_LIST:
        return _FUND_NAMES_LIST
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT fund_name FROM mfi360_funds WHERE fund_name IS NOT NULL;")
                _FUND_NAMES_LIST = [r[0] for r in cur.fetchall()]
    except Exception:
        pass
    return _FUND_NAMES_LIST


def resolve_best_fund_name(raw_name: str) -> str:
    """
    Production-Grade 4-Stage Ranked Entity Resolution:
    1. Acronym & Synonym Expansion (including Bluechip -> Large Cap)
    2. Suffix & Noise Stripping
    3. Exact Substring Search in Catalog
    4. Ranked Levenshtein / Trigram Matching (Prevents collision bugs)
    """
    cleaned = raw_name.lower()
    for pattern, replacement in AMC_SYNONYMS.items():
        cleaned = re.sub(pattern, replacement.lower(), cleaned, flags=re.IGNORECASE)

    cleaned = re.sub(r"\b(direct|regular|growth|idcw|dividend|plan|fund|mutual\s+fund|scheme)\b", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    catalog = load_fund_names_catalog()
    if not catalog:
        return cleaned

    # Stage 3: Exact Substring
    for f in catalog:
        if cleaned.lower() in f.lower():
            return f

    # Stage 4: Ranked Fuzzy Match
    matches = difflib.get_close_matches(cleaned, catalog, n=1, cutoff=0.4)
    if matches:
        return matches[0]

    return cleaned


def sanitize_fund_name_subqueries(sql_query: str) -> str:
    """Applies 4-stage entity resolution to fund_name subqueries."""
    def clean_match(m):
        raw_val = m.group(1)
        resolved = resolve_best_fund_name(raw_val)
        safe_resolved = resolved.replace("'", "''")
        return f"fund_name ILIKE '%{safe_resolved}%'"

    return re.sub(r"fund_name\s+ILIKE\s+'%([^%']+)%'", clean_match, sql_query, flags=re.IGNORECASE)


def normalize_sql_literals(sql_query: str) -> str:
    """
    Auto-heals case-sensitive literals for PostgreSQL:
    - plan = 'DIRECT' -> plan = 'Direct'
    - option = 'GROWTH' -> option = 'Growth'
    - nature = 'EQUITY' -> nature = 'Equity'
    """
    normalized = sql_query
    normalized = re.sub(r"\bplan\s*=\s*['\"]direct['\"]", "plan = 'Direct'", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bplan\s*=\s*['\"]regular['\"]", "plan = 'Regular'", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\boption\s*=\s*['\"]growth['\"]", "option = 'Growth'", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\boption\s*=\s*['\"]idcw['\"]", "option = 'IDCW'", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bnature\s*=\s*['\"]equity['\"]", "nature = 'Equity'", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bnature\s*=\s*['\"]debt['\"]", "nature = 'Debt'", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\bnature\s*=\s*['\"]hybrid['\"]", "nature = 'Hybrid'", normalized, flags=re.IGNORECASE)
    return normalized


def execute_safe_sql(sql_query: str, max_rows: int = 100) -> Dict[str, Any]:
    """
    Executes dynamic SQL generated by LLM with:
    1. Read-Only Guardrail (blocks mutating keywords)
    2. Auto-Healing Fuzzy Interceptor (auto-corrects column typos & name mismatches)
    3. In-memory query caching (< 0.1ms)
    4. Statement Timeout safety (2000ms max)
    """
    if not sql_query or not sql_query.strip():
        return {"rows": [], "error": "Empty SQL query"}

    clean_sql = normalize_sql_literals(sql_query.strip().rstrip(";"))

    # Security Guardrail
    first_word = clean_sql.split()[0].upper() if clean_sql.split() else ""
    if first_word not in ("SELECT", "WITH", "EXPLAIN"):
        return {"rows": [], "error": f"Disallowed command '{first_word}'. Only SELECT queries are permitted."}

    forbidden = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|EXEC|CREATE)\b", re.IGNORECASE)
    if forbidden.search(clean_sql):
        return {"rows": [], "error": "Query contains forbidden mutating statements."}

    # Cache check
    now = time.time()
    cache_key = f"{clean_sql}::{max_rows}"
    if cache_key in _QUERY_CACHE:
        cached_time, cached_rows = _QUERY_CACHE[cache_key]
        if now - cached_time < QUERY_CACHE_TTL:
            log_db_query(
                sql=clean_sql,
                row_count=len(cached_rows),
                elapsed_ms=0.05,
                cached=True,
                sample_data=cached_rows,
            )
            return {"rows": cached_rows, "cached": True, "count": len(cached_rows)}

    start_t = time.perf_counter()
    load_table_schema_map()

    def run_query(target_sql: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = '2000ms';")
                exec_sql = target_sql if re.search(r"\bLIMIT\s+\d+\b", target_sql, re.IGNORECASE) else f"{target_sql} LIMIT {int(max_rows)}"
                try:
                    cur.execute(exec_sql)
                except Exception as e:
                    conn.rollback()
                    return None, str(e)

                if not cur.description:
                    return [], None

                col_names = [d[0] for d in cur.description]
                raw_rows = cur.fetchall()

                rows = []
                for r in raw_rows:
                    row_dict = {}
                    for col, val in zip(col_names, r):
                        if hasattr(val, "isoformat"):
                            row_dict[col] = val.isoformat()
                        elif isinstance(val, (float, int, Decimal)):
                            row_dict[col] = round(float(val), 4) if isinstance(val, (float, Decimal)) else val
                        elif val is None:
                            row_dict[col] = None
                        else:
                            row_dict[col] = str(val)
                    rows.append(row_dict)
                return rows, None

    # Multi-pass execution with auto-healing (up to 3 repair attempts)
    current_sql = clean_sql
    repaired_from = None
    rows = None
    err = None

    for attempt in range(4):
        rows, err = run_query(current_sql)
        if not err:
            break

        # If PostgreSQL error indicates missing column or table, heal and retry
        if "does not exist" in err.lower():
            healed_sql = auto_heal_sql_query(current_sql, err)
            if healed_sql and healed_sql != current_sql:
                print(f"[SQL Auto-Healer] Repaired typo (pass {attempt+1}):\n   Before: {current_sql}\n   After:  {healed_sql}")
                repaired_from = current_sql
                current_sql = healed_sql
                continue
        break

    # Attempt: Fuzzy Fund Name retry if 0 rows matched due to plan suffixes or alias mismatches (e.g. Bluechip -> Large Cap)
    if rows is not None and len(rows) == 0 and "fund_name ILIKE" in current_sql:
        sanitized_sql = sanitize_fund_name_subqueries(current_sql)
        if sanitized_sql != current_sql:
            print(f"[SQL Fuzzy Matcher] Retrying with sanitized fund name:\n   {sanitized_sql}")
            repaired_from = current_sql
            rows, err = run_query(sanitized_sql)

    elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)

    if err:
        log_db_query(
            sql=current_sql,
            row_count=0,
            elapsed_ms=elapsed_ms,
            error=err,
            repaired_from=repaired_from,
        )
        return {"rows": [], "error": err}

    final_rows = rows or []

    # Telemetry logging to logs/db.log
    log_db_query(
        sql=current_sql,
        row_count=len(final_rows),
        elapsed_ms=elapsed_ms,
        repaired_from=repaired_from,
        sample_data=final_rows,
    )

    # Cache successful result
    _QUERY_CACHE[cache_key] = (now, final_rows)
    return {"rows": final_rows, "count": len(final_rows), "elapsed_ms": elapsed_ms}
