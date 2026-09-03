import os
import re
import json
import time
import asyncio
from pathlib import Path
from typing import AsyncGenerator, Optional, Dict, Any
import httpx
from dotenv import load_dotenv
from logger import (
    log_llm_started, log_llm_completed,
    log_llm_ttft, log_prompt_loaded, log_ast_processing,
    log_llm_stream_start, log_llm_stream_chunk, log_llm_stream_end,
    log_llm_thinking_start, log_llm_thinking_chunk, log_llm_thinking_end,
)

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
    raw = os.getenv(name, default)
    if raw is None:
        return None
    val = raw.strip()
    return None if val.lower() in {"", "null", "unset"} else val


GROQ_REASONING_EFFORT = nullable_env("GROQ_REASONING_EFFORT")
OPENCODE_REASONING_EFFORT = nullable_env("OPENCODE_REASONING_EFFORT")

PROMPTS_DIR = Path(__file__).parent / "prompts"
PROMPT_FILE = Path(__file__).parent / "openui_prompt.txt"


def load_system_prompt() -> tuple:
    """
    Dynamically loads the modular system prompt files from the /prompts directory:
    - 01_library_ast.txt       (Component definitions from OpenUI library)
    - 02_db_schema.txt         (PostgreSQL database schema reference)
    - 03_domain_skills.txt     (Financial SQL recipes & visual guidelines)
    - 04_syntactic_rules.txt   (AST ordering, component palette & constraints)

    Falls back to openui_prompt.txt if the /prompts directory is not present.

    Returns: (prompt_text, files_loaded, total_chars, prompt_hash)
    """
    import hashlib as _hashlib

    if PROMPTS_DIR.exists() and PROMPTS_DIR.is_dir():
        prompt_parts = []
        files_loaded = []
        for file in sorted(PROMPTS_DIR.glob("*.txt")):
            text = file.read_text(encoding="utf-8").strip()
            if text:
                prompt_parts.append(text)
                files_loaded.append(file.name)
        if prompt_parts:
            full = "\n\n".join(prompt_parts)
            phash = _hashlib.md5(full.encode()).hexdigest()
            return full, files_loaded, len(full), phash

    if PROMPT_FILE.exists():
        full = PROMPT_FILE.read_text(encoding="utf-8").strip()
        phash = _hashlib.md5(full.encode()).hexdigest()
        return full, ["openui_prompt.txt"], len(full), phash

    fallback = "You are an AI financial assistant generating OpenUI declarative code."
    return fallback, ["<builtin-fallback>"], len(fallback), "00000000"



async def _stream_openai_compatible(
    base_url: str,
    api_key: str,
    payload: Dict[str, Any],
    err_prefix: str,
    extra_headers: Optional[Dict[str, str]] = None,
    ttft_callback: Optional[Any] = None,
) -> AsyncGenerator[str, None]:
    """Shared helper for OpenAI-compatible streaming endpoints (Groq, OpenCode)."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if extra_headers:
        headers.update(extra_headers)

    _ttft_fired = False
    _thinking_active = False
    _thinking_chars = 0
    _thinking_start_t = 0.0
    _in_think_tag = False

    max_retries = 3
    for attempt in range(max_retries):
        async with httpx.AsyncClient(timeout=60.0) as client:
            req_start_t = time.perf_counter()
            async with client.stream("POST", f"{base_url}/chat/completions", headers=headers, json=payload) as response:
                if response.status_code == 429 and attempt < max_retries - 1:
                    await asyncio.sleep(2.5 * (attempt + 1))
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

                            # 1. Dedicated reasoning/thinking delta fields (DeepSeek / vLLM / OpenCode)
                            reasoning = delta.get("reasoning_content") or delta.get("reasoning") or delta.get("thought")
                            if reasoning:
                                if not _thinking_active:
                                    _thinking_start_t = time.perf_counter()
                                    log_llm_thinking_start()
                                    _thinking_active = True
                                _thinking_chars += len(reasoning)
                                log_llm_thinking_chunk(reasoning)
                                continue

                            # 2. Standard code content
                            content = delta.get("content") or ""
                            if content:
                                if _thinking_active:
                                    think_dur_ms = (time.perf_counter() - _thinking_start_t) * 1000
                                    log_llm_thinking_end(_thinking_chars, think_dur_ms)
                                    _thinking_active = False

                                # Handle inline <think> tags if present inside content
                                if "<think>" in content:
                                    _in_think_tag = True
                                    parts = content.split("<think>", 1)
                                    if parts[0]:
                                        if not _ttft_fired and ttft_callback:
                                            elapsed_ms = round((time.perf_counter() - req_start_t) * 1000, 1)
                                            ttft_callback(elapsed_ms)
                                            _ttft_fired = True
                                        yield parts[0]
                                    if not _thinking_active:
                                        _thinking_start_t = time.perf_counter()
                                        log_llm_thinking_start()
                                        _thinking_active = True
                                    content = parts[1]

                                if _in_think_tag:
                                    if "</think>" in content:
                                        think_part, code_part = content.split("</think>", 1)
                                        _thinking_chars += len(think_part)
                                        log_llm_thinking_chunk(think_part)
                                        think_dur_ms = (time.perf_counter() - _thinking_start_t) * 1000
                                        log_llm_thinking_end(_thinking_chars, think_dur_ms)
                                        _thinking_active = False
                                        _in_think_tag = False
                                        content = code_part
                                    else:
                                        _thinking_chars += len(content)
                                        log_llm_thinking_chunk(content)
                                        continue

                                if content:
                                    if not _ttft_fired and ttft_callback:
                                        elapsed_ms = round((time.perf_counter() - req_start_t) * 1000, 1)
                                        ttft_callback(elapsed_ms)
                                        _ttft_fired = True
                                    yield content
                        except Exception:
                            continue

                    if _thinking_active:
                        think_dur_ms = (time.perf_counter() - _thinking_start_t) * 1000
                        log_llm_thinking_end(_thinking_chars, think_dur_ms)
                        _thinking_active = False

                    return
                except GeneratorExit:
                    if _thinking_active:
                        think_dur_ms = (time.perf_counter() - _thinking_start_t) * 1000
                        log_llm_thinking_end(_thinking_chars, think_dur_ms)
                    return



# In-memory session store for multi-turn conversations
# Maps session_id -> list of {"role": "user"|"assistant", "content": str}
_SESSION_HISTORY: Dict[str, list] = {}
_MAX_SESSION_TURNS = int(os.getenv("MAX_SESSION_TURNS", "5"))  # 5 turns = 10 messages max


def get_session_history(session_id: Optional[str]) -> list:
    if not session_id or session_id not in _SESSION_HISTORY:
        return []
    return _SESSION_HISTORY[session_id]


def append_session_turn(session_id: Optional[str], user_msg: str, assistant_ast: str) -> None:
    if not session_id:
        return
    if session_id not in _SESSION_HISTORY:
        _SESSION_HISTORY[session_id] = []

    _SESSION_HISTORY[session_id].append({"role": "user", "content": user_msg})
    _SESSION_HISTORY[session_id].append({"role": "assistant", "content": assistant_ast})

    # Cap to max turns
    if len(_SESSION_HISTORY[session_id]) > _MAX_SESSION_TURNS * 2:
        _SESSION_HISTORY[session_id] = _SESSION_HISTORY[session_id][-_MAX_SESSION_TURNS * 2:]


async def stream_groq(prompt_text: str, query: str,
                      history: Optional[list] = None,
                      ttft_callback: Optional[Any] = None) -> AsyncGenerator[str, None]:
    """Streams response from Groq API (openai/gpt-oss-120b or llama-3.3-70b)."""
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        yield 'root = Column([TextContent("Error: GROQ_API_KEY is not set in environment.")])'
        return

    messages = [{"role": "system", "content": prompt_text}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": query})

    payload: Dict[str, Any] = {
        "model": GROQ_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "max_completion_tokens": GROQ_MAX_COMPLETION_TOKENS,
        "stream": True,
    }
    if GROQ_REASONING_EFFORT:
        payload["reasoning_effort"] = GROQ_REASONING_EFFORT

    async for chunk in _stream_openai_compatible(
        GROQ_BASE_URL, api_key, payload, "Groq", ttft_callback=ttft_callback
    ):
        yield chunk


async def stream_gemini(prompt_text: str, query: str,
                        history: Optional[list] = None,
                        ttft_callback: Optional[Any] = None) -> AsyncGenerator[str, None]:
    """Streams response from Google Gemini API via official SDK or high-speed httpx SSE."""
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        yield 'root = Column([TextContent("Error: GEMINI_API_KEY is not set.")])'
        return

    _ttft_fired = False

    # Construct chat contents
    gemini_contents = []
    if history:
        for turn in history:
            role = "user" if turn["role"] == "user" else "model"
            gemini_contents.append({"role": role, "parts": [{"text": turn["content"]}]})
    gemini_contents.append({"role": "user", "parts": [{"text": query}]})

    if genai is not None:
        try:
            client = genai.Client(api_key=gemini_key)
            req_start_t = time.perf_counter()
            response_stream = client.models.generate_content_stream(
                model=GEMINI_MODEL,
                contents=query if not history else gemini_contents,
                config=types.GenerateContentConfig(
                    system_instruction=prompt_text,
                    temperature=0.2,
                ),
            )
            for chunk in response_stream:
                if chunk.text:
                    if not _ttft_fired and ttft_callback:
                        elapsed_ms = round((time.perf_counter() - req_start_t) * 1000, 1)
                        ttft_callback(elapsed_ms)
                        _ttft_fired = True
                    yield chunk.text
            return
        except Exception:
            pass

    # High-speed HTTP REST fallback with retry
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:streamGenerateContent?alt=sse&key={gemini_key}"
    payload = {
        "contents": gemini_contents,
        "systemInstruction": {"parts": [{"text": prompt_text}]},
        "generationConfig": {"temperature": 0.2},
    }

    max_retries = 3
    for attempt in range(max_retries):
        async with httpx.AsyncClient(timeout=60.0) as client:
            req_start_t = time.perf_counter()
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
                                if not _ttft_fired and ttft_callback:
                                    elapsed_ms = round((time.perf_counter() - req_start_t) * 1000, 1)
                                    ttft_callback(elapsed_ms)
                                    _ttft_fired = True
                                yield text
                        except json.JSONDecodeError:
                            continue
                return


async def stream_opencode(prompt_text: str, query: str,
                          history: Optional[list] = None,
                          ttft_callback: Optional[Any] = None) -> AsyncGenerator[str, None]:
    """Streams response from OpenCode API with multi-turn conversation support."""
    api_key = os.getenv("OPENCODE_API_KEY", "")
    if not api_key:
        yield 'root = Column([TextContent("Error: OPENCODE_API_KEY is not set.")])'
        return

    messages = [{"role": "system", "content": prompt_text}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": query})

    payload: Dict[str, Any] = {
        "model": OPENCODE_MODEL,
        "messages": messages,
        "temperature": 0.2,
        "stream": True,
    }
    if OPENCODE_REASONING_EFFORT:
        payload["reasoning_effort"] = OPENCODE_REASONING_EFFORT

    async for chunk in _stream_openai_compatible(
        OPENCODE_BASE_URL, api_key, payload, "OpenCode", ttft_callback=ttft_callback
    ):
        yield chunk




def split_top_level_statements(code: str) -> list:
    """Splits declarative AST code into top-level statements, tracking (), [], {} balance."""
    statements = []
    current = []
    depth = 0
    in_single_quote = False
    in_double_quote = False
    escape = False

    for line in code.splitlines():
        if not line.strip() and depth == 0:
            continue
        current.append(line)
        for ch in line:
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue
            if ch == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
            elif ch == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif not in_single_quote and not in_double_quote:
                if ch in "([{":
                    depth += 1
                elif ch in ")]}":
                    depth = max(0, depth - 1)

        if depth == 0 and current:
            statements.append("\n".join(current).strip())
            current = []

    if current:
        statements.append("\n".join(current).strip())

    return [s for s in statements if s]


def reorder_ast(code: str) -> str:
    """
    Reorders OpenUI AST so that:
    1. All Query() assignments go to the TOP (they are data sources, no deps)
    2. All intermediate component definitions stay in the MIDDLE
    3. root = ... goes to the BOTTOM (it must be evaluated last)

    Handles full multi-line Query(...) and root = Column([...]) blocks cleanly without syntax corruption.
    """
    if not code:
        return code

    statements = split_top_level_statements(code)
    query_stmts = []
    root_stmts = []
    other_stmts = []

    for stmt in statements:
        if re.match(r'^\s*\w+\s*=\s*Query\(', stmt):
            query_stmts.append(stmt)
        elif re.match(r'^\s*root\s*=\s*', stmt):
            root_stmts.append(stmt)
        else:
            other_stmts.append(stmt)

    parts = []
    if query_stmts:
        parts.append("\n\n".join(query_stmts))
    if other_stmts:
        parts.append("\n\n".join(other_stmts))
    if root_stmts:
        parts.append("\n\n".join(root_stmts))

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

    # Collapse nested Column(Column(...)) -> Column(...) repeatedly (handles Root(Container([...])) -> Column(Column([...])))
    prev = None
    while prev != code:
        prev = code
        code = re.sub(r'Column\s*\(\s*Column\s*\(', 'Column(', code)

    # If root = Column(singleVar) or root = Column([singleVar]):
    # Unwrap it to root = singleVar so the inliner below can resolve its definition
    code = re.sub(r'^\s*root\s*=\s*Column\(\s*\[?\s*([a-zA-Z_]\w*)\s*\]?\s*\)\s*$', r'root = \1', code, flags=re.MULTILINE)
    # Handle root = Column(Column(var)) after collapse above
    code = re.sub(r'^\s*root\s*=\s*Column\(\s*([a-zA-Z_]\w*)\s*\)\s*$', r'root = \1', code, flags=re.MULTILINE)

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



# Component keywords to count in the final AST for renderer log
_VISUAL_COMPONENTS = re.compile(
    r'\b(MetricCard|PieChart|BarChart|LineChart|AreaChart|DonutChart|Table|'
    r'Card|Grid|Callout|Badge|BulletList|Divider|TextContent|SectionHeader)\s*\('
)


async def stream_openui_chain(user_query: str, session_id: Optional[str] = None) -> AsyncGenerator[str, None]:
    """
    Main LangChain-compatible streaming entrypoint with multi-turn session support.
    Loads the system prompt and streams from the active LLM provider with full evaluation logging.
    Post-processes the full output with AST normalizers before final yield.
    """
    # ── 1. Load & log prompt ──────────────────────────────────────────────────
    prompt, files_loaded, total_chars, prompt_hash = load_system_prompt()
    log_prompt_loaded(files_loaded, total_chars, prompt_hash)

    provider = LLM_PROVIDER
    model = (
        OPENCODE_MODEL if provider == "opencode"
        else (GEMINI_MODEL if provider == "gemini" else GROQ_MODEL)
    )

    history = get_session_history(session_id)

    # ── 2. LLM call ───────────────────────────────────────────────────────────
    start_t = time.perf_counter()
    accumulated = ""
    err = None
    ttft_ms_ref = [0.0]

    # TTFT callback — fired by the streaming client upon receiving the first non-empty token
    def _on_first_token(elapsed_ms: float):
        ttft_ms_ref[0] = elapsed_ms
        log_llm_ttft(elapsed_ms)
        log_llm_stream_start()

    log_llm_started(provider, model, temperature=0.2)

    try:
        # Select provider stream (unified loop so chunk logging happens once)
        if provider == "gemini":
            _stream = stream_gemini(prompt, user_query, history=history, ttft_callback=_on_first_token)
        elif provider == "opencode":
            _stream = stream_opencode(prompt, user_query, history=history, ttft_callback=_on_first_token)
        else:
            _stream = stream_groq(prompt, user_query, history=history, ttft_callback=_on_first_token)

        async for chunk in _stream:
            accumulated += chunk
            log_llm_stream_chunk(chunk)   # ← live token written to log as it arrives

        log_llm_stream_end(len(accumulated))

        elapsed_ms = round((time.perf_counter() - start_t) * 1000, 1)
        raw_tokens_est = len(accumulated) // 4
        log_llm_completed(provider, model, elapsed_ms, raw_tokens_est, ttft_ms=ttft_ms_ref[0])

        # ── 3. AST post-processing ────────────────────────────────────────────
        raw_lines = len(accumulated.splitlines())
        processed = reorder_ast(accumulated)
        processed = normalize_ast_root(processed)
        processed_lines = len(processed.splitlines())
        log_ast_processing(raw_lines, processed_lines, modified=(processed != accumulated))

        # ── 4. Save to session history ─────────────────────────────────────────
        if session_id and processed:
            append_session_turn(session_id, user_query, processed)

        # ── 5. Renderer dispatch ──────────────────────────────────────────────
        query_nodes = len(re.findall(r'\bQuery\s*\(', processed))
        visual_nodes = len(_VISUAL_COMPONENTS.findall(processed))
        from logger import log_renderer_started
        log_renderer_started(query_nodes, visual_nodes, processed_lines)

        yield processed

    except Exception as e:
        err = str(e)
        elapsed_ms = round((time.perf_counter() - start_t) * 1000, 1)
        log_llm_completed(provider, model, elapsed_ms, 0, error=err)
        raise
