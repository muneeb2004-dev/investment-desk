# Investment Desk

A fleet of Gemini Enterprise agents that run a personal trading &
investing desk: preset or user-defined strategies, risk-capped trade
execution on MT5, and a personalized report every morning at 8am.

Built for the **Fortified Enterprise Fleet** track of Google Cloud's
*All Things Agentic Hackathon*.

![Architecture diagram](docs/architecture.svg)

## What it does

Two "desks," one agent fleet:

- **Trading Desk** — short-term signals from Order Block/SMC structure
  (BOS/CHoCH), RSI divergence, currency strength, Heikin-Ashi trend
  reads, and CCI+EMA confirmation — the strategies actually used day
  to day, ported from MQL5 into deterministic, testable Python.
- **Investment Desk** — a transparent, rules-based "quality at a
  reasonable price" screen (low debt, strong ROE, consistent earnings
  growth, positive free cash flow) for longer-term stock picks.

Either desk works two ways: pick a **preset** strategy, or **describe
one in your own words** to the Strategy Builder Agent, which turns
that description into a structured, saved strategy definition.

Every trade idea that reaches execution passes through a **Risk &
Sizing Agent** that enforces a daily loss cap and computes position
size from it — the Execution Agent physically cannot place an order
without a fresh, signed approval token from that check. Every agent
decision — approvals, rejections, and orders — is written to an
append-only Firestore audit log.

## Why this fits "Fortified Enterprise Fleet"

- **Agent registry / discovery** — a Gemini Enterprise Orchestrator
  routes between five specialist agents, each scoped to only the
  tools it needs.
- **Long-running background execution** — Cloud Scheduler fires the
  Reporting Agent every day at 8:00am without a user in the loop.
- **Persistent state** — Firestore holds strategies, per-day risk
  budget, watchlists, and reports across sessions.
- **Observability** — every agent action is audit-logged with a
  timestamp, the agent that acted, and full details.
- **Security enforcement** — capital-affecting actions are gated
  behind a single, short-lived, signed approval token that only the
  Risk Agent can issue.

## Architecture

See `docs/architecture.svg`. In short: Gemini Enterprise agents call a
small FastAPI backend as "tools." The backend runs on a local machine
(MT5's Python API is Windows-only) and is reached over a tunnel; it
talks to the MT5 terminal for quotes/candles/orders and to Firestore
for all persistent state. Cloud Scheduler triggers the daily report
by hitting the backend directly.

## Repo layout

```
strategies/            pure-function strategy logic (no I/O, unit-testable)
  technical.py          Trading Desk: SMC, divergence, currency strength, HA, CCI+EMA
  investment.py         Investment Desk: value/quality screen

backend/                FastAPI app — the "tools" Gemini Enterprise agents call
  main.py                all endpoints
  mt5_client.py          MetaTrader5 wrapper (Windows-only, demo-account-only)
  firestore_client.py    persistence: strategies, risk state, watchlist, audit log, reports
  risk.py                position sizing + daily loss cap + signed approval tokens
  reporting.py           daily report generation
  .env.example           config template — copy to .env and fill in your own values

gemini_enterprise/
  SETUP.md               step-by-step console setup: data stores, agents, tool wiring

scripts/
  setup_cloud_scheduler.sh   creates the 8am Cloud Scheduler job

docs/
  architecture.svg       system diagram (embedded above)
```

## Running it

Prerequisites: Python 3.11+, an MT5 **demo** account and terminal
installed, a GCP project with Firestore enabled, and `gcloud` +
`cloudflared` (or `ngrok`) installed.

```bash
pip install -r requirements.txt
cp backend/.env.example backend/.env      # fill in your own values — never commit this file
uvicorn backend.main:app --reload --port 8000
```

In another terminal:

```bash
cloudflared tunnel --url http://localhost:8000
```

Then follow `gemini_enterprise/SETUP.md` to wire up the agents in the
Gemini Enterprise console, and run `scripts/setup_cloud_scheduler.sh`
to schedule the 8am report.

## Safety notes

- The MT5 client (`backend/mt5_client.py`) checks the connected
  account's `trade_mode` and **refuses to initialize against anything
  that isn't reported as a demo account.**
- The daily loss cap is enforced server-side, not just suggested by
  the agent's prompt — `/execute-order` cannot succeed without a
  token that `/risk-size` issued for that exact order.
- Real MT5 credentials live only in a local, untracked `.env` file
  (see `.gitignore`) — they are never sent to Gemini, logged, or
  committed.

## Roadmap (not built for this submission)

A Signal Ingestion Agent that watches Discord/Telegram trading-signal
channels, extracts entry/stop-loss/take-profit, and turns each signal
into a *proposed* order — routed through the exact same Risk &
Execution Agent above, so a signal can never bypass the daily cap or
go straight to a live order. Scoped out of today's build deliberately
(see architecture diagram) rather than shipped half-working.
