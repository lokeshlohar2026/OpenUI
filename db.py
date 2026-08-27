import os
import re
from contextlib import contextmanager
from typing import Optional, Tuple, List, Dict, Any
import psycopg2
from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL Connection Configuration (supports both POSTGRES_* and PG_*)
PG_HOST = os.getenv("POSTGRES_HOST") or os.getenv("PG_HOST", "127.0.0.1")
PG_PORT = int(os.getenv("POSTGRES_PORT") or os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("POSTGRES_DB") or os.getenv("PG_DB", "mf_saarthi_db")
PG_USER = os.getenv("POSTGRES_USER") or os.getenv("PG_USER", "postgres")
PG_PASS = os.getenv("POSTGRES_PASSWORD") or os.getenv("PG_PASS", "1234")

# Thread-safe connection pool for production efficiency
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
    """Context manager for acquiring and releasing a connection from the pool."""
    pool = get_pool()
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)


def find_fund(cur, q: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Multi-tier fuzzy matching algorithm to resolve a user query string into a precise (fund_id, fund_name).
    1. Exact phrase match
    2. Normalized cleaned name match
    3. Token-based AND matching (all tokens in name)
    4. AMC Prefix search fallback
    """
    cleaned = (
        re.sub(
            r"\b(growth|regular|direct|plan|fund|idcw|dividend|payout|reinvestment)\b",
            "",
            q,
            flags=re.I,
        )
        .strip()
        .lower()
    )
    tokens = [t for t in re.split(r"\s+", cleaned) if len(t) > 1]

    # Strategy 1: Exact phrase match
    cur.execute(
        "SELECT fund_id, fund_name FROM mfi360_funds WHERE fund_name ILIKE %s ORDER BY aum_cr DESC NULLS LAST LIMIT 1",
        (f"%{q.strip()}%",),
    )
    r = cur.fetchone()
    if r:
        return r[0], r[1]

    # Strategy 2: Normalized cleaned match
    if cleaned:
        cur.execute(
            "SELECT fund_id, fund_name FROM mfi360_funds WHERE fund_name ILIKE %s ORDER BY aum_cr DESC NULLS LAST LIMIT 1",
            (f"%{cleaned}%",),
        )
        r = cur.fetchone()
        if r:
            return r[0], r[1]

    # Strategy 3: All-token AND match
    if tokens:
        clauses = " AND ".join(["fund_name ILIKE %s"] * len(tokens))
        params = [f"%{t}%" for t in tokens]
        cur.execute(
            f"SELECT fund_id, fund_name FROM mfi360_funds WHERE {clauses} ORDER BY aum_cr DESC NULLS LAST LIMIT 1",
            params,
        )
        r = cur.fetchone()
        if r:
            return r[0], r[1]

    # Strategy 4: AMC fallback match
    first_tok = tokens[0] if tokens else q.strip().split()[0] if q.strip() else ""
    if first_tok:
        cur.execute(
            "SELECT fund_id, fund_name FROM mfi360_funds WHERE fund_name ILIKE %s ORDER BY aum_cr DESC NULLS LAST LIMIT 1",
            (f"%{first_tok}%",),
        )
        r = cur.fetchone()
        if r:
            return r[0], r[1]

    return None, None


# ── Data Access Functions ──────────────────────────────────────────────────


def get_portfolio_holdings(q: str, limit: int = 0) -> Dict[str, Any]:
    """Fetch real stock holdings and % of net assets from PostgreSQL."""
    if not q or not q.strip():
        return {"holdings": [], "fund_name": None, "fund_id": None}

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            fund_id, fund_name = find_fund(cur, q)
            if not fund_id:
                return {"holdings": [], "fund_name": None, "fund_id": None}

            cur.execute(
                "SELECT MAX(portfolio_date) FROM mfi360_fund_portfolio_holdings WHERE fund_id = %s",
                (fund_id,),
            )
            max_date_row = cur.fetchone()
            max_date = max_date_row[0] if max_date_row else None
            if not max_date:
                return {"holdings": [], "fund_name": fund_name, "fund_id": fund_id}

            query = """
                SELECT company_name, percentage_in_net_asset, portfolio_date
                FROM mfi360_fund_portfolio_holdings
                WHERE fund_id = %s AND portfolio_date = %s
                ORDER BY percentage_in_net_asset DESC
            """
            if limit and limit > 0:
                query += f" LIMIT {int(limit)}"

            cur.execute(query, (fund_id, max_date))
            holdings = [
                {
                    "company_name": row[0],
                    "percentage_in_net_asset": round(float(row[1]), 2) if row[1] is not None else 0,
                    "portfolio_date": row[2].isoformat() if hasattr(row[2], "isoformat") else str(row[2]),
                }
                for row in cur.fetchall()
            ]
            return {"holdings": holdings, "fund_name": fund_name, "fund_id": fund_id}


def get_market_cap_allocation(q: str) -> Dict[str, Any]:
    """Fetch Large Cap, Mid Cap, Small Cap allocation breakdown from PostgreSQL."""
    if not q or not q.strip():
        return {"allocation": [], "fund_name": None, "fund_id": None}

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            fund_id, fund_name = find_fund(cur, q)
            if not fund_id:
                return {"allocation": [], "fund_name": None, "fund_id": None}

            cur.execute(
                "SELECT MAX(portfolio_date) FROM mfi360_fund_portfolio_holdings WHERE fund_id = %s",
                (fund_id,),
            )
            max_date = cur.fetchone()[0]

            cur.execute(
                """
                SELECT market_cap_caption, SUM(percentage_in_net_asset)
                FROM mfi360_fund_portfolio_holdings
                WHERE fund_id = %s AND portfolio_date = %s AND market_cap_caption IS NOT NULL
                GROUP BY market_cap_caption
                ORDER BY SUM(percentage_in_net_asset) DESC
                """,
                (fund_id, max_date),
            )
            alloc = [
                {
                    "name": row[0] or "Other",
                    "value": round(float(row[1]), 2) if row[1] is not None else 0,
                }
                for row in cur.fetchall()
            ]
            return {"allocation": alloc, "fund_name": fund_name, "fund_id": fund_id}


def get_aum_history(q: str, limit: int = 24) -> Dict[str, Any]:
    """Fetch monthly AUM history for line charts from PostgreSQL."""
    if not q or not q.strip():
        return {"history": [], "fund_name": None, "fund_id": None}

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            fund_id, fund_name = find_fund(cur, q)
            if not fund_id:
                return {"history": [], "fund_name": None, "fund_id": None}

            cur.execute(
                """
                SELECT aum_date, aum_cr
                FROM mfi360_fund_aum_history
                WHERE fund_id = %s
                ORDER BY aum_date ASC
                LIMIT %s
                """,
                (fund_id, int(limit) if limit else 24),
            )
            history = [
                {
                    "date": row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0]),
                    "aum": round(float(row[1]), 2) if row[1] is not None else 0,
                }
                for row in cur.fetchall()
            ]
            return {"history": history, "fund_name": fund_name, "fund_id": fund_id}


def get_fund_overview(q: str) -> Dict[str, Any]:
    """Fetch fund meta information (AUM, Nature, Sub Nature, Riskometer, Managers)."""
    if not q or not q.strip():
        return {"overview": {}, "fund_name": None, "fund_id": None}

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            fund_id, fund_name = find_fund(cur, q)
            if not fund_id:
                return {"overview": {}, "fund_name": None, "fund_id": None}

            cur.execute(
                """
                SELECT fund_name, aum_cr, nature, sub_nature, riskometer, fund_manager
                FROM mfi360_funds
                WHERE fund_id = %s
                LIMIT 1
                """,
                (fund_id,),
            )
            row = cur.fetchone()
            if not row:
                return {"overview": {}, "fund_name": fund_name, "fund_id": fund_id}

            mgr = row[5]
            if isinstance(mgr, list):
                mgr_str = ", ".join(str(m) for m in mgr if m)
            elif mgr:
                mgr_str = str(mgr)
            else:
                mgr_str = "—"

            overview = {
                "fund_name": row[0] or fund_name,
                "aum_cr": f"₹{float(row[1]):,.0f} Cr" if row[1] is not None else "—",
                "nature": row[2] or "—",
                "sub_nature": row[3] or "—",
                "riskometer": row[4] or "—",
                "managers": mgr_str,
            }
            return {"overview": overview, "fund_name": fund_name, "fund_id": fund_id}
