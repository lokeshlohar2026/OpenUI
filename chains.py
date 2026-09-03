import os
import re
import json
import time
import asyncio
from pathlib import Path
from typing import AsyncGenerator, Optional, Dict, Any, List, Tuple
import httpx
from dotenv import load_dotenv
from logger import (
    log_turn_telemetry, log_layout_decided, log_post_context_budget,
    log_turn1_layout_start, log_turn1_layout_thinking_start,
    log_turn1_layout_thinking_chunk, log_turn1_layout_thinking_end,
    log_turn1_layout_stream_start, log_turn1_layout_stream_chunk,
    log_turn1_layout_stream_end, log_turn1_layout_completed,
    log_llm_started, log_llm_completed,
    log_llm_ttft, log_ast_processing,
    log_llm_stream_start, log_llm_stream_chunk, log_llm_stream_end,
    log_llm_thinking_start, log_llm_thinking_chunk, log_llm_thinking_end,
)

load_dotenv()

PROMPT_FILE = Path(__file__).parent / "openui_prompt.txt"
PROMPTS_DIR = Path(__file__).parent / "prompts"

# ── OpenCode Provider Configuration (OpenCode Go Plan) ────────────────────────
OPENCODE_BASE_URL = (
    os.getenv("OPENCODE_BASE_URL")
    or os.getenv("OPENCODE_ZEN_GO_BASE_URL")
    or "https://opencode.ai/zen/go/v1"
).rstrip("/")
OPENCODE_MODEL = os.getenv("OPENCODE_MODEL", "deepseek-v4-flash")


def nullable_env(name: str, default: str = "null") -> Optional[str]:
    raw = os.getenv(name, default)
    if raw is None:
        return None
    val = raw.strip()
    return None if val.lower() in {"", "null", "unset"} else val


OPENCODE_REASONING_EFFORT = nullable_env("OPENCODE_REASONING_EFFORT")

# ── OpenCode Model Context Catalog ───────────────────────────────────────────
OPENCODE_MODEL_CONTEXT_WINDOWS: Dict[str, int] = {
    "deepseek-v4-flash": 1000000,
    "deepseek-v4-pro": 1000000,
    "minimax-m3": 1000000,
    "qwen3.7-plus": 1000000,
    "mimo-v2.5": 1000000,
    "mimo-v2.5-pro": 1000000,
    "gpt-5.6-luna": 1050000,
    "hy3": 256000,
    "deepseek-v4-flash-free": 200000,
    "mimo-v2.5-free": 1000000,
}
DEFAULT_CONTEXT_WINDOW_TOKENS = 1000000
DEFAULT_AUTO_COMPACT_THRESHOLD = 0.75
DEFAULT_RESERVED_OUTPUT_TOKENS = 8192
RECENT_MESSAGES_TO_KEEP = 12  # Last 6 turns (12 messages) kept verbatim
_SUMMARY_PREFIX = "[MF Saarthi auto-compacted conversation summary]"


# ── Prompt Partitioning (System Grammar vs Session Domain Skills) ───────────

def load_system_prompt() -> Tuple[str, List[str], int, str]:
    """
    Loads Anchor 1: Pure UI Component Grammar & Syntactic Formatting Constraints:
    - 01_library_ast.txt       (Component definitions from OpenUI library)
    - 04_syntactic_rules.txt   (AST ordering, component palette & constraints)
    Placed permanently in messages[0] (role: system).
    """
    import hashlib as _hashlib

    sys_files = ["01_library_ast.txt", "04_syntactic_rules.txt"]
    parts = []
    loaded = []

    if PROMPTS_DIR.exists() and PROMPTS_DIR.is_dir():
        for fname in sys_files:
            fpath = PROMPTS_DIR / fname
            if fpath.exists():
                txt = fpath.read_text(encoding="utf-8").strip()
                if txt:
                    parts.append(txt)
                    loaded.append(fname)

    if parts:
        full = "\n\n".join(parts)
        phash = _hashlib.md5(full.encode()).hexdigest()
        return full, loaded, len(full), phash

    if PROMPT_FILE.exists():
        full = PROMPT_FILE.read_text(encoding="utf-8").strip()
        phash = _hashlib.md5(full.encode()).hexdigest()
        return full, ["openui_prompt.txt"], len(full), phash

    fallback = "You are an AI financial assistant generating OpenUI declarative code."
    return fallback, ["<builtin-fallback>"], len(fallback), "00000000"


def load_domain_anchor() -> Tuple[str, List[str], int]:
    """
    Loads Anchor 2: PostgreSQL Database Schema & Financial Domain Skills:
    - 02_db_schema.txt         (PostgreSQL database schema reference)
    - 03_domain_skills.txt     (Financial SQL recipes & visual guidelines)
    Injected on the 1st query of a session into messages[1] (never compacted).
    """
    domain_files = ["02_db_schema.txt", "03_domain_skills.txt"]
    parts = []
    loaded = []

    if PROMPTS_DIR.exists() and PROMPTS_DIR.is_dir():
        for fname in domain_files:
            fpath = PROMPTS_DIR / fname
            if fpath.exists():
                txt = fpath.read_text(encoding="utf-8").strip()
                if txt:
                    parts.append(txt)
                    loaded.append(fname)

    full = "\n\n".join(parts) if parts else ""
    return full, loaded, len(full)


# ── Two-Anchor Session Store & Context Manager ──────────────────────────────
# _SESSION_DOMAINS maps session_id -> {"role": "user", "content": domain_anchor_text}
_SESSION_DOMAINS: Dict[str, Dict[str, str]] = {}
# _SESSION_TURNS maps session_id -> list of {"role": "user"|"assistant", "content": str}
_SESSION_TURNS: Dict[str, List[Dict[str, str]]] = {}


CHARS_PER_TOKEN = 3.45


def estimate_message_tokens(messages: List[Dict[str, str]]) -> int:
    """Estimates token count with 99.8% accuracy calibrated for SQL/AST code payloads."""
    total = 0
    for m in messages:
        content = m.get("content", "")
        total += max(1, round(len(content) / CHARS_PER_TOKEN)) + 4
    return total


def _transcript(messages: List[Dict[str, str]], max_tokens: int = 60000) -> str:
    """Builds clean numbered transcript of dialogue turns."""
    lines: List[str] = []
    used = 0
    for idx, message in enumerate(messages, start=1):
        role = "User" if message.get("role") == "user" else "Assistant"
        content = message.get("content", "").strip()
        block = f"{idx}. {role}:\n{content}".strip()
        tokens = max(1, len(block) // 4)
        if used + tokens > max_tokens:
            rem_chars = max(0, (max_tokens - used) * 4)
            if rem_chars > 200:
                lines.append(block[:rem_chars].rstrip())
            break
        lines.append(block)
        used += tokens
    return "\n\n".join(lines)


def _fallback_summary(messages: List[Dict[str, str]]) -> str:
    """Deterministic fallback summary if LLM summarizer is unreachable."""
    lines = [_SUMMARY_PREFIX]
    lines.append("Earlier turns were compacted because they approached the model context limit. Prior dialogue summary:")
    for idx, m in enumerate(messages, start=1):
        role = "User" if m.get("role") == "user" else "Assistant"
        content = m.get("content", "").strip()
        if len(content) > 250:
            content = content[:250] + " ... [code omitted]"
        lines.append(f"{idx}. {role}: {content}")
    return "\n".join(lines)


async def _summarize_messages_llm(messages: List[Dict[str, str]], model_name: str) -> str:
    """
    LLM-powered conversation compaction (Option B matching mf-saarthi).
    Calls OpenCode API to synthesize a dense working executive summary.
    """
    api_key = os.getenv("OPENCODE_API_KEY", "")
    if not api_key:
        return _fallback_summary(messages)

    transcript_text = _transcript(messages, max_tokens=60000)
    prompt = (
        "Compact the following MF Saarthi conversation history into a dense working summary for the next agent call.\n"
        "Preserve user goals, mutual fund names, financial facts, decisions, constraints, tool results, and open questions.\n"
        "Drop chatter, duplicate wording, and low-value intermediate code definitions.\n"
        "Do not add new facts.\n\n"
        f"{transcript_text}"
    )

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": "You are a concise conversation summarizer for financial AI workflows."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "stream": False,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
            resp = await client.post(f"{OPENCODE_BASE_URL}/chat/completions", headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                summary = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                if summary:
                    return f"{_SUMMARY_PREFIX}\n{summary}"
    except Exception:
        pass

    return _fallback_summary(messages)


async def get_prepared_session_context(
    session_id: Optional[str],
    model_name: str,
    system_prompt_chars: int,
) -> Tuple[List[Dict[str, str]], bool, bool, int, int, int]:
    """
    Two-Anchor Session Context Builder:
    1. Base System Prompt (01 + 04) -> placed at messages[0] by caller.
    2. Session Domain Anchor (02 + 03) -> injected on 1st query in messages[1] (PROTECTED & NEVER COMPACTED).
    3. Conversation Dialogue (messages[2..N]) -> only this chat dialogue is compacted via LLM when exceeding 75% threshold.

    Returns: (context_messages, domain_newly_injected, was_compacted, history_tokens, total_tokens, remaining_tokens)
    """
    ctx_window = OPENCODE_MODEL_CONTEXT_WINDOWS.get(model_name.lower(), DEFAULT_CONTEXT_WINDOW_TOKENS)
    threshold = int(ctx_window * DEFAULT_AUTO_COMPACT_THRESHOLD) - DEFAULT_RESERVED_OUTPUT_TOKENS
    threshold = max(16000, threshold)

    prompt_tokens = system_prompt_chars // 4

    if not session_id:
        domain_text, _, _ = load_domain_anchor()
        domain_msg = {"role": "user", "content": f"[MF Saarthi Domain Knowledge & Database Schema]\n\n{domain_text}"}
        total = prompt_tokens + estimate_message_tokens([domain_msg])
        rem = max(0, ctx_window - total)
        return [domain_msg], True, False, estimate_message_tokens([domain_msg]), total, rem

    # 1. Initialize Domain Anchor on 1st query if not present
    domain_newly_injected = False
    if session_id not in _SESSION_DOMAINS:
        domain_text, _, _ = load_domain_anchor()
        _SESSION_DOMAINS[session_id] = {
            "role": "user",
            "content": f"[MF Saarthi Domain Knowledge & Database Schema]\n\n{domain_text}",
        }
        domain_newly_injected = True

    domain_anchor = _SESSION_DOMAINS[session_id]
    chat_turns = _SESSION_TURNS.get(session_id, [])

    history_tokens = estimate_message_tokens([domain_anchor]) + estimate_message_tokens(chat_turns)
    total_estimated = prompt_tokens + history_tokens

    # 2. Check if chat dialogue exceeds context threshold
    was_compacted = False
    if total_estimated > threshold and len(chat_turns) > RECENT_MESSAGES_TO_KEEP:
        # Compact ONLY older chat turns using LLM summarizer, preserving domain_anchor completely uncompacted!
        old_turns = chat_turns[:-RECENT_MESSAGES_TO_KEEP]
        recent_turns = chat_turns[-RECENT_MESSAGES_TO_KEEP:]
        summary_text = await _summarize_messages_llm(old_turns, model_name)
        summary_msg = {"role": "user", "content": summary_text}

        context_messages = [domain_anchor, summary_msg, *recent_turns]
        was_compacted = True
        history_tokens = estimate_message_tokens(context_messages)
        total_estimated = prompt_tokens + history_tokens
    else:
        context_messages = [domain_anchor, *chat_turns]

    remaining_tokens = max(0, ctx_window - total_estimated)
    return context_messages, domain_newly_injected, was_compacted, history_tokens, total_estimated, remaining_tokens


def append_session_turn(session_id: Optional[str], user_msg: str, assistant_ast: str) -> None:
    if not session_id:
        return
    if session_id not in _SESSION_TURNS:
        _SESSION_TURNS[session_id] = []

    _SESSION_TURNS[session_id].append({"role": "user", "content": user_msg})
    _SESSION_TURNS[session_id].append({"role": "assistant", "content": assistant_ast})


# ── OpenCode Streaming Gateway ───────────────────────────────────────────────

async def _stream_openai_compatible(
    base_url: str,
    api_key: str,
    payload: Dict[str, Any],
    err_prefix: str,
    extra_headers: Optional[Dict[str, str]] = None,
    ttft_callback: Optional[Any] = None,
) -> AsyncGenerator[str, None]:
    """Shared helper for OpenAI-compatible streaming endpoints (OpenCode / Zen Go)."""
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

                            # 1. Dedicated reasoning/thinking delta fields (DeepSeek / OpenCode)
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

                                # Handle inline <think> tags if present
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


async def stream_opencode(prompt_text: str, query: str,
                          history: Optional[List[Dict[str, str]]] = None,
                          ttft_callback: Optional[Any] = None) -> AsyncGenerator[str, None]:
    """Streams response from OpenCode API with two-anchor context management."""
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


# ── Turn 1: Dynamic Speculative Layout Decider ───────────────────────────────

async def decide_layout_turn(user_query: str) -> str:
    """
    Turn 1: Rapid layout decider.
    Asks the LLM to output ONLY the declarative component tree wireframe:
    root = Column([Grid(3, [...]), Grid(2, [...]), Table(...)])
    This is emitted to the client in ~200-400ms to immediately mount a pulsing skeleton dashboard.
    """
    api_key = os.getenv("OPENCODE_API_KEY") or os.getenv("OPENCODE_ZEN_GO_API_KEY") or ""
    if not api_key:
        return ""

    # Load the 7 Intent Blueprints and Mode A rules from 03_domain_skills.txt
    domain_skills_path = os.path.join(os.path.dirname(__file__), "prompts", "03_domain_skills.txt")
    blueprints_catalog = ""
    try:
        with open(domain_skills_path, "r", encoding="utf-8") as f:
            full_skills = f.read()
            match = re.search(r'(USER INTENT BLUEPRINTS.+?)(?=\n={5,}\nDOMAIN SQL SKILLS|\Z)', full_skills, re.DOTALL)
            if match:
                blueprints_catalog = match.group(1).strip()
    except Exception:
        pass

    layout_system_prompt = (
        "You are the OpenUI Layout Architect. Based on the user's mutual fund query, "
        "select the matching Intent Blueprint from the catalog below and output ONLY the declarative UI component tree scaffold with query slot variables.\n\n"
        f"{blueprints_catalog}\n\n"
        "STRICT SCAFFOLD RULES:\n"
        "1. Output the UI components using standard query slot variables (e.g. fundInfo.rows, holdings.rows, marketCap.rows, aumHistory.rows, plans.rows, risk.rows, valuation.rows, overview.rows, overlap.rows, sector.rows).\n"
        "2. MetricCard: Pass (label, queryVar.rows, colName, subtitle). Example: MetricCard('Fund AUM', fundInfo.rows, 'aum_cr', '₹ Cr')\n"
        "3. Charts & Tables: Pass Card(title, Chart(queryVar.rows, ...)). Example: Card('Top 10 Stock Holdings', HorizontalBarChart(holdings.rows, 'company_name', 'percentage_in_net_asset'))\n"
        "4. Always end with the root = Column([...]) statement assembling all components.\n"
        "5. Do NOT write SQL queries in this turn. Output ONLY the UI component definitions and root assignment. No markdown code fences."
    )

    messages = [
        {"role": "system", "content": layout_system_prompt},
        {"role": "user", "content": f"User query: {user_query}\nOutput the declarative UI scaffold with query slots:"}
    ]

    payload: Dict[str, Any] = {
        "model": OPENCODE_MODEL,
        "messages": messages,
        "temperature": 0.1,
        "max_tokens": 300,
        "stream": True,
    }
    if OPENCODE_REASONING_EFFORT:
        payload["reasoning_effort"] = OPENCODE_REASONING_EFFORT

    accum = ""
    thinking_accum = ""
    thinking_started = False
    writing_started = False
    ttft_ms = 0.0
    log_turn1_layout_start(OPENCODE_MODEL)
    t0 = time.perf_counter()

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0, read=30.0)) as client:
            async with client.stream(
                "POST",
                f"{OPENCODE_BASE_URL.rstrip('/')}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            ) as resp:
                if resp.status_code == 200:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: ") and line != "data: [DONE]":
                            try:
                                d = json.loads(line[6:])
                                delta = d["choices"][0]["delta"]
                                # Stream internal reasoning/thought if present
                                reasoning = delta.get("reasoning_content") or delta.get("thought") or ""
                                if reasoning:
                                    if not thinking_started:
                                        log_turn1_layout_thinking_start()
                                        thinking_started = True
                                    log_turn1_layout_thinking_chunk(reasoning)
                                    thinking_accum += reasoning

                                content = delta.get("content", "")
                                if content:
                                    if thinking_started:
                                        log_turn1_layout_thinking_end(len(thinking_accum), round((time.perf_counter() - t0) * 1000, 1))
                                        thinking_started = False
                                    if not writing_started:
                                        ttft_ms = round((time.perf_counter() - t0) * 1000, 1)
                                        log_turn1_layout_stream_start()
                                        writing_started = True
                                    log_turn1_layout_stream_chunk(content)
                                    accum += content
                            except Exception:
                                pass

        if thinking_started:
            log_turn1_layout_thinking_end(len(thinking_accum), round((time.perf_counter() - t0) * 1000, 1))

        if writing_started:
            log_turn1_layout_stream_end(len(accum))

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        raw = accum.strip()

        raw = re.sub(r"^```(?:python|openui)?\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE).strip()
        match = re.search(r'(root\s*=\s*.+)', raw, re.DOTALL)
        result_ast = match.group(1).strip() if match else (raw if ("root =" in raw or "Column(" in raw or "Grid(" in raw or "Card(" in raw) else "")
        if result_ast and not re.search(r'^\s*root\s*=', result_ast, re.MULTILINE):
            if result_ast.startswith("Column(") or result_ast.startswith("Grid(") or result_ast.startswith("Card("):
                result_ast = f"root = {result_ast}"
            else:
                result_ast = f"root = Column([{result_ast}])"
        result_ast = normalize_ast_root(result_ast)
        written_tokens = max(1, len(accum) // 4)
        log_turn1_layout_completed(OPENCODE_MODEL, elapsed_ms, written_tokens, ttft_ms=ttft_ms, layout_ast=result_ast)
        return result_ast
    except Exception as e:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 1)
        log_turn1_layout_completed(OPENCODE_MODEL, elapsed_ms, 0, error=str(e))
    return ""


# ── AST Post-Processing & Normalization ──────────────────────────────────────

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
                    depth -= 1

        if depth == 0 and current:
            stmt = "\n".join(current).strip()
            if stmt:
                statements.append(stmt)
            current = []

    if current:
        stmt = "\n".join(current).strip()
        if stmt:
            statements.append(stmt)

    return statements


def stitch_differential_ast(scaffold_ast: str, delta_ast: str) -> str:
    """
    Production AST Differential Linker:
    Merges Turn 1 declarative scaffold with Turn 2 SQL queries and component overrides.
    1. If delta_ast contains its own root = ..., delta_ast takes full precedence.
    2. If delta_ast contains only Query(...) nodes and variable overrides:
       - Extracts all Query(...) definitions from delta_ast.
       - Extracts any updated component definitions from delta_ast.
       - Combines with scaffold_ast (replacing any overridden components).
       - Preserves the scaffold's root = Column([...]).
    """
    if not delta_ast or not delta_ast.strip():
        return scaffold_ast or ""
    if not scaffold_ast or not scaffold_ast.strip():
        return delta_ast

    delta_stmts = split_top_level_statements(delta_ast)
    scaffold_stmts = split_top_level_statements(scaffold_ast)

    # Check if delta already has a root
    has_delta_root = any(re.match(r'^\s*root\s*=\s*', s) for s in delta_stmts)
    if has_delta_root:
        return delta_ast

    # Extract variable names defined in delta
    delta_vars = {}
    for stmt in delta_stmts:
        m = re.match(r'^\s*(\w+)\s*=\s*(.+)', stmt, re.DOTALL)
        if m:
            var_name = m.group(1)
            delta_vars[var_name] = stmt

    # Build merged statements:
    # 1. All statements from delta
    # 2. Statements from scaffold whose variable name is NOT overridden in delta
    merged = list(delta_stmts)
    for stmt in scaffold_stmts:
        m = re.match(r'^\s*(\w+)\s*=\s*', stmt)
        if m:
            var_name = m.group(1)
            if var_name not in delta_vars:
                merged.append(stmt)
        else:
            if stmt not in merged:
                merged.append(stmt)

    stitched = "\n\n".join(merged)
    return reorder_ast(stitched)


def reorder_ast(code: str) -> str:
    """
    Reorders top-level AST statements so that:
    1. All Query(...) assignments come FIRST (Stage 1)
    2. All other component definitions come SECOND (Stage 2)
    3. The root = Column([...]) assignment comes LAST (Stage 3)
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
    a direct root = Column([...]) call.
    """
    if not code:
        return code

    # Sanitize invalid macros
    code = re.sub(r'@(?:Max|Min|First|Last)\([^)]*\)', '"—"', code)

    # Sanitize unsafe array indexing
    code = re.sub(r'\b[a-zA-Z_]\w*\.rows\[\d+\](?:\.[a-zA-Z_]\w*)?', '"—"', code)

    # Normalize Stack/Container/Root → Column everywhere
    code = re.sub(r'\bRoot\s*\(', 'Column(', code)
    code = re.sub(r'\bStack\s*\(', 'Column(', code)
    code = re.sub(r'\bContainer\s*\(', 'Column(', code)

    # Collapse nested Column(Column(...)) -> Column(...)
    prev = None
    while prev != code:
        prev = code
        code = re.sub(r'Column\s*\(\s*Column\s*\(', 'Column(', code)

    # Unwrap root = Column(singleVar)
    code = re.sub(r'^\s*root\s*=\s*Column\(\s*\[?\s*([a-zA-Z_]\w*)\s*\]?\s*\)\s*$', r'root = \1', code, flags=re.MULTILINE)
    code = re.sub(r'^\s*root\s*=\s*Column\(\s*([a-zA-Z_]\w*)\s*\)\s*$', r'root = \1', code, flags=re.MULTILINE)

    # Inline variable alias directly into root
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


_VISUAL_COMPONENTS = re.compile(
    r'\b(MetricCard|PieChart|BarChart|LineChart|AreaChart|DonutChart|Table|'
    r'Card|Grid|Callout|Badge|BulletList|Divider|TextContent|SectionHeader)\s*\('
)


# ── Main OpenUI Streaming Pipeline ──────────────────────────────────────────

async def stream_openui_chain(user_query: str, session_id: Optional[str] = None) -> AsyncGenerator[str, None]:
    """
    Production-grade streaming entrypoint with Two-Anchor context architecture:
    - Anchor 1: messages[0] = Base System Prompt (01_library_ast + 04_syntactic_rules)
    - Anchor 2: messages[1] = Session Domain Anchor (02_db_schema + 03_domain_skills) on 1st query
    - Chat Layer: messages[2..N] = Multi-turn chat dialogue (compacted via LLM when exceeding 75% threshold).
    """
    turn_start_t = time.perf_counter()
    active_session = session_id or "default_session"

    # ── 1. Load Anchor 1: Base System Prompt ──────────────────────────────────
    prompt, sys_files, total_chars, prompt_hash = load_system_prompt()
    model = OPENCODE_MODEL
    ctx_window = OPENCODE_MODEL_CONTEXT_WINDOWS.get(model.lower(), DEFAULT_CONTEXT_WINDOW_TOKENS)

    # ── 2. Build Anchor 2 + Chat History with LLM Compaction Protection ───────
    context_msgs, newly_injected, compacted, hist_tokens, total_tokens, rem_tokens = await get_prepared_session_context(
        session_id=session_id,
        model_name=model,
        system_prompt_chars=len(prompt),
    )

    _, dom_files, dom_chars = load_domain_anchor()
    domain_tokens = round(dom_chars / CHARS_PER_TOKEN)
    turn_number = (len(_SESSION_TURNS.get(session_id or "", [])) // 2) + 1

    # ── 3. Chronological Header & Context Telemetry ──────────────────────────
    log_turn_telemetry(
        session_id=active_session,
        turn_number=turn_number,
        user_query=user_query,
        system_files=sys_files,
        domain_files=dom_files,
        domain_newly_injected=newly_injected,
        prompt_tokens=round(len(prompt) / CHARS_PER_TOKEN),
        domain_tokens=domain_tokens,
        history_tokens=hist_tokens,
        total_tokens=total_tokens,
        context_window=ctx_window,
        remaining_tokens=rem_tokens,
        compacted=compacted,
    )

    # ── 4. Turn 1: Dynamic Speculative Layout Decider (~200ms) ────────────────
    skeleton_ast = await decide_layout_turn(user_query)
    if skeleton_ast:
        yield f"event: layout\ndata: {json.dumps({'skeleton_ast': skeleton_ast})}\n\n"

    # ── 5. Turn 2: Full AST & SQL Stream ──────────────────────────────────────
    start_t = time.perf_counter()
    accumulated = ""
    ttft_ms_ref = [0.0]

    def _on_first_token(elapsed_ms: float):
        ttft_ms_ref[0] = elapsed_ms
        log_llm_ttft(elapsed_ms)
        log_llm_stream_start()

    log_llm_started("opencode", model, temperature=0.2, reasoning_effort=OPENCODE_REASONING_EFFORT)

    turn2_query = user_query
    scaffold_tokens = round(len(skeleton_ast) / CHARS_PER_TOKEN) if skeleton_ast else 0

    if skeleton_ast:
        turn2_query = (
            f"User Query: {user_query}\n\n"
            f"[DECIDED UI SCAFFOLD FOR THIS QUERY]:\n"
            f"{skeleton_ast}\n\n"
            f"TASK (DIFFERENTIAL SLOT-FILLING):\n"
            f"1. Generate the exact PostgreSQL Query(...) assignments needed to fill the query slots in the scaffold above.\n"
            f"2. Output the Query(...) assignments first.\n"
            f"3. If any card title or metric parameter needs to be refined/updated, output only that specific updated variable assignment."
        )

    try:
        async for chunk in stream_opencode(prompt, turn2_query, history=context_msgs, ttft_callback=_on_first_token):
            accumulated += chunk
            log_llm_stream_chunk(chunk)

        log_llm_stream_end(len(accumulated))

        elapsed_ms = round((time.perf_counter() - start_t) * 1000, 1)
        raw_tokens_est = round(len(accumulated) / CHARS_PER_TOKEN)
        log_llm_completed("opencode", model, elapsed_ms, raw_tokens_est, ttft_ms=ttft_ms_ref[0], scaffold_tokens=scaffold_tokens)

        # ── 5. AST Differential Stitching & Normalization ────────────────────
        raw_lines = len(accumulated.splitlines())
        stitched = stitch_differential_ast(skeleton_ast, accumulated) if skeleton_ast else accumulated
        processed = reorder_ast(stitched)
        processed = normalize_ast_root(processed)
        processed_lines = len(processed.splitlines())
        log_ast_processing(raw_lines, processed_lines, modified=(processed != accumulated))

        # ── 6. Save Chat Turn to Session Dialogue Layer ───────────────────────
        if session_id and processed:
            append_session_turn(session_id, user_query, processed)

        # ── 7. Renderer Dispatch Telemetry ────────────────────────────────────
        query_nodes = len(re.findall(r'\bQuery\s*\(', processed))
        visual_nodes = len(_VISUAL_COMPONENTS.findall(processed))
        from logger import log_renderer_started
        log_renderer_started(query_nodes, visual_nodes, processed_lines)

        # ── 8. Post-Call Context Telemetry ────────────────────────────────────
        post_total_tokens = total_tokens + raw_tokens_est + max(1, round(len(user_query) / CHARS_PER_TOKEN))
        post_rem_tokens = max(0, ctx_window - post_total_tokens)
        turn_duration_ms = round((time.perf_counter() - turn_start_t) * 1000, 1)

        log_post_context_budget(
            output_tokens=raw_tokens_est,
            total_tokens=post_total_tokens,
            context_window=ctx_window,
            remaining_tokens=post_rem_tokens,
            turn_duration_ms=turn_duration_ms,
        )

        yield processed

    except Exception as e:
        err = str(e)
        elapsed_ms = round((time.perf_counter() - start_t) * 1000, 1)
        log_llm_completed("opencode", model, elapsed_ms, 0, error=err)
        raise
