"""
Tool functions the ADK agents call.

Each one is a thin HTTP wrapper around the FastAPI backend in
`backend/` — the same "tools layer" the Gemini Enterprise console
would have called over the tunnel. Keeping the backend as the single
source of truth means the risk cap, the signed approval token and the
Firestore audit log are enforced server-side no matter which client
(ADK, Gemini Enterprise, or Cloud Scheduler) is driving.

Every function returns a plain dict so the model can read it directly.
Errors are returned as {"error": ...} rather than raised, so an agent
can explain a failure to the user instead of the run blowing up.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

# backend/.env holds BACKEND_API_KEY — the same shared secret the
# backend checks on every call.
_ENV_PATH = Path(__file__).resolve().parent.parent / "backend" / ".env"
load_dotenv(_ENV_PATH)

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
_API_KEY = os.getenv("BACKEND_API_KEY", "")
_TIMEOUT = 90


def _headers() -> dict[str, str]:
    return {"X-Backend-Api-Key": _API_KEY, "Content-Type": "application/json"}


def _get(path: str) -> dict[str, Any]:
    try:
        r = requests.get(f"{BACKEND_URL}{path}", headers=_headers(), timeout=_TIMEOUT)
        if r.status_code >= 400:
            return {"error": f"HTTP {r.status_code}", "detail": r.text[:500]}
        return r.json()
    except Exception as exc:  # network/timeouts surface as readable text
        return {"error": str(exc)}


def _post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        r = requests.post(f"{BACKEND_URL}{path}", headers=_headers(), json=payload, timeout=_TIMEOUT)
        if r.status_code >= 400:
            return {"error": f"HTTP {r.status_code}", "detail": r.text[:500]}
        return r.json()
    except Exception as exc:
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Market data / account
# ---------------------------------------------------------------------------

def get_account_summary() -> dict:
    """Get the connected MT5 demo account's balance, equity and currency.

    Use this to tell the user how much capital they have before sizing a
    trade. Returns login, balance, equity, currency and is_demo.
    """
    return _get("/account-summary")


def get_quote(symbol: str) -> dict:
    """Get the current bid/ask quote for one trading symbol.

    Args:
        symbol: Trading symbol, e.g. "EURUSD", "GBPUSD", "XAUUSD".
    """
    return _get(f"/quote/{symbol}")


# ---------------------------------------------------------------------------
# Trading Desk — technical analysis
# ---------------------------------------------------------------------------

def analyze_technical(symbol: str, timeframe: str = "H1", strategy_name: str = "") -> dict:
    """Run the Trading Desk technical strategies on a symbol and get signals.

    Runs deterministic Python strategy logic (Order Block/SMC structure,
    RSI divergence, currency strength, Heikin-Ashi trend, CCI+EMA) over
    live MT5 candles and returns a consensus signal plus each strategy's
    own signal, confidence, reasoning and key price levels.

    Args:
        symbol: Trading symbol, e.g. "EURUSD".
        timeframe: Candle timeframe, e.g. "M15", "H1", "H4", "D1". Defaults to "H1".
        strategy_name: Optional single preset to run instead of all of them.
            One of: order_block_smc, rsi_divergence, currency_strength,
            heikin_ashi_trend, cci_ema_strategy. Empty string runs all
            of them and returns the confluence view.
    """
    payload: dict[str, Any] = {"symbol": symbol, "timeframe": timeframe}
    if strategy_name:
        payload["strategy_name"] = strategy_name
    return _post("/analyze-technical", payload)


# ---------------------------------------------------------------------------
# Investment Desk — value/quality screen
# ---------------------------------------------------------------------------

def analyze_investment(
    symbol: str,
    pe_ratio: float = -1.0,
    debt_to_equity: float = -1.0,
    return_on_equity: float = -1.0,
    revenue_growth_5y: float = -1.0,
    earnings_growth_5y: float = -1.0,
    free_cash_flow_positive_years: int = -1,
    gross_margin: float = -1.0,
) -> dict:
    """Screen one stock against the transparent value/quality rules.

    Checks low debt, strong return on equity, consistent earnings growth
    and positive free cash flow, and returns a pass/fail breakdown per
    rule plus a verdict. Ask the user for any fundamentals you do not
    have — pass -1 for anything genuinely unknown, and say which inputs
    were missing when you explain the result. Always relay the
    `disclaimer` field back to the user verbatim.

    Args:
        symbol: Ticker, e.g. "AAPL".
        pe_ratio: Price/earnings ratio. -1 if unknown.
        debt_to_equity: Debt-to-equity ratio. -1 if unknown.
        return_on_equity: ROE as a percentage, e.g. 35.0. -1 if unknown.
        revenue_growth_5y: 5-year revenue growth percentage. -1 if unknown.
        earnings_growth_5y: 5-year earnings growth percentage. -1 if unknown.
        free_cash_flow_positive_years: Count of recent years with positive FCF. -1 if unknown.
        gross_margin: Gross margin percentage. -1 if unknown.
    """
    candidate: dict[str, Any] = {"symbol": symbol}
    optional = {
        "pe_ratio": pe_ratio,
        "debt_to_equity": debt_to_equity,
        "return_on_equity": return_on_equity,
        "revenue_growth_5y": revenue_growth_5y,
        "earnings_growth_5y": earnings_growth_5y,
        "gross_margin": gross_margin,
    }
    for key, value in optional.items():
        if value is not None and value >= 0:
            candidate[key] = value
    if free_cash_flow_positive_years is not None and free_cash_flow_positive_years >= 0:
        candidate["free_cash_flow_positive_years"] = free_cash_flow_positive_years

    return _post("/analyze-investment", {"candidates": [candidate]})


# ---------------------------------------------------------------------------
# Strategy Builder — presets and natural-language custom strategies
# ---------------------------------------------------------------------------

def save_strategy(user_id: str, name: str, desk: str, mode: str, definition: dict) -> dict:
    """Save a strategy (preset selection or custom, user-described one) to Firestore.

    Args:
        user_id: The user this strategy belongs to, e.g. "muneeb".
        name: Human-readable strategy name to show the user later.
        desk: Either "trading" or "investment".
        mode: Either "preset" (one of the built-ins) or "custom" (described by the user).
        definition: Structured definition. For a preset use
            {"strategy_name": "order_block_smc", "timeframe": "H1"}. For a
            custom strategy capture the user's rules as fields such as
            description, entry_rule, stop_loss and take_profit.
    """
    return _post("/save-strategy", {
        "user_id": user_id, "name": name, "desk": desk, "mode": mode, "definition": definition,
    })


def list_strategies(user_id: str) -> dict:
    """List every strategy this user has saved.

    Args:
        user_id: The user, e.g. "muneeb".
    """
    return _get(f"/strategies/{user_id}")


def set_watchlist_entry(user_id: str, symbol: str, desk: str, strategy_id: str) -> dict:
    """Put a symbol on the user's watchlist, bound to a saved strategy.

    Watchlist entries are what the daily report iterates over each morning.

    Args:
        user_id: The user, e.g. "muneeb".
        symbol: Symbol to watch, e.g. "EURUSD" or "AAPL".
        desk: Either "trading" or "investment".
        strategy_id: The id returned by save_strategy or shown by list_strategies.
    """
    return _post("/watchlist", {
        "user_id": user_id, "symbol": symbol, "desk": desk, "strategy_id": strategy_id,
    })


def get_watchlist(user_id: str) -> dict:
    """Get the user's current watchlist.

    Args:
        user_id: The user, e.g. "muneeb".
    """
    return _get(f"/watchlist/{user_id}")


# ---------------------------------------------------------------------------
# Risk & Execution — the security-critical pair
# ---------------------------------------------------------------------------

def risk_size(user_id: str, symbol: str, direction: str, stop_loss_pips: float) -> dict:
    """Run the mandatory risk check and get a position size for a trade.

    This is the ONLY way to obtain an `approval_token`, and the backend
    will not execute any order without one. Returns approved (true/false),
    the computed lot_size, the dollar risk, the remaining daily budget,
    and a reason when rejected.

    Args:
        user_id: The user, e.g. "muneeb".
        symbol: Symbol to trade, e.g. "EURUSD".
        direction: Either "buy" or "sell".
        stop_loss_pips: Distance to the stop loss in pips. Must be > 0.
    """
    return _post("/risk-size", {
        "user_id": user_id, "symbol": symbol, "direction": direction, "stop_loss_pips": stop_loss_pips,
    })


def execute_order(
    approval_token: str,
    stop_loss_price: float = -1.0,
    take_profit_price: float = -1.0,
    comment: str = "investment-desk",
) -> dict:
    """Place the approved order on the MT5 demo account.

    Requires a fresh, unused `approval_token` from risk_size. The backend
    rejects invalid, expired or already-used tokens with HTTP 403 — never
    invent a token, and never call this without calling risk_size first
    and getting approved: true.

    Args:
        approval_token: The token returned by risk_size.
        stop_loss_price: Absolute stop-loss price. -1 to omit.
        take_profit_price: Absolute take-profit price. -1 to omit.
        comment: Order comment recorded on the trade.
    """
    payload: dict[str, Any] = {"approval_token": approval_token, "comment": comment}
    if stop_loss_price is not None and stop_loss_price > 0:
        payload["stop_loss_price"] = stop_loss_price
    if take_profit_price is not None and take_profit_price > 0:
        payload["take_profit_price"] = take_profit_price
    return _post("/execute-order", payload)


# ---------------------------------------------------------------------------
# Reporting / observability
# ---------------------------------------------------------------------------

def daily_report(user_id: str) -> dict:
    """Generate the personalized daily report for the user.

    Walks the user's watchlist, runs each symbol's strategies against live
    market data, and returns the account state, the risk budget used today
    and a per-symbol signal breakdown. This is the same endpoint the 8am
    scheduled trigger calls.

    Args:
        user_id: The user, e.g. "muneeb".
    """
    return _post("/daily-report", {"user_id": user_id})


def get_audit_log(user_id: str) -> dict:
    """Read the append-only audit log of every agent action taken for this user.

    Use this to show the user exactly what the fleet did and when —
    approvals, rejections and orders are all recorded here.

    Args:
        user_id: The user, e.g. "muneeb".
    """
    return _get(f"/audit-log/{user_id}")
