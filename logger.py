import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone, timedelta
from typing import Any, Optional, List

# ── Single unified log file ───────────────────────────────────────────────────
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

_LOG_FILE = os.path.join(LOGS_DIR, "openui.log")

_logger = logging.getLogger("openui")
_logger.setLevel(logging.INFO)
if not _logger.handlers:
    _handler = RotatingFileHandler(
        _LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_handler)


def _raw_write(text: str) -> None:
    """Write raw text directly to the log file — used for LLM stream chunks."""
    try:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(text)
    except Exception:
        pass


def _ts() -> str:
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).strftime("%H:%M:%S IST")


def _log(event: str, detail: str = "", elapsed_ms: float = 0.0) -> None:
    """Write one clean line to openui.log."""
    parts = [f"[{_ts()}]", f"[{event:<18}]"]
    if elapsed_ms:
        parts.append(f"({elapsed_ms:.0f}ms)")
    if detail:
        parts.append(detail)
    _logger.info("  ".join(parts))


def log_request_received(query: str) -> None:
    pass


def log_prompt_loaded(files: list, total_chars: int, prompt_hash: str) -> None:
    pass


def log_turn_telemetry(
    session_id: str,
    turn_number: int,
    user_query: str,
    system_files: List[str],
    domain_files: List[str],
    domain_newly_injected: bool,
    prompt_tokens: int,
    domain_tokens: int,
    history_tokens: int,
    total_tokens: int,
    context_window: int,
    remaining_tokens: int,
    compacted: bool = False,
) -> None:
    """Logs the turn start and context budget in exact chronological order."""
    _raw_write("\n\n\n" + ("=" * 80) + "\n")
    comp_tag = " [COMPACTION OCCURRED]" if compacted else ""
    _log("TURN START", f"Session: {session_id}  |  Turn #{turn_number}{comp_tag}")

    # 1. System Prompt (Anchor 1)
    sys_str = ", ".join(system_files)
    _log("SYSTEM PROMPT", f"[{sys_str}]  ({len(system_files)} files | ~{prompt_tokens:,} tokens)")

    # 2. Domain Schema & Skills (Anchor 2) - Only displayed when newly injected!
    if domain_newly_injected:
        dom_str = ", ".join(domain_files)
        _log("DOMAIN INJECT", f"[{dom_str}]  ({len(domain_files)} files | ~{domain_tokens:,} tokens) [1st-Query Priming]")

    # 3. User Query
    query_tokens = max(1, len(user_query) // 4)
    _log("USER QUERY", f'"{user_query}"  ({len(user_query)} chars | ~{query_tokens} tokens)')

    # 4. Pre-Call Context Budget
    free_pct = (remaining_tokens / context_window) * 100.0
    _log("PRE-CONTEXT", f"Used: ~{total_tokens:,} / {context_window:,} tokens  |  Remaining: ~{remaining_tokens:,} tokens ({free_pct:.1f}% free)")
    _raw_write(("-" * 80) + "\n")


def log_turn1_layout_start(model: str) -> None:
    _log("TURN 1 LAYOUT", f"Deciding Speculative Layout Wireframe with {model}...")


def log_turn1_layout_thinking_start() -> None:
    _raw_write(
        f"\n{'-' * 80}\n"
        f"[{_ts()}]  [TURN 1 THINKING START]  (layout reasoning begins)\n"
        f"{'-' * 80}\n"
    )


def log_turn1_layout_thinking_chunk(chunk: str) -> None:
    _raw_write(chunk)


def log_turn1_layout_thinking_end(total_chars: int, elapsed_ms: float = 0.0) -> None:
    dur_str = f" in {elapsed_ms/1000:.1f}s" if elapsed_ms > 0 else ""
    _raw_write(
        f"\n{'-' * 80}\n"
        f"[{_ts()}]  [TURN 1 THINKING END]  ({total_chars} chars reasoning{dur_str})\n"
        f"{'-' * 80}\n"
    )


def log_turn1_layout_stream_start() -> None:
    _raw_write(
        f"\n{'-' * 80}\n"
        f"[{_ts()}]  [TURN 1 WRITING START]  (wireframe AST streaming)\n"
        f"{'-' * 80}\n"
    )


def log_turn1_layout_stream_chunk(chunk: str) -> None:
    _raw_write(chunk)


def log_turn1_layout_stream_end(total_chars: int) -> None:
    _raw_write(
        f"\n{'-' * 80}\n"
        f"[{_ts()}]  [TURN 1 WRITING END]  ({total_chars} chars generated)\n"
        f"{'-' * 80}\n\n"
    )


def log_turn1_layout_completed(
    model: str, elapsed_ms: float, total_tokens: int, ttft_ms: float = 0.0,
    layout_ast: str = "", error: Optional[str] = None,
) -> None:
    """Logs Turn 1 Layout Decider throughput, tokens, and wireframe."""
    status = "ERROR" if error else "OK"
    stream_ms = max(0.0, elapsed_ms - ttft_ms)
    tps = round(total_tokens / (stream_ms / 1000), 1) if stream_ms > 0 else 0.0
    detail = f"opencode/{model}  |  {status}  |  ~{total_tokens:,} tokens generated ({stream_ms/1000:.1f}s stream)  |  {tps} tok/s"
    if error:
        detail += f"  |  {error[:120]}"
    _log("TURN 1 DONE", detail, elapsed_ms)
    if layout_ast:
        _raw_write(
            f"\n{'-' * 80}\n"
            f"[{_ts()}]  [TURN 1 WIREFRAME AST (SKELETON)]\n"
            f"{layout_ast}\n"
            f"{'-' * 80}\n\n"
        )


def log_layout_decided(layout_ast: str, elapsed_ms: float) -> None:
    """Legacy compatibility wrapper."""
    clean_layout = " ".join(layout_ast.split())
    _log("LAYOUT DECIDED", f"{clean_layout[:90]}...", elapsed_ms)


def log_llm_started(provider: str, model: str, temperature: float = 0.2, reasoning_effort: Optional[str] = None) -> None:
    effort_str = f"  |  reasoning_effort={reasoning_effort}" if reasoning_effort else ""
    _log("LLM START", f"{provider}/{model}  |  temp={temperature}{effort_str}")


def log_llm_ttft(elapsed_ms: float) -> None:
    _log("LLM TTFT", "First token received", elapsed_ms)


def log_llm_thinking_start() -> None:
    _raw_write(
        f"\n{'-' * 80}\n"
        f"[{_ts()}]  [LLM THINKING START]  (internal reasoning begins)\n"
        f"{'-' * 80}\n"
    )


def log_llm_thinking_chunk(chunk: str) -> None:
    _raw_write(chunk)


def log_llm_thinking_end(total_chars: int, elapsed_ms: float = 0.0) -> None:
    dur_str = f" in {elapsed_ms/1000:.1f}s" if elapsed_ms > 0 else ""
    _raw_write(
        f"\n{'-' * 80}\n"
        f"[{_ts()}]  [LLM THINKING END]  ({total_chars} chars reasoning{dur_str})\n"
        f"{'-' * 80}\n\n"
    )


def log_llm_stream_start() -> None:
    _raw_write(
        f"\n{'-' * 80}\n"
        f"[{_ts()}]  [LLM STREAM START]  (raw OpenUI AST stream begins)\n"
        f"{'-' * 80}\n"
    )


def log_llm_stream_chunk(chunk: str) -> None:
    _raw_write(chunk)


def log_llm_stream_end(total_chars: int) -> None:
    _raw_write(
        f"\n{'-' * 80}\n"
        f"[{_ts()}]  [LLM STREAM END]  ({total_chars:,} chars received)\n"
        f"{'-' * 80}\n"
    )


def log_llm_completed(
    provider: str, model: str, elapsed_ms: float,
    raw_tokens_est: int, ttft_ms: float = 0.0, error: Optional[str] = None,
    scaffold_tokens: int = 0,
) -> None:
    status = "ERROR" if error else "OK"
    gen_duration_sec = ((elapsed_ms - ttft_ms) / 1000.0) if (ttft_ms > 0 and elapsed_ms > ttft_ms) else (elapsed_ms / 1000.0)
    gen_tps = (raw_tokens_est / gen_duration_sec) if gen_duration_sec > 0 else 0.0
    
    saved_str = ""
    if scaffold_tokens > 0:
        saved_tokens = max(0, scaffold_tokens - 10)
        saved_pct = round((saved_tokens / (scaffold_tokens + raw_tokens_est)) * 100.0, 1) if (scaffold_tokens + raw_tokens_est) > 0 else 0.0
        saved_str = f"  |  Saved ~{saved_tokens} rewrite tokens ({saved_pct}%)"

    detail = f"{provider}/{model}  |  {status}  |  ~{raw_tokens_est:,} update tokens ({gen_duration_sec:.1f}s stream)  |  {gen_tps:.1f} tok/s{saved_str}"
    if error:
        detail += f"  |  {error[:120]}"
    _log("DELTA UPDATE", detail, elapsed_ms)


def log_ast_processing(raw_lines: int, processed_lines: int, modified: bool) -> None:
    change = "MODIFIED" if modified else "CLEAN (no changes)"
    _log("AST POST-PROC", f"{change}  |  {raw_lines} -> {processed_lines} lines")


def log_renderer_started(query_nodes: int, visual_components: int, ast_lines: int) -> None:
    _log("RENDERER START", f"{query_nodes} Query nodes  |  {visual_components} visual components  |  {ast_lines} AST lines")


def log_post_context_budget(
    output_tokens: int,
    total_tokens: int,
    context_window: int,
    remaining_tokens: int,
    turn_duration_ms: float,
) -> None:
    """Logs context window budget AFTER the LLM call completes (including output tokens)."""
    _raw_write(("-" * 80) + "\n")
    free_pct = (remaining_tokens / context_window) * 100.0
    _log("POST-CONTEXT", f"Used: ~{total_tokens:,} / {context_window:,} tokens  |  Remaining: ~{remaining_tokens:,} tokens ({free_pct:.1f}% free)")
    _log("TURN END", f"Turn completed in {turn_duration_ms/1000:.1f}s")
    _raw_write(("=" * 80) + "\n\n\n")


def log_db_query(sql: str, elapsed_ms: float, row_count: int, error: Optional[str] = None) -> None:
    status = "ERR" if error else "OK"
    detail = f"({elapsed_ms:.0f}ms)  {status}  {row_count} rows  |  {sql[:100]}"
    if error:
        detail += f"  |  {error[:80]}"
    _log("DB QUERY", detail)
