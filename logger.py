import os
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

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


# ── Timeline events ───────────────────────────────────────────────────────────

def log_request_received(query: str) -> None:
    _raw_write("\n\n\n\n" + ("═" * 72) + "\n")
    _log("REQUEST RECV", f'"{query[:120]}"  ({len(query)} chars)')


def log_prompt_loaded(files: list, total_chars: int, prompt_hash: str) -> None:
    token_est = total_chars // 4
    files_str = ", ".join(files) if files else "openui_prompt.txt (fallback)"
    _log("PROMPT LOADED",
         f"{len(files)} files  |  {total_chars:,} chars (~{token_est:,} tokens)  |  hash={prompt_hash[:8]}")
    _log("PROMPT FILES", files_str)


def log_llm_started(provider: str, model: str, temperature: float = 0.2) -> None:
    _log("LLM START", f"{provider}/{model}  |  temp={temperature}")


def log_llm_ttft(elapsed_ms: float) -> None:
    _log("LLM TTFT", "First token received", elapsed_ms)


def log_llm_thinking_start() -> None:
    """Write the LLM thinking header — everything until THINKING END is raw reasoning."""
    _raw_write(
        f"\n{'─' * 72}\n"
        f"[{_ts()}]  [LLM THINKING ▼ START]  (internal reasoning begins)\n"
        f"{'─' * 72}\n"
    )


def log_llm_thinking_chunk(chunk: str) -> None:
    """Write raw reasoning tokens directly to log."""
    _raw_write(chunk)


def log_llm_thinking_end(total_chars: int, elapsed_ms: float = 0.0) -> None:
    """Write the LLM thinking footer."""
    dur_str = f" in {elapsed_ms/1000:.1f}s" if elapsed_ms > 0 else ""
    _raw_write(
        f"\n{'─' * 72}\n"
        f"[{_ts()}]  [LLM THINKING ▲ END]  ({total_chars} chars reasoning{dur_str})\n"
        f"{'─' * 72}\n\n"
    )


def log_llm_stream_start() -> None:
    """Write the LLM stream header — everything until STREAM END is raw LLM output."""
    _raw_write(
        f"\n{'─' * 72}\n"
        f"[{_ts()}]  [LLM STREAM ▼ START]  (raw output begins)\n"
        f"{'─' * 72}\n"
    )


def log_llm_stream_chunk(chunk: str) -> None:
    """Write a raw LLM chunk directly — no timestamp, live output."""
    _raw_write(chunk)


def log_llm_stream_end(total_chars: int) -> None:
    """Write the LLM stream footer after all tokens have arrived."""
    _raw_write(
        f"\n{'─' * 72}\n"
        f"[{_ts()}]  [LLM STREAM ▲ END]  ({total_chars} chars received)\n"
        f"{'─' * 72}\n\n"
    )


def log_llm_completed(provider: str, model: str, elapsed_ms: float,
                       raw_tokens_est: int, ttft_ms: float = 0.0, error: Optional[str] = None) -> None:
    status = "ERROR" if error else "OK"
    # Generation duration is the streaming decode phase: (total elapsed - TTFT prefill)
    gen_duration_sec = ((elapsed_ms - ttft_ms) / 1000.0) if (ttft_ms > 0 and elapsed_ms > ttft_ms) else (elapsed_ms / 1000.0)
    gen_tps = (raw_tokens_est / gen_duration_sec) if gen_duration_sec > 0 else 0.0
    detail = f"{provider}/{model}  |  {status}  |  ~{raw_tokens_est} tokens generated ({gen_duration_sec:.1f}s stream)  |  {gen_tps:.1f} tok/s"
    if error:
        detail += f"  |  {error[:120]}"
    _log("LLM DONE", detail, elapsed_ms)


def log_ast_processing(raw_lines: int, processed_lines: int, modified: bool) -> None:
    change = "MODIFIED" if modified else "CLEAN (no changes)"
    _log("AST POST-PROC", f"{change}  |  {raw_lines} → {processed_lines} lines")


def log_db_query(sql: str, elapsed_ms: float, row_count: int,
                 error: Optional[str] = None) -> None:
    status = "ERR" if error else "OK"
    detail = f"({elapsed_ms:.0f}ms)  {status}  {row_count} rows  |  {sql[:100]}"
    if error:
        detail += f"  |  {error[:80]}"
    _log("DB QUERY", detail)


def log_renderer_started(query_nodes: int, visual_components: int, ast_lines: int) -> None:
    _log("RENDERER START",
         f"{query_nodes} Query nodes  |  {visual_components} visual components  |  {ast_lines} AST lines")
