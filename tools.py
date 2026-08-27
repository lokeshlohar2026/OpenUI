from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from db import (
    get_portfolio_holdings,
    get_market_cap_allocation,
    get_aum_history,
    get_fund_overview,
)


class FundSearchInput(BaseModel):
    q: str = Field(description="Fund or AMC name substring, e.g. 'HDFC Flexi Cap', 'SBI Bluechip'")


class PortfolioHoldingsInput(FundSearchInput):
    limit: Optional[int] = Field(
        default=0,
        description="Max holdings rows to return (default 0 returns all holdings)",
    )


class AumHistoryInput(FundSearchInput):
    limit: Optional[int] = Field(
        default=24,
        description="Number of monthly records to return (default 24)",
    )


@tool("portfolio_holdings", args_schema=PortfolioHoldingsInput)
def portfolio_holdings_tool(q: str, limit: int = 0) -> Dict[str, Any]:
    """
    Get portfolio stock holdings and percentage of net asset for any mutual fund.
    Returns { holdings: [{ company_name: str, percentage_in_net_asset: float, portfolio_date: str }] }.
    """
    return get_portfolio_holdings(q=q, limit=limit)


@tool("market_cap_allocation", args_schema=FundSearchInput)
def market_cap_allocation_tool(q: str) -> Dict[str, Any]:
    """
    Get Market Cap allocation (Large Cap, Mid Cap, Small Cap % breakdown) for a mutual fund.
    Returns { allocation: [{ name: str, value: float }] }.
    """
    return get_market_cap_allocation(q=q)


@tool("aum_history", args_schema=AumHistoryInput)
def aum_history_tool(q: str, limit: int = 24) -> Dict[str, Any]:
    """
    Get monthly AUM history (in ₹ Cr) over time for fund growth trajectory line charts.
    Returns { history: [{ date: str, aum: float }] }.
    """
    return get_aum_history(q=q, limit=limit)


@tool("fund_overview", args_schema=FundSearchInput)
def fund_overview_tool(q: str) -> Dict[str, Any]:
    """
    Get mutual fund metadata (Total AUM, Nature, Sub Nature, Riskometer, Fund Managers).
    Returns { overview: { fund_name: str, aum_cr: str, nature: str, sub_nature: str, riskometer: str, managers: str } }.
    """
    return get_fund_overview(q=q)


# Exported list of all OpenUI tools ready to be passed directly to any LangChain Agent or Orchestrator
ALL_OPENUI_TOOLS = [
    portfolio_holdings_tool,
    market_cap_allocation_tool,
    aum_history_tool,
    fund_overview_tool,
]
