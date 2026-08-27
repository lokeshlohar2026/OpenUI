import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from dotenv import load_dotenv

from chains import stream_openui_chain
from db import (
    get_portfolio_holdings,
    get_market_cap_allocation,
    get_aum_history,
    get_fund_overview,
)

load_dotenv()

app = FastAPI(
    title="MF Saarthi OpenUI Backend",
    version="1.0.0",
    description="Production-grade LangChain-compatible backend with PostgreSQL database tools for generative OpenUI interfaces.",
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
    return {"status": "ok", "service": "openui-backend"}


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
        if not user_message:
            return JSONResponse(status_code=400, content={"error": "message is required"})

        return StreamingResponse(
            stream_openui_chain(user_message),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ── Predefined SQL Tool Endpoints ──────────────────────────────────────────


@app.get("/api/tools/portfolio_holdings")
def portfolio_holdings(q: str = "", limit: int = 0):
    """Fetch top stock holdings from PostgreSQL."""
    try:
        data = get_portfolio_holdings(q=q, limit=limit)
        return JSONResponse(content=data)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/tools/market_cap_allocation")
def market_cap_allocation(q: str = ""):
    """Fetch Large / Mid / Small Cap allocation breakdown from PostgreSQL."""
    try:
        data = get_market_cap_allocation(q=q)
        return JSONResponse(content=data)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/tools/aum_history")
def aum_history(q: str = "", limit: int = 24):
    """Fetch monthly AUM history for line charts from PostgreSQL."""
    try:
        data = get_aum_history(q=q, limit=limit)
        return JSONResponse(content=data)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/tools/fund_overview")
def fund_overview(q: str = ""):
    """Fetch fund overview metadata (AUM, Category, Riskometer, Managers)."""
    try:
        data = get_fund_overview(q=q)
        return JSONResponse(content=data)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


if __name__ == "__main__":
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8000"))
    print(f"🚀 Starting MF Saarthi OpenUI Server on http://{host}:{port}")
    uvicorn.run("main:app", host=host, port=port, reload=True)
