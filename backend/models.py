from typing import Any, Literal

from pydantic import BaseModel


class AnalyzeTechnicalRequest(BaseModel):
    symbol: str
    timeframe: str = "H1"
    strategy_name: str | None = None  # None = run all presets (confluence view)


class InvestmentCandidate(BaseModel):
    symbol: str
    pe_ratio: float | None = None
    debt_to_equity: float | None = None
    return_on_equity: float | None = None
    revenue_growth_5y: float | None = None
    earnings_growth_5y: float | None = None
    free_cash_flow_positive_years: int | None = None
    gross_margin: float | None = None


class AnalyzeInvestmentRequest(BaseModel):
    candidates: list[InvestmentCandidate]


class SaveStrategyRequest(BaseModel):
    user_id: str
    name: str
    desk: Literal["trading", "investment"]
    mode: Literal["preset", "custom"]
    definition: dict[str, Any]


class RiskSizeRequest(BaseModel):
    user_id: str
    symbol: str
    direction: Literal["buy", "sell"]
    stop_loss_pips: float


class ExecuteOrderRequest(BaseModel):
    approval_token: str
    stop_loss_price: float | None = None
    take_profit_price: float | None = None
    comment: str = "investment-desk"


class WatchlistEntryRequest(BaseModel):
    user_id: str
    symbol: str
    desk: Literal["trading", "investment"]
    strategy_id: str


class DailyReportRequest(BaseModel):
    user_id: str
