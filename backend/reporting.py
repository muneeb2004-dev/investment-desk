"""
Reporting Agent — builds the personalized daily feed. Triggered by
Cloud Scheduler hitting POST /daily-report at 8am, but callable
on-demand too (which is how you'll trigger it live during the demo
video instead of waiting for 8am).
"""

from __future__ import annotations

import datetime as dt

from . import firestore_client as fs
from . import mt5_client
from .strategies_bridge import run_all_technical_presets


def generate_daily_report(user_id: str) -> dict:
    watchlist = fs.get_watchlist(user_id)
    account = mt5_client.get_account_summary()
    risk_state = fs.get_today_risk_state(user_id)
    profile = fs.get_risk_profile(user_id)

    items = []
    for entry in watchlist:
        symbol = entry["symbol"]
        try:
            if entry["desk"] == "trading":
                candles = mt5_client.get_candles(symbol, "H1", 300)
                results = run_all_technical_presets(candles)
                buys = sum(1 for r in results if r["signal"] == "buy")
                sells = sum(1 for r in results if r["signal"] == "sell")
                consensus = "buy" if buys > sells else "sell" if sells > buys else "none"
                items.append(
                    {
                        "symbol": symbol,
                        "desk": "trading",
                        "consensus_signal": consensus,
                        "strategy_votes": {r["strategy"]: r["signal"] for r in results},
                        "details": results,
                    }
                )
            else:
                # Investment desk items are scored elsewhere (fundamentals
                # come from the caller / a market-data provider); here we
                # just surface the last saved screen result if present.
                items.append({"symbol": symbol, "desk": "investment", "note": "Run /analyze-investment for a fresh score."})
        except Exception as exc:  # keep the report resilient to one bad symbol
            items.append({"symbol": symbol, "desk": entry["desk"], "error": str(exc)})

    report = {
        "user_id": user_id,
        "date": dt.date.today().isoformat(),
        "account_balance": account["balance"],
        "account_equity": account["equity"],
        "daily_loss_cap_pct": profile["daily_loss_cap_pct"],
        "risk_used_today": risk_state["risk_committed_today"],
        "realized_pnl_today": risk_state["realized_pnl_today"],
        "watchlist_items": items,
    }
    fs.save_report(user_id, report)
    fs.append_audit_log(user_id, "reporting_agent", "generate_daily_report", {"symbols": [i["symbol"] for i in items]})
    return report
