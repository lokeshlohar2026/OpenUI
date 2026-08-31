import os
import re
import json
import time
import asyncio
from pathlib import Path
from typing import AsyncGenerator, Optional, Dict, Any
import httpx
from dotenv import load_dotenv
from logger import log_llm_interaction

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

load_dotenv()

PROMPT_FILE = Path(__file__).parent / "openui_prompt.txt"

# Model Configuration from Environment Variables
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1").rstrip("/")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_MAX_COMPLETION_TOKENS = int(os.getenv("GROQ_MAX_COMPLETION_TOKENS", "1024"))

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

OPENCODE_BASE_URL = (os.getenv("OPENCODE_BASE_URL") or os.getenv("OPENCODE_ZEN_GO_BASE_URL") or "https://opencode.ai/zen/go/v1").rstrip("/")
OPENCODE_MODEL = os.getenv("OPENCODE_MODEL", "mimo-v2.5-pro")


def nullable_env(name: str, default: str = "null") -> Optional[str]:
    value = os.getenv(name, default).strip()
    return None if value.lower() in {"", "null", "none"} else value


GROQ_REASONING_EFFORT = nullable_env("GROQ_REASONING_EFFORT")
OPENCODE_REASONING_EFFORT = nullable_env("OPENCODE_REASONING_EFFORT")

PROMPTS_DIR = Path(__file__).parent / "prompts"
PROMPT_FILE = Path(__file__).parent / "openui_prompt.txt"

def load_system_prompt() -> str:
    """
    Dynamically loads the modular system prompt files from the /prompts directory:
    - 01_library_ast.txt       (Component definitions from OpenUI library)
    - 02_db_schema.txt         (PostgreSQL database schema reference)
    - 03_domain_skills.txt     (Financial SQL recipes & visual guidelines)
    - 04_syntactic_rules.txt   (AST ordering, component palette & constraints)
    
    Falls back to openui_prompt.txt if the /prompts directory is not present.
    """
    if PROMPTS_DIR.exists() and PROMPTS_DIR.is_dir():
        prompt_parts = []
        for file in sorted(PROMPTS_DIR.glob("*.txt")):
            text = file.read_text(encoding="utf-8").strip()
            if text:
                prompt_parts.append(text)
        if prompt_parts:
            return "\n\n".join(prompt_parts)

    if PROMPT_FILE.exists():
        return PROMPT_FILE.read_text(encoding="utf-8").strip()

    return "You are an AI financial assistant generating OpenUI declarative code."


async def _stream_openai_compatible(base_url: str, api_key: str, payload: Dict[str, Any], err_prefix: str) -> AsyncGenerator[str, None]:
    """Shared helper for OpenAI-compatible streaming (Groq, OpenCode)."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    max_retries = 3
    for attempt in range(max_retries):
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", f"{base_url}/chat/completions", headers=headers, json=payload) as response:
                if response.status_code == 429 and attempt < max_retries - 1:
                    await asyncio.sleep(2.5 * (1 if err_prefix == "Groq" else 1))
                    continue
                if response.status_code != 200:
                    err_body = await response.aread()
                    yield f'root = Column([TextContent("{err_prefix} API error {response.status_code}: {err_body.decode(errors="ignore")}")])'
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
                            content = delta.get("content") or delta.get("content", "")
                            if content:
                                yield content
                        except Exception:
                            continue
                    return
                except GeneratorExit:
                    return


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

    async for chunk in _stream_openai_compatible(GROQ_BASE_URL, api_key, payload, "Groq"):
        yield chunk


async def stream_gemini(prompt_text: str, query: str) -> AsyncGenerator[str, None]:
    """Streams response from Google Gemini API via official SDK or high-speed httpx SSE."""
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        yield 'root = Column([TextContent("Error: GEMINI_API_KEY is not set.")])'
        return

    if genai is not None:
        try:
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
            return
        except Exception:
            pass

    # High-speed HTTP REST fallback with retry
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:streamGenerateContent?alt=sse&key={gemini_key}"
    payload = {
        "contents": [{"parts": [{"text": query}]}],
        "systemInstruction": {"parts": [{"text": prompt_text}]},
        "generationConfig": {"temperature": 0.2},
    }

    max_retries = 3
    for attempt in range(max_retries):
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code == 429 and attempt < max_retries - 1:
                    await asyncio.sleep(2.5 * (attempt + 1))
                    continue
                if response.status_code != 200:
                    yield f'root = Column([TextContent("Gemini Error: {response.status_code}")])'
                    return
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        try:
                            data = json.loads(data_str)
                            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            if text:
                                yield text
                        except json.JSONDecodeError:
                            continue
                return


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

    async for chunk in _stream_openai_compatible(OPENCODE_BASE_URL, api_key, payload, "OpenCode"):
        yield chunk



def reorder_ast(code: str) -> str:
    """
    Reorders OpenUI AST lines so that:
    1. All Query() assignments go to the TOP (they are data sources, no deps)
    2. root = ... goes to the BOTTOM (it must be evaluated last)
    3. All other lines stay in their relative order in between

    This prevents forward-reference errors like:
        root = mainLayout      ← mainLayout not defined yet!
        ...
        mainLayout = Column([...])
    """
    if not code:
        return code

    lines = code.splitlines()
    query_lines: list[str] = []
    root_lines: list[str] = []
    other_lines: list[str] = []

    in_multiline_query = False
    current_query_chunk: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not in_multiline_query:
            # Detect Query() assignment (possibly multiline)
            if re.match(r'^\s*\w+\s*=\s*Query\(', line):
                open_p = line.count("(")
                close_p = line.count(")")
                if open_p > close_p:
                    in_multiline_query = True
                    current_query_chunk = [line]
                else:
                    query_lines.append(line)
            # Sink root = ... to bottom
            elif re.match(r'^\s*root\s*=\s*', line):
                root_lines.append(line)
            else:
                other_lines.append(line)
        else:
            current_query_chunk.append(line)
            open_p = sum(l.count("(") for l in current_query_chunk)
            close_p = sum(l.count(")") for l in current_query_chunk)
            if close_p >= open_p:
                in_multiline_query = False
                query_lines.extend(current_query_chunk)
                current_query_chunk = []

    if in_multiline_query and current_query_chunk:
        query_lines.extend(current_query_chunk)

    parts = []
    if query_lines:
        parts.append("\n".join(query_lines))
    if other_lines:
        parts.append("\n".join(other_lines))
    if root_lines:
        parts.append("\n".join(root_lines))

    return "\n\n".join(parts)


def normalize_ast_root(code: str) -> str:
    """
    Normalizes LLM-generated OpenUI AST so that the Renderer always receives
    a direct root = Column([...]) call (not a variable alias or Root()/Column() wrapper).

    Handles all LLM variations:
    - root = Column(mainLayout)   → unwrap & inline → root = Column([...])
    - root = Root([mainLayout])   → unwrap & inline → root = Column([...])
    - root = Root(mainLayout)     → unwrap & inline → root = Column([...])
    - root = mainLayout           → inline → root = Column([...])
    - root = Stack([...])         → root = Column([...])
    - root = Container([...])     → root = Column([...])
    - Stack/Container anywhere    → Column(...)
    - strips markdown fences
    """
    if not code:
        return code

    # Sanitize invalid macros (@Max, @Min, @First, @Last) – @Sum/@Avg/@Count/@Round are VALID and handled by frontend rewriteMacros / MetricCard
    code = re.sub(r'@(?:Max|Min|First|Last)\([^)]*\)', '"—"', code)

    # Sanitize unsafe array indexing in AST expressions (e.g. query.rows[0].value -> "—")
    code = re.sub(r'\b[a-zA-Z_]\w*\.rows\[\d+\](?:\.[a-zA-Z_]\w*)?', '"—"', code)

    # Normalize Stack/Container/Root → Column everywhere
    code = re.sub(r'\bRoot\s*\(', 'Column(', code)
    code = re.sub(r'\bStack\s*\(', 'Column(', code)
    code = re.sub(r'\bContainer\s*\(', 'Column(', code)

    # If root = Column(singleVar) or root = Column([singleVar]):
    # Unwrap it to root = singleVar so the inliner below can resolve its definition
    code = re.sub(r'^\s*root\s*=\s*Column\(\s*\[?\s*([a-zA-Z_]\w*)\s*\]?\s*\)\s*$', r'root = \1', code, flags=re.MULTILINE)

    # CRITICAL: root = varName (simple variable alias)
    # Inline the variable's assigned value directly into root.
    # e.g. root = mainLayout  +  mainLayout = Column([...])  →  root = Column([...])
    root_alias_match = re.search(r'^\s*root\s*=\s*([a-zA-Z_]\w*)\s*$', code, flags=re.MULTILINE)
    if root_alias_match:
        var_name = root_alias_match.group(1)
        var_def_match = re.search(
            rf'^\s*{re.escape(var_name)}\s*=\s*(.+)$',
            code, flags=re.MULTILINE
        )
        if var_def_match:
            var_value = var_def_match.group(1).strip()
            code = re.sub(
                r'^\s*root\s*=\s*[a-zA-Z_]\w*\s*$',
                f'root = {var_value}',
                code, flags=re.MULTILINE
            )

    return code


async def stream_openui_chain(user_query: str) -> AsyncGenerator[str, None]:
    """
    Main LangChain-compatible streaming entrypoint.
    Loads the system prompt and streams from the active LLM provider with telemetry logging.
    Post-processes the full output with AST normalizers before final yield.
    """
    prompt = load_system_prompt()
    provider = LLM_PROVIDER
    model = (
        OPENCODE_MODEL if provider == "opencode"
        else (GEMINI_MODEL if provider == "gemini" else GROQ_MODEL)
    )

    start_t = time.perf_counter()
    accumulated = ""
    err = None

    try:
        if provider == "gemini":
            async for chunk in stream_gemini(prompt, user_query):
                accumulated += chunk
        elif provider == "opencode":
            async for chunk in stream_opencode(prompt, user_query):
                accumulated += chunk
        else:
            async for chunk in stream_groq(prompt, user_query):
                accumulated += chunk

        # Apply post-processing pipeline:
        # 1. Reorder: Query() to top, root= to bottom, everything else in between
        # 2. Normalize Root/Stack/Container → Column
        processed = reorder_ast(accumulated)
        processed = normalize_ast_root(processed)

        # Stream the fully-processed code as a single payload
        yield processed

    except Exception as e:
        err = str(e)
        raise
    finally:
        elapsed_ms = round((time.perf_counter() - start_t) * 1000, 2)
        log_llm_interaction(
            provider=provider,
            model=model,
            user_query=user_query,
            generated_code=accumulated,
            elapsed_ms=elapsed_ms,
            error=err,
        )
