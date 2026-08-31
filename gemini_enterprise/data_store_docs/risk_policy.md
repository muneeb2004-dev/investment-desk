# Risk Policy

This is the governance layer every trade passes through before it can
reach the market — agents should use this to explain *why* a trade was
approved, scaled down, or rejected, in plain language.

## Daily loss cap
Each user has a `daily_loss_cap_pct` (default 2% of account balance).
Once the amount already risked today (open positions' committed risk,
adjusted for any realized losses already booked today) reaches that
cap, **no new orders are approved for the rest of the day**, no matter
how good the setup looks. This resets at midnight.

## Per-trade risk sizing
Each user has a `risk_per_trade_pct` (default 0.5% of account
balance). A new trade's position size is calculated so that if the
stop-loss is hit, the loss equals that percentage of the account — not
a fixed lot size. If the remaining daily budget is smaller than a full
per-trade allocation, the trade is sized down to fit whatever budget
is left, rather than rejected outright, as long as some budget remains.

## Approval tokens
The Risk & Sizing Agent is the only agent that can approve a trade. It
issues a short-lived (2-minute), cryptographically signed token that
proves a real risk check happened for that exact symbol, direction,
and size. The Execution Agent cannot place an order without a valid
token — this isn't a suggestion in a prompt, it's enforced by the
backend regardless of what any agent is told to do.

## Demo-account only
This system is configured to work only against an MT5 account that
reports itself as a demo account. It refuses to initialize against a
live account. This is a deliberate hackathon-scope safety boundary,
not a limitation of the design — the same architecture would extend
to a live account only after additional human sign-off steps not built
for this submission.

## Audit trail
Every approval, rejection, and executed order is written to a
permanent, append-only log with a timestamp and the full reasoning —
nothing is approved or rejected silently.
