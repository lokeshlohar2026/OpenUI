import os
import json
import time
import uuid
import uvicorn
import psycopg2
import re
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
import httpx
from google import genai
from google.genai import types


load_dotenv()
app = FastAPI()
gemini_client = genai.Client()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# System prompt auto-generated from the TS component library (single source of truth).
# Regenerate with: npm run gen:prompt  (runs scripts/gen-prompt.mjs -> openui_prompt.txt)
SYSTEM_PROMPT = (Path(__file__).parent / "openui_prompt.txt").read_text(encoding="utf-8")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").strip().lower()
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
GROQ_MAX_COMPLETION_TOKENS = int(os.getenv("GROQ_MAX_COMPLETION_TOKENS", "1024"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
OPENCODE_BASE_URL = os.getenv("OPENCODE_BASE_URL", "https://opencode.ai/zen/v1").rstrip("/")
OPENCODE_MODEL = os.getenv("OPENCODE_MODEL", "mimo-v2.5-free")
OPENCODE_FREE_MODELS = {
    "deepseek-v4-flash-free",
    "mimo-v2.5-free",
    "hy3-free",
    "laguna-s-2.1-free",
    "nemotron-3-ultra-free",
    "nemotron-3.5-lightning-free",
    "big-pickle",
}


def nullable_env(name: str, default: str = "null"):
    value = os.getenv(name, default).strip()
    return None if value.lower() in {"", "null", "none"} else value


GROQ_REASONING_EFFORT = nullable_env("GROQ_REASONING_EFFORT")
OPENCODE_REASONING_EFFORT = nullable_env("OPENCODE_REASONING_EFFORT")


def log_event(tag: str, message: str, **data):
    payload = ""
    if data:
        payload = " " + json.dumps(data, default=str, ensure_ascii=True)
    print(f"[{time.strftime('%H:%M:%S')}] [{tag}] {message}{payload}", flush=True)


def sample_rows(rows, limit=3):
    if not isinstance(rows, list):
        return rows
    return rows[:limit]


def openui_error_response(message: str):
    safe = message.replace("\\", "\\\\").replace('"', '\\"').replace("\r", " ").replace("\n", " ")
    return f'root = Column([TextContent("{safe}")])'


def groq_payload(prompt_text: str, query: str):
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": prompt_text},
            {"role": "user", "content": query},
        ],
        "temperature": 1,
        "max_completion_tokens": GROQ_MAX_COMPLETION_TOKENS,
        "top_p": 1,
        "stream": True,
        "stop": None,
    }
    if GROQ_REASONING_EFFORT is not None:
        payload["reasoning_effort"] = GROQ_REASONING_EFFORT
    return payload


def extract_groq_delta(line: str):
    if not line.startswith("data: "):
        return ""
    data = line[len("data: ") :]
    if data == "[DONE]":
        return ""
    event = json.loads(data)
    return (event.get("choices") or [{}])[0].get("delta", {}).get("content", "")


def opencode_headers(api_key: str, model: str):
    _ = model
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def opencode_endpoint(model: str):
    _ = model
    return f"{OPENCODE_BASE_URL}/chat/completions"


def opencode_payload(model: str, prompt_text: str, query: str):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt_text},
            {"role": "user", "content": query},
        ],
        "temperature": 0.1,
        "stream": True,
    }
    if OPENCODE_REASONING_EFFORT is not None:
        payload["reasoning_effort"] = OPENCODE_REASONING_EFFORT
    return payload


def extract_opencode_delta(model: str, line: str):
    _ = model
    if not line.startswith("data: "):
        return ""
    data = line[len("data: ") :]
    if data == "[DONE]":
        return ""
    event = json.loads(data)
    return (event.get("choices") or [{}])[0].get("delta", {}).get("content", "")


def llm_request_config(prompt_text: str, query: str):
    if LLM_PROVIDER == "groq":
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not configured")
        return {
            "provider": "groq",
            "model": GROQ_MODEL,
            "endpoint": f"{GROQ_BASE_URL}/chat/completions",
            "headers": {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            "payload": groq_payload(prompt_text, query),
            "extract": extract_groq_delta,
            "quota_message": "Groq quota or rate limit hit. Please retry later or switch model.",
        }
    if LLM_PROVIDER == "opencode":
        if OPENCODE_MODEL not in OPENCODE_FREE_MODELS:
            raise RuntimeError(f"OpenCode model '{OPENCODE_MODEL}' is not in the free model list.")
        api_key = os.getenv("OPENCODE_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENCODE_API_KEY is not configured")
        return {
            "provider": "opencode",
            "model": OPENCODE_MODEL,
            "endpoint": opencode_endpoint(OPENCODE_MODEL),
            "headers": opencode_headers(api_key, OPENCODE_MODEL),
            "payload": opencode_payload(OPENCODE_MODEL, prompt_text, query),
            "extract": lambda line: extract_opencode_delta(OPENCODE_MODEL, line),
            "quota_message": "OpenCode quota or rate limit hit. Please retry later or switch model.",
        }
    if LLM_PROVIDER == "gemini":
        if not os.getenv("GEMINI_API_KEY", "").strip():
            raise RuntimeError("GEMINI_API_KEY is not configured")
        return {
            "provider": "gemini",
            "model": GEMINI_MODEL,
            "quota_message": "Gemini quota or rate limit hit. Please retry later or switch model.",
        }
    raise RuntimeError(f"Unsupported LLM_PROVIDER '{LLM_PROVIDER}'. Use 'groq', 'opencode', or 'gemini'.")

# -- Postgres (dynamic holdings for any fund/AMC, not just Nippon) --
PG_CFG = dict(
    host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
    port=int(os.getenv("POSTGRES_PORT", "5432")),
    dbname=os.getenv("POSTGRES_DB", "mf_saarthi_db"),
    user=os.getenv("POSTGRES_USER", "mf_saarthi_user"),
    password=os.getenv("POSTGRES_PASSWORD", "MFSaarthi2026"),
)

def pg_conn():
    return psycopg2.connect(**PG_CFG)



def find_fund(cur, q: str):
    """Find fund_id and fund_name using substring match on fund name or AMC name."""
    log_event("db:find_fund", "start", q=q)
    clean_q = q.strip()
    tokens = [t for t in re.split(r"\s+", clean_q) if len(t) >= 2]
    compact_q = re.sub(r"[^a-z0-9]", "", clean_q.lower())

    lookups = [("exact phrase", "fund_name ILIKE %s", (f"%{clean_q}%",))]
    if compact_q:
        lookups.append(
            (
                "normalized phrase",
                "regexp_replace(lower(fund_name), '[^a-z0-9]', '', 'g') LIKE %s",
                (f"%{compact_q}%",),
            )
        )
    if len(tokens) > 1:
        lookups.append(
            (
                "all tokens",
                " AND ".join(["fund_name ILIKE %s"] * len(tokens)),
                tuple(f"%{t}%" for t in tokens),
            )
        )

    for label, where_sql, params in lookups:
        log_event("db:find_fund", "fund lookup", strategy=label, params=params)
        cur.execute(
            f"SELECT fund_id, fund_name FROM mfi360_funds WHERE {where_sql} ORDER BY aum_cr DESC NULLS LAST LIMIT 1",
            params,
        )
        row = cur.fetchone()
        if row:
            log_event("db:find_fund", "matched fund", strategy=label, fund_id=row[0], fund_name=row[1])
            return row[0], row[1]

    amc_patterns = [f"%{clean_q}%"]
    if len(tokens) == 1:
        amc_patterns.append(f"%{tokens[0]}%")
    for pattern in amc_patterns:
        log_event("db:find_fund", "amc lookup", pattern=pattern)
        cur.execute("SELECT mf_id FROM mfi360_amcs WHERE name ILIKE %s LIMIT 1", (pattern,))
        amc = cur.fetchone()
        if not amc:
            continue
        cur.execute(
            "SELECT fund_id, fund_name FROM mfi360_funds WHERE mf_id=%s ORDER BY aum_cr DESC NULLS LAST LIMIT 1",
            (amc[0],),
        )
        row = cur.fetchone()
        if row:
            log_event("db:find_fund", "matched amc fund", mf_id=amc[0], fund_id=row[0], fund_name=row[1])
            return row[0], row[1]

    if len(tokens) == 1:
        pattern = f"%{tokens[0]}%"
        log_event("db:find_fund", "single-token fallback", pattern=pattern)
        cur.execute(
            "SELECT fund_id, fund_name FROM mfi360_funds WHERE fund_name ILIKE %s ORDER BY aum_cr DESC NULLS LAST LIMIT 1",
            (pattern,),
        )
        row = cur.fetchone()
        if row:
            log_event("db:find_fund", "matched single token", fund_id=row[0], fund_name=row[1])
            return row[0], row[1]

    log_event("db:find_fund", "no match", q=q)
    return None, None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/tools/portfolio_holdings")
def portfolio_holdings(q: str = "", limit: int = 0):
    """Predefined SQL: returns portfolio holdings ordered by % net asset."""
    log_event("db:portfolio_holdings", "request", q=q, limit=limit)
    if not q.strip():
        log_event("db:portfolio_holdings", "empty q")
        return {"holdings": []}
    try:
        conn = pg_conn()
        cur = conn.cursor()
        fund_id, fund_name = find_fund(cur, q)
        if not fund_id:
            conn.close()
            log_event("db:portfolio_holdings", "no fund", q=q)
            return {"holdings": [], "fund_name": None, "note": f"No fund/AMC matching '{q}'"}

        log_event("db:portfolio_holdings", "max date query", fund_id=fund_id)
        cur.execute("SELECT MAX(portfolio_date) FROM mfi360_fund_portfolio_holdings WHERE fund_id=%s", (fund_id,))
        max_date = cur.fetchone()[0]
        if not max_date:
            conn.close()
            log_event("db:portfolio_holdings", "no portfolio date", fund_id=fund_id, fund_name=fund_name)
            return {"holdings": [], "fund_name": fund_name, "fund_id": fund_id}

        query = """
            SELECT company_name, percentage_in_net_asset, portfolio_date
            FROM mfi360_fund_portfolio_holdings
            WHERE fund_id=%s AND portfolio_date=%s
            ORDER BY percentage_in_net_asset DESC
        """
        if limit and limit > 0:
            query += f" LIMIT {limit}"

        log_event("db:portfolio_holdings", "holdings query", fund_id=fund_id, fund_name=fund_name, portfolio_date=max_date, limit=limit)
        cur.execute(query, (fund_id, max_date))
        holdings = [
            {
                "company_name": r[0],
                "percentage_in_net_asset": round(float(r[1]), 2) if r[1] is not None else 0,
                "portfolio_date": r[2].isoformat(),
            }
            for r in cur.fetchall()
        ]
        conn.close()
        log_event("db:portfolio_holdings", "response", rows=len(holdings), sample=sample_rows(holdings))
        return {"holdings": holdings, "fund_name": fund_name, "fund_id": fund_id, "portfolio_date": max_date.isoformat()}
    except Exception as e:
        log_event("db:portfolio_holdings", "error", error=str(e))
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/tools/market_cap_allocation")
def market_cap_allocation(q: str = ""):
    """Predefined SQL: returns Market Cap breakdown (Large Cap, Mid Cap, Small Cap, Other)."""
    log_event("db:market_cap_allocation", "request", q=q)
    if not q.strip():
        log_event("db:market_cap_allocation", "empty q")
        return {"allocation": []}
    try:
        conn = pg_conn()
        cur = conn.cursor()
        fund_id, fund_name = find_fund(cur, q)
        if not fund_id:
            conn.close()
            log_event("db:market_cap_allocation", "no fund", q=q)
            return {"allocation": [], "fund_name": None}

        log_event("db:market_cap_allocation", "max date query", fund_id=fund_id)
        cur.execute("SELECT MAX(portfolio_date) FROM mfi360_fund_portfolio_holdings WHERE fund_id=%s", (fund_id,))
        max_date = cur.fetchone()[0]
        if not max_date:
            conn.close()
            log_event("db:market_cap_allocation", "no portfolio date", fund_id=fund_id, fund_name=fund_name)
            return {"allocation": [], "fund_name": fund_name}

        log_event("db:market_cap_allocation", "allocation query", fund_id=fund_id, fund_name=fund_name, portfolio_date=max_date)
        cur.execute(
            """SELECT COALESCE(market_cap_caption, 'Other/Cash') as name, ROUND(SUM(percentage_in_net_asset), 2) as value
               FROM mfi360_fund_portfolio_holdings
               WHERE fund_id=%s AND portfolio_date=%s
               GROUP BY COALESCE(market_cap_caption, 'Other/Cash')
               ORDER BY value DESC""",
            (fund_id, max_date),
        )
        allocation = [{"name": r[0], "value": float(r[1]) if r[1] is not None else 0} for r in cur.fetchall()]
        conn.close()
        log_event("db:market_cap_allocation", "response", rows=len(allocation), sample=sample_rows(allocation))
        return {"allocation": allocation, "fund_name": fund_name}
    except Exception as e:
        log_event("db:market_cap_allocation", "error", error=str(e))
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/tools/aum_history")
def aum_history(q: str = "", limit: int = 24):
    """Predefined SQL: returns historical monthly AUM in ₹ Cr for growth charts."""
    log_event("db:aum_history", "request", q=q, limit=limit)
    if not q.strip():
        log_event("db:aum_history", "empty q")
        return {"history": []}
    try:
        conn = pg_conn()
        cur = conn.cursor()
        fund_id, fund_name = find_fund(cur, q)
        if not fund_id:
            conn.close()
            log_event("db:aum_history", "no fund", q=q)
            return {"history": [], "fund_name": None}

        log_event("db:aum_history", "history query", fund_id=fund_id, fund_name=fund_name, limit=limit)
        cur.execute(
            """SELECT aum_date::text, aum_cr
               FROM (
                   SELECT aum_date, aum_cr
                   FROM mfi360_fund_aum_history
                   WHERE fund_id=%s
                   ORDER BY aum_date DESC
                   LIMIT %s
               ) sub
               ORDER BY aum_date ASC""",
            (fund_id, limit),
        )
        history = [
            {"date": r[0], "aum": round(float(r[1]), 1) if r[1] is not None else 0}
            for r in cur.fetchall()
        ]
        conn.close()
        log_event("db:aum_history", "response", rows=len(history), sample=sample_rows(history))
        return {"history": history, "fund_name": fund_name}
    except Exception as e:
        log_event("db:aum_history", "error", error=str(e))
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/tools/fund_overview")
def fund_overview(q: str = ""):
    """Predefined SQL: returns fund meta details (AUM, Category, Riskometer, Fund Managers)."""
    log_event("db:fund_overview", "request", q=q)
    if not q.strip():
        log_event("db:fund_overview", "empty q")
        return {"overview": {}}
    try:
        conn = pg_conn()
        cur = conn.cursor()
        fund_id, fund_name = find_fund(cur, q)
        if not fund_id:
            conn.close()
            log_event("db:fund_overview", "no fund", q=q)
            return {"overview": {}, "fund_name": None}

        log_event("db:fund_overview", "overview query", fund_id=fund_id, fund_name=fund_name)
        cur.execute(
            """SELECT fund_name, aum_cr, nature, sub_nature, riskometer, array_to_string(fund_manager, ', ')
               FROM mfi360_funds
               WHERE fund_id=%s""",
            (fund_id,),
        )
        row = cur.fetchone()
        conn.close()
        if not row:
            log_event("db:fund_overview", "no row", fund_id=fund_id)
            return {"overview": {}}
        response = {
            "overview": {
                "fund_name": row[0],
                "aum_cr": f"₹{round(float(row[1]), 1):,} Cr" if row[1] is not None else "N/A",
                "nature": row[2] or "N/A",
                "sub_nature": row[3] or "N/A",
                "riskometer": row[4] or "N/A",
                "managers": row[5] or "N/A",
            }
        }
        log_event("db:fund_overview", "response", overview=response["overview"])
        return response
    except Exception as e:
        log_event("db:fund_overview", "error", error=str(e))
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/v1/chat/stream")
async def stream(req: Request):
    body = await req.json()
    query = body.get("message", "")
    request_id = str(uuid.uuid4())[:8]
    log_event(f"chat:{request_id}", "request received", query=query, body=body)

    def gen():
        final_text = ""
        started = time.perf_counter()
        try:
            prompt_text = (Path(__file__).parent / "openui_prompt.txt").read_text(encoding="utf-8")
            llm = llm_request_config(prompt_text, query)
            provider_tag = f"{llm['provider']}:{request_id}"
            log_event(
                provider_tag,
                "start",
                model=llm["model"],
                endpoint=llm.get("endpoint", "google-genai-sdk"),
                prompt_chars=len(prompt_text),
                query=query,
            )
            first_chunk_at = None
            if llm["provider"] == "gemini":
                stream = gemini_client.models.generate_content_stream(
                    model=llm["model"],
                    contents=query,
                    config=types.GenerateContentConfig(
                        system_instruction=prompt_text,
                        temperature=0.1,
                    ),
                )
                for chunk in stream:
                    chunk_text = chunk.text or ""
                    if chunk_text:
                        if first_chunk_at is None:
                            first_chunk_at = time.perf_counter()
                            log_event(
                                provider_tag,
                                "first chunk",
                                elapsed_ms=round((first_chunk_at - started) * 1000),
                            )
                        final_text += chunk_text
                        log_event(provider_tag, "chunk", chars=len(chunk_text), text=chunk_text)
                        yield chunk_text
            else:
                with httpx.Client(timeout=300.0) as client:
                    with client.stream(
                        "POST",
                        llm["endpoint"],
                        headers=llm["headers"],
                        json=llm["payload"],
                    ) as response:
                        response.raise_for_status()
                        for line in response.iter_lines():
                            chunk_text = llm["extract"](line)
                            if chunk_text:
                                if first_chunk_at is None:
                                    first_chunk_at = time.perf_counter()
                                    log_event(
                                        provider_tag,
                                        "first chunk",
                                        elapsed_ms=round((first_chunk_at - started) * 1000),
                                    )
                                final_text += chunk_text
                                log_event(provider_tag, "chunk", chars=len(chunk_text), text=chunk_text)
                                yield chunk_text
            log_event(
                provider_tag,
                "complete",
                elapsed_ms=round((time.perf_counter() - started) * 1000),
                chars=len(final_text),
                text=final_text,
            )
        except Exception as e:
            err = str(e)
            provider = LLM_PROVIDER if LLM_PROVIDER in {"groq", "opencode", "gemini"} else "llm"
            log_event(f"{provider}:{request_id}", "error", error=err)
            if "429" in err:
                if provider == "opencode":
                    fallback = openui_error_response("OpenCode quota or rate limit hit. Please retry later or switch model.")
                elif provider == "gemini":
                    fallback = openui_error_response("Gemini quota or rate limit hit. Please retry later or switch model.")
                else:
                    fallback = openui_error_response("Groq quota or rate limit hit. Please retry later or switch model.")
            else:
                fallback = openui_error_response(f"Error: {err[:300]}")
            log_event(f"{provider}:{request_id}", "fallback openui", text=fallback)
            yield fallback

    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
