import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from dotenv import load_dotenv

from chains import stream_openui_chain
from db import execute_safe_sql

load_dotenv()

app = FastAPI(
    title="MF Saarthi OpenUI Backend",
    version="2.0.0",
    description="Universal Dynamic SQL Engine for Generative OpenUI Interfaces.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "openui-backend",
        "mode": "universal-sql-engine",
        "tools_count": 1,
    }


# ── Universal Dynamic SQL Tool Endpoint ─────────────────────────────────────


def _clamp_rows(v) -> int:
    try:
        n = int(v)
    except Exception:
        n = 100
    return max(1, min(200, n))


@app.post("/api/tools/sql_query")
async def sql_query_post(request: Request):
    """Universal Dynamic SQL Execution endpoint called by OpenUI Query('sql_query', ...)"""
    import time
    from logger import log_db_query
    try:
        body = await request.json()
        query = (body.get("sql") or body.get("query") or "").strip()
        if not query:
            return JSONResponse(status_code=400, content={"rows": [], "error": "sql is required"})
        max_rows = _clamp_rows(body.get("max_rows", 100))
        t0 = time.perf_counter()
        res = execute_safe_sql(query, max_rows=max_rows)
        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        log_db_query(query, elapsed, len(res.get("rows", [])))
        return JSONResponse(content=res)
    except Exception as e:
        log_db_query(query if "query" in dir() else "?", 0, 0, error=str(e))
        return JSONResponse(status_code=500, content={"rows": [], "error": str(e)})


@app.get("/api/tools/sql_query")
async def sql_query_get(request: Request, sql: str = "", query: str = "", max_rows: int = 100):
    """GET variant of Universal Dynamic SQL execution."""
    import time
    from logger import log_db_query
    target_sql = (sql or query).strip()
    if not target_sql:
        return JSONResponse(status_code=400, content={"rows": [], "error": "sql is required"})
    try:
        t0 = time.perf_counter()
        res = execute_safe_sql(target_sql, max_rows=_clamp_rows(max_rows))
        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        log_db_query(target_sql, elapsed, len(res.get("rows", [])))
        return JSONResponse(content=res)
    except Exception as e:
        log_db_query(target_sql, 0, 0, error=str(e))
        return JSONResponse(status_code=500, content={"rows": [], "error": str(e)})


# ── Chat Streaming Gateway ──────────────────────────────────────────────────


@app.post("/api/v1/chat/stream")
async def chat_stream(request: Request):
    """
    Streaming endpoint called by OpenUI ChatPage.
    Accepts JSON body: { message: str } and streams openui-lang tokens.
    """
    try:
        body = await request.json()
        user_message = body.get("message", "").strip()
        session_id = body.get("session_id") or body.get("chat_id")
        if not user_message:
            return JSONResponse(status_code=400, content={"error": "message is required"})
        if len(user_message) > 2000:
            return JSONResponse(status_code=400, content={"error": "message too long (max 2000 chars)"})

        return StreamingResponse(
            stream_openui_chain(user_message, session_id=session_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


if __name__ == "__main__":
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8001"))
    print(f"Starting MF Saarthi Universal OpenUI Server on http://{host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=True)
