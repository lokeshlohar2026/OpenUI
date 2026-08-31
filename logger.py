import os
import time
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Any, Dict, Optional

# Ensure logs directory exists
LOGS_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# General App Logger
app_logger = logging.getLogger("openui_app")
app_logger.setLevel(logging.INFO)
if not app_logger.handlers:
    app_handler = RotatingFileHandler(
        os.path.join(LOGS_DIR, "app.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    app_formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    app_handler.setFormatter(app_formatter)
    app_logger.addHandler(app_handler)

# Dedicated DB Calls Logger
db_logger = logging.getLogger("openui_db")
db_logger.setLevel(logging.INFO)
if not db_logger.handlers:
    db_handler = RotatingFileHandler(
        os.path.join(LOGS_DIR, "db.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    db_formatter = logging.Formatter(
        "[%(asctime)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    db_handler.setFormatter(db_formatter)
    db_logger.addHandler(db_handler)

# Dedicated LLM Interactions Logger
llm_logger = logging.getLogger("openui_llm")
llm_logger.setLevel(logging.INFO)
if not llm_logger.handlers:
    llm_handler = RotatingFileHandler(
        os.path.join(LOGS_DIR, "llm.log"),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    llm_formatter = logging.Formatter(
        "[%(asctime)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    llm_handler.setFormatter(llm_formatter)
    llm_logger.addHandler(llm_handler)


def log_db_query(
    sql: str,
    row_count: int,
    elapsed_ms: float,
    error: Optional[str] = None,
    cached: bool = False,
    repaired_from: Optional[str] = None,
    sample_data: Optional[Any] = None,
):
    """Logs database query execution with full telemetry."""
    status = "ERROR" if error else ("CACHED" if cached else "SUCCESS")
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "status": status,
        "elapsed_ms": elapsed_ms,
        "row_count": row_count,
        "sql": sql,
        "error": error,
        "repaired_from": repaired_from,
        "sample_preview": sample_data[:2] if isinstance(sample_data, list) else sample_data,
    }
    
    msg_lines = [
        f"─── [DB QUERY: {status}] ─── ({elapsed_ms} ms, {row_count} rows)",
        f"SQL: {sql}",
    ]
    if repaired_from:
        msg_lines.append(f"Auto-Repaired From: {repaired_from}")
    if error:
        msg_lines.append(f"Error: {error}")
    else:
        msg_lines.append(f"Sample Data: {json.dumps(sample_data[:2] if isinstance(sample_data, list) else sample_data, default=str)}")
    msg_lines.append("────────────────────────────────────────────────────────────")
    
    db_logger.info("\n".join(msg_lines))
    app_logger.info(f"DB [{status}] {elapsed_ms}ms | rows: {row_count} | SQL: {sql[:100]}...")


def log_llm_interaction(
    provider: str,
    model: str,
    user_query: str,
    generated_code: str,
    elapsed_ms: float,
    error: Optional[str] = None,
):
    """Logs LLM interaction including prompt query, generated OpenUI code, and latency."""
    status = "ERROR" if error else "SUCCESS"
    msg_lines = [
        f"─── [LLM CALL: {status}] ─── ({provider} / {model} in {elapsed_ms} ms)",
        f"User Query: {user_query}",
        "Generated OpenUI AST Code:",
        generated_code if generated_code else "(empty)",
    ]
    if error:
        msg_lines.append(f"Error: {error}")
    msg_lines.append("────────────────────────────────────────────────────────────")
    
    llm_logger.info("\n".join(msg_lines))
    app_logger.info(f"LLM [{status}] {provider}/{model} in {elapsed_ms}ms | query: '{user_query}'")
