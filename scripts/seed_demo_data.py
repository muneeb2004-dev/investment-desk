"""
Seeds Firestore with enough demo data that the app isn't starting from
a blank slate when you sit down to build the Gemini Enterprise agents
or record the demo video.

Run this AFTER backend/.env is filled in (it reads GOOGLE_CLOUD_PROJECT
from there) and you've run `gcloud auth application-default login`
(or set GOOGLE_APPLICATION_CREDENTIALS):

    python scripts/seed_demo_data.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import firestore_client as fs  # noqa: E402

USER_ID = "muneeb"


def main():
    print(f"Seeding demo data for user_id={USER_ID} ...")

    fs.set_risk_profile(USER_ID, daily_loss_cap_pct=2.0, risk_per_trade_pct=0.5)
    print("  risk profile set: 2% daily loss cap, 0.5% risk per trade")

    smc_id = fs.save_strategy(
        USER_ID, name="Order Block / SMC (preset)", desk="trading", mode="preset",
        definition={"strategy_name": "order_block_smc", "timeframe": "H1"},
    )
    ha_id = fs.save_strategy(
        USER_ID, name="Heikin-Ashi trend (preset)", desk="trading", mode="preset",
        definition={"strategy_name": "heikin_ashi_trend", "timeframe": "H1"},
    )
    custom_id = fs.save_strategy(
        USER_ID, name="Breakout above prior day high + RSI>50 (custom)", desk="trading", mode="custom",
        definition={
            "description": "Buy when price closes above the previous day's high while RSI(14) is above 50.",
            "entry_rule": "close > prev_day_high and rsi_14 > 50",
            "stop_loss": "below the breakout candle's low",
            "take_profit": "2x the stop-loss distance",
        },
    )
    value_id = fs.save_strategy(
        USER_ID, name="Value/Quality screen (preset)", desk="investment", mode="preset",
        definition={"strategy_name": "value_quality_screen"},
    )
    print(f"  saved strategies: {smc_id}, {ha_id}, {custom_id}, {value_id}")

    fs.set_watchlist_entry(USER_ID, "EURUSD", desk="trading", strategy_id=smc_id)
    fs.set_watchlist_entry(USER_ID, "GBPUSD", desk="trading", strategy_id=ha_id)
    fs.set_watchlist_entry(USER_ID, "AAPL", desk="investment", strategy_id=value_id)
    print("  watchlist set: EURUSD (SMC), GBPUSD (Heikin-Ashi), AAPL (value screen)")

    fs.append_audit_log(USER_ID, "seed_script", "initialize_demo_data", {"note": "seeded for hackathon demo"})
    print("Done. Open Firestore in the GCP console to see it, or call GET /strategies/muneeb "
          "and GET /watchlist/muneeb on the running backend to confirm.")


if __name__ == "__main__":
    main()
