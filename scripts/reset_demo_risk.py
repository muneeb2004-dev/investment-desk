"""
Administrative reset of a user's daily risk budget.

Risk is committed at APPROVAL time (see risk.consume_approval), not at
fill time — a rejected or failed order still consumes budget, because the
capital was formally committed the moment the token was issued. That is
deliberate: it fails closed. The practical consequence is that testing
against a live cap will exhaust the day's budget, and this script is how
you clear it between test runs.

    # clear today's committed risk, leave the configured cap alone
    python scripts/reset_demo_risk.py

    # clear it and change the cap at the same time
    python scripts/reset_demo_risk.py --cap 0.5

The cap is expressed as a percentage of account balance. At the default
2% on a $100k account the cap is $2,000, and at 0.5% risk per trade each
order commits $500 — so four orders clear and the fifth is refused.
Lowering --cap tightens that: at 0.5% the cap is $500, so the second
order is refused. Useful for exercising the rejection path directly
instead of placing four orders to reach it.

Every reset is itself written to the audit log, so the budget cannot be
quietly cleared without leaving a trace.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import firestore_client as fs  # noqa: E402

USER_ID = "muneeb"


def main():
    ap = argparse.ArgumentParser(description="Reset today's demo risk budget.")
    ap.add_argument("--user", default=USER_ID, help='user_id to reset (default: "muneeb")')
    ap.add_argument("--cap", type=float, default=None,
                    help="also set the daily loss cap, as a percent of balance (e.g. 0.5 or 2.0)")
    ap.add_argument("--risk-per-trade", type=float, default=None,
                    help="also set risk per trade, as a percent of balance (e.g. 0.5)")
    args = ap.parse_args()

    state = fs.get_today_risk_state(args.user)
    print(f"before: committed={state.get('risk_committed_today', 0.0)} "
          f"realized_pnl={state.get('realized_pnl_today', 0.0)}")

    # Increment by the negative of whatever is there to land exactly on 0.
    committed = float(state.get("risk_committed_today", 0.0) or 0.0)
    if committed:
        fs.add_committed_risk(args.user, -committed)
    fs.sync_realized_pnl(args.user, 0.0)

    if args.cap is not None or args.risk_per_trade is not None:
        profile = fs.get_risk_profile(args.user)
        cap = args.cap if args.cap is not None else profile["daily_loss_cap_pct"]
        rpt = args.risk_per_trade if args.risk_per_trade is not None else profile["risk_per_trade_pct"]
        fs.set_risk_profile(args.user, daily_loss_cap_pct=cap, risk_per_trade_pct=rpt)
        print(f"risk profile set: daily cap {cap}%, risk per trade {rpt}%")

    after = fs.get_today_risk_state(args.user)
    profile = fs.get_risk_profile(args.user)
    print(f"after:  committed={after.get('risk_committed_today', 0.0)} "
          f"realized_pnl={after.get('realized_pnl_today', 0.0)}")
    print(f"cap now {profile['daily_loss_cap_pct']}% of balance, "
          f"risk per trade {profile['risk_per_trade_pct']}%")

    fs.append_audit_log(args.user, "demo_reset_script", "reset_daily_risk",
                        {"cleared": committed, "cap_pct": profile["daily_loss_cap_pct"]})
    print("Done.")


if __name__ == "__main__":
    main()
