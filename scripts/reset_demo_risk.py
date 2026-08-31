"""
Reset today's risk budget — for rehearsing and recording the demo.

Risk is committed at APPROVAL time (see risk.consume_approval), so a few
rehearsal runs will eat into today's cap and the "rejected by the daily
cap" moment will fire earlier than you expect. Run this between takes.

    # put the budget back to zero, leave the cap at its current value
    python scripts/reset_demo_risk.py

    # zero the budget AND tighten the cap so the rejection lands fast
    python scripts/reset_demo_risk.py --cap 0.5

Why --cap matters for the video: the default cap is 2% of a $100k demo
balance = $2,000, and each trade commits 0.5% = $500. That is FOUR
approved trades before the fifth is rejected — far too slow on camera.
Setting --cap 0.5 makes the cap $500, so trade #1 is approved and trade
#2 is rejected outright. That is the money shot for the security story.

Set it back afterwards with:  python scripts/reset_demo_risk.py --cap 2.0
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
