"""
FastAPI backend — the set of "tools"/"actions" the Gemini Enterprise
agents call. Runs on Muneeb's Windows machine (see README) so it can
talk to the MT5 terminal directly, and is exposed to Gemini
Enterprise / Cloud Scheduler via a tunnel (Cloudflare Tunnel or
ngrok) for the hackathon demo.

Every state-changing call is written to the Firestore audit log
(backend/firestore_client.py) — this is the "observability" story for
the Fortified Enterprise Fleet judging criterion.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Header, HTTPException

from . import firestore_client as fs
from . import mt5_client
from . import reporting
from . import risk
from .config import settings
from .models import (
    AnalyzeInvestmentRequest,
    AnalyzeTechnicalRequest,
    DailyReportRequest,
    ExecuteOrderRequest,
    RiskSizeRequest,
    SaveStrategyRequest,
    WatchlistEntryRequest,
)
from .strategies_bridge import run_all_technical_presets, run_preset, screen_many, Fundamentals

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("investment_desk")

app = FastAPI(title="Investment Desk — Fortified Enterprise Fleet backend")


def _check_auth(x_backend_api_key: str | None) -> None:
    if not settings.BACKEND_API_KEY:
        logger.warning("BACKEND_API_KEY is not set — refusing all requests until it's configured.")
        raise HTTPException(status_code=503, detail="Backend not configured: set BACKEND_API_KEY in .env")
    if x_backend_api_key != settings.BACKEND_API_KEY:
        raise HTTPException(status_code=401, detail="Missing or invalid X-Backend-Api-Key header")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/account-summary")
def account_summary(x_backend_api_key: str | None = Header(None)):
    _check_auth(x_backend_api_key)
    return mt5_client.get_account_summary()


@app.get("/quote/{symbol}")
def quote(symbol: str, x_backend_api_key: str | None = Header(None)):
    _check_auth(x_backend_api_key)
    return mt5_client.get_quote(symbol)


# --------------------------------------------------------------------------
# Technical Analyst Agent (Trading Desk)
# --------------------------------------------------------------------------

@app.post("/analyze-technical")
def analyze_technical(req: AnalyzeTechnicalRequest, x_backend_api_key: str | None = Header(None)):
    _check_auth(x_backend_api_key)
    candles = mt5_client.get_candles(req.symbol, req.timeframe, 300)

    if req.strategy_name:
        result = run_preset(req.strategy_name, candles)
        results = [result]
    else:
        results = run_all_technical_presets(candles)

    buys = sum(1 for r in results if r["signal"] == "buy")
    sells = sum(1 for r in results if r["signal"] == "sell")
    consensus = "buy" if buys > sells else "sell" if sells > buys else "none"

    return {"symbol": req.symbol, "timeframe": req.timeframe, "consensus_signal": consensus, "results": results}


# --------------------------------------------------------------------------
# Investment Analyst Agent (Investment Desk)
# --------------------------------------------------------------------------

@app.post("/analyze-investment")
def analyze_investment(req: AnalyzeInvestmentRequest, x_backend_api_key: str | None = Header(None)):
    _check_auth(x_backend_api_key)
    fundamentals = [Fundamentals(**c.model_dump()) for c in req.candidates]
    return {"results": screen_many(fundamentals)}


# --------------------------------------------------------------------------
# Strategy Builder Agent — saves preset selections AND natural-language
# -derived custom strategies
# --------------------------------------------------------------------------

@app.post("/save-strategy")
def save_strategy(req: SaveStrategyRequest, x_backend_api_key: str | None = Header(None)):
    _check_auth(x_backend_api_key)
    strategy_id = fs.save_strategy(req.user_id, req.name, req.desk, req.mode, req.definition)
    fs.append_audit_log(req.user_id, "strategy_builder_agent", "save_strategy", {"strategy_id": strategy_id, "name": req.name})
    return {"strategy_id": strategy_id}


@app.get("/strategies/{user_id}")
def list_strategies(user_id: str, x_backend_api_key: str | None = Header(None)):
    _check_auth(x_backend_api_key)
    return {"strategies": fs.list_strategies(user_id)}


@app.post("/watchlist")
def set_watchlist(req: WatchlistEntryRequest, x_backend_api_key: str | None = Header(None)):
    _check_auth(x_backend_api_key)
    fs.set_watchlist_entry(req.user_id, req.symbol, req.desk, req.strategy_id)
    return {"ok": True}


@app.get("/watchlist/{user_id}")
def get_watchlist(user_id: str, x_backend_api_key: str | None = Header(None)):
    _check_auth(x_backend_api_key)
    return {"watchlist": fs.get_watchlist(user_id)}


# --------------------------------------------------------------------------
# Risk & Sizing Agent — the only path to an order approval token
# --------------------------------------------------------------------------

@app.post("/risk-size")
def risk_size(req: RiskSizeRequest, x_backend_api_key: str | None = Header(None)):
    _check_auth(x_backend_api_key)
    return risk.approve_or_reject(req.user_id, req.symbol, req.direction, req.stop_loss_pips)


# --------------------------------------------------------------------------
# Execution Agent — ONLY accepts a valid, unexpired risk-approval token
# --------------------------------------------------------------------------

@app.post("/execute-order")
def execute_order(req: ExecuteOrderRequest, x_backend_api_key: str | None = Header(None)):
    _check_auth(x_backend_api_key)
    payload = risk.consume_approval(req.approval_token)
    if payload is None:
        raise HTTPException(status_code=403, detail="Invalid, expired, or already-used risk approval token.")

    result = mt5_client.place_order(
        symbol=payload["symbol"],
        direction=payload["direction"],
        lot_size=payload["lot_size"],
        stop_loss=req.stop_loss_price,
        take_profit=req.take_profit_price,
        comment=req.comment,
    )
    fs.append_audit_log(
        payload["user_id"], "execution_agent", "place_order",
        {"symbol": payload["symbol"], "direction": payload["direction"], "lot_size": payload["lot_size"], "result": result},
    )
    return result


# --------------------------------------------------------------------------
# Reporting Agent
# --------------------------------------------------------------------------

@app.post("/daily-report")
def daily_report(req: DailyReportRequest, x_backend_api_key: str | None = Header(None)):
    _check_auth(x_backend_api_key)
    return reporting.generate_daily_report(req.user_id)


@app.get("/audit-log/{user_id}")
def audit_log(user_id: str, x_backend_api_key: str | None = Header(None)):
    _check_auth(x_backend_api_key)
    return {"entries": fs.get_audit_log(user_id)}
