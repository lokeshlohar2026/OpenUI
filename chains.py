import os
import json
import time
from pathlib import Path
from typing import AsyncGenerator, Optional, Dict, Any
import httpx
from dotenv import load_dotenv
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

load_dotenv()

PROMPT_FILE = Path(__file__).parent / "openui_prompt.txt"

# Model Configuration from Environment Variables (Exact models preserved)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").strip().lower()
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
GROQ_MAX_COMPLETION_TOKENS = int(os.getenv("GROQ_MAX_COMPLETION_TOKENS", "1024"))

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

OPENCODE_BASE_URL = os.getenv("OPENCODE_BASE_URL", "https://opencode.ai/zen/v1").rstrip("/")
OPENCODE_MODEL = os.getenv("OPENCODE_MODEL", "mimo-v2.5-free")


def nullable_env(name: str, default: str = "null") -> Optional[str]:
    value = os.getenv(name, default).strip()
    return None if value.lower() in {"", "null", "none"} else value


GROQ_REASONING_EFFORT = nullable_env("GROQ_REASONING_EFFORT")
OPENCODE_REASONING_EFFORT = nullable_env("OPENCODE_REASONING_EFFORT")


def load_system_prompt() -> str:
    """Dynamically read the latest compiled OpenUI prompt from openui_prompt.txt."""
    if PROMPT_FILE.exists():
        return PROMPT_FILE.read_text(encoding="utf-8")
    return "You are an AI financial assistant generating OpenUI declarative code."


async def stream_groq(prompt_text: str, query: str) -> AsyncGenerator[str, None]:
    """Streams response from Groq API (openai/gpt-oss-20b)."""
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        yield 'root = Column([TextContent("Error: GROQ_API_KEY is not set in environment.")])'
        return

    payload: Dict[str, Any] = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": prompt_text},
            {"role": "user", "content": query},
        ],
        "temperature": 1,
        "max_completion_tokens": GROQ_MAX_COMPLETION_TOKENS,
        "top_p": 1,
        "stream": True,
    }
    if GROQ_REASONING_EFFORT:
        payload["reasoning_effort"] = GROQ_REASONING_EFFORT

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST",
            f"{GROQ_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        ) as response:
            if response.status_code != 200:
                err_body = await response.aread()
                yield f'root = Column([TextContent("Groq API error {response.status_code}: {err_body.decode(errors="ignore")}")])'
                return

            try:
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except Exception:
                        continue
            except GeneratorExit:
                return


async def stream_gemini(prompt_text: str, query: str) -> AsyncGenerator[str, None]:
    """Streams response from Google Gemini API."""
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        yield 'root = Column([TextContent("Error: GEMINI_API_KEY is not set.")])'
        return

    client = genai.Client(api_key=gemini_key)
    response_stream = client.models.generate_content_stream(
        model=GEMINI_MODEL,
        contents=query,
        config=types.GenerateContentConfig(
            system_instruction=prompt_text,
            temperature=0.2,
        ),
    )
    for chunk in response_stream:
        if chunk.text:
            yield chunk.text


async def stream_opencode(prompt_text: str, query: str) -> AsyncGenerator[str, None]:
    """Streams response from OpenCode API."""
    api_key = os.getenv("OPENCODE_API_KEY", "")
    if not api_key:
        yield 'root = Column([TextContent("Error: OPENCODE_API_KEY is not set.")])'
        return

    payload: Dict[str, Any] = {
        "model": OPENCODE_MODEL,
        "messages": [
            {"role": "system", "content": prompt_text},
            {"role": "user", "content": query},
        ],
        "temperature": 0.2,
        "stream": True,
    }
    if OPENCODE_REASONING_EFFORT:
        payload["reasoning_effort"] = OPENCODE_REASONING_EFFORT

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST",
            f"{OPENCODE_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        ) as response:
            if response.status_code != 200:
                err_body = await response.aread()
                yield f'root = Column([TextContent("OpenCode API error {response.status_code}: {err_body.decode(errors="ignore")}")])'
                return

            try:
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except Exception:
                        continue
            except GeneratorExit:
                return


async def stream_openui_chain(user_query: str) -> AsyncGenerator[str, None]:
    """
    Main LangChain-compatible streaming entrypoint.
    Loads the system prompt and streams from the active LLM provider.
    """
    prompt = load_system_prompt()
    provider = LLM_PROVIDER

    if provider == "gemini":
        async for chunk in stream_gemini(prompt, user_query):
            yield chunk
    elif provider == "opencode":
        async for chunk in stream_opencode(prompt, user_query):
            yield chunk
    else:
        # Default: Groq
        async for chunk in stream_groq(prompt, user_query):
            yield chunk
