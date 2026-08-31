from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from db import execute_safe_sql


class SqlQueryInput(BaseModel):
    sql: str = Field(description="Standard PostgreSQL SELECT query")
    max_rows: Optional[int] = Field(default=50, description="Max rows to return (default 50)")


@tool("sql_query", args_schema=SqlQueryInput)
def sql_query_tool(sql: str, max_rows: int = 50) -> Dict[str, Any]:
    """
    Universal safe PostgreSQL read-only query tool.
    Executes any dynamic SELECT query against the auto-discovered database schema.
    """
    return execute_safe_sql(sql_query=sql, max_rows=max_rows)


# Single Universal Tool for LangChain Agents & Orchestrator
ALL_OPENUI_TOOLS = [sql_query_tool]
