# Gemini Enterprise console setup

> **Not the path used for this submission.** The fleet that ships here
> runs on Google ADK (`adk_agents/`) against the Gemini API — see the
> README. Gemini Enterprise requires an active Google Cloud billing
> account, which this project did not have.
>
> This document is kept because the backend is deliberately front-end
> agnostic: the tools are plain authenticated HTTP with an OpenAPI
> schema, so the same six agents can be rebuilt in the Gemini Enterprise
> console without touching a line of backend code. That portability is
> the point — the security guarantees live in the backend, not in
> whichever runtime is driving it.

This is the exact agent/tool layout for this project, so you're not
re-deciding structure while the clock is running.

## 1. Expose the backend first

Everything below points at your FastAPI backend's live URL, so start
the backend and tunnel before touching the console.

```
cd backend
pip install -r ../requirements.txt
cp .env.example .env          # then fill in YOUR values in .env
uvicorn backend.main:app --reload --port 8000
```

In a second terminal, tunnel it (no account needed for a quick tunnel):

```
cloudflared tunnel --url http://localhost:8000
```

Copy the `https://xxxxx.trycloudflare.com` URL it prints — call this
`BACKEND_URL` below. (ngrok works the same way if you already have it
set up: `ngrok http 8000`.)

Sanity check: open `BACKEND_URL/docs` in a browser — you should see
the FastAPI interactive docs. `BACKEND_URL/openapi.json` is the full
OpenAPI schema — Gemini Enterprise can import tools directly from
this instead of you hand-typing schemas.

## 2. Create the data stores

- **strategy_library** — unstructured data store. Upload a short doc
  per preset strategy (Order Block/SMC, RSI divergence, currency
  strength, Heikin-Ashi, CCI+EMA, and the value/quality investing
  screen) describing what it does in plain language — this is what
  grounds the Strategy Builder and Analyst agents' explanations, and
  what a user browses when picking a preset.
- **risk_policy** — one short doc explaining the daily loss cap and
  per-trade risk rules in plain language, so agents can explain *why*
  an order was rejected, not just that it was.

## 3. Create the agents

For every agent below: Tools -> Add Tool -> OpenAPI -> paste
`BACKEND_URL/openapi.json`, then restrict each agent to only the
operations it actually needs (this is itself part of your security
story — no agent has a tool it doesn't need). Add a custom header on
every tool: `X-Backend-Api-Key: <your BACKEND_API_KEY value>`.

### Orchestrator (the front door)
- Ground it in both data stores.
- Tools: none directly — it routes to the other agents.
- System instructions: greet the user, ask whether they want the
  Trading Desk or Investment Desk, and whether to use a preset or
  build a custom strategy; hand off accordingly.

### Strategy Builder Agent
- Ground it in `strategy_library`.
- Tools: `POST /save-strategy`, `GET /strategies/{user_id}`.
- System instructions: have a short back-and-forth turning what the
  user describes ("I want to buy when price breaks above yesterday's
  high with RSI above 50") into a structured JSON `definition` object,
  confirm it back to them in plain language, then call `/save-strategy`.
  This is the "speak your own strategy" flow.

### Technical Analyst Agent (Trading Desk)
- Tools: `POST /analyze-technical`, `GET /quote/{symbol}`.
- System instructions: given a symbol (and optionally a preset
  strategy name), call `/analyze-technical`, then explain the
  consensus signal and each strategy's reasoning in plain language —
  never invent a signal that didn't come back from the tool call.

### Investment Analyst Agent (Investment Desk)
- Tools: `POST /analyze-investment`.
- System instructions: given one or more symbols and their
  fundamentals (ask the user, or note this is a demo-data limitation
  if no live fundamentals feed is wired up), call `/analyze-investment`
  and explain the verdict per the screen's own stated criteria —
  always relay the `disclaimer` field verbatim.

### Risk & Execution Agent
- Tools: `POST /risk-size`, `POST /execute-order`.
- System instructions: **never** call `/execute-order` without first
  calling `/risk-size` in the same turn and getting `approved: true`
  back — pass its `approval_token` straight through. If rejected,
  explain the reason from the response (don't paraphrase around it)
  and stop. This agent should always state the lot size and dollar
  risk out loud before executing, and only execute against the demo
  account.

### Reporting Agent
- Tools: `POST /daily-report`, `GET /watchlist/{user_id}`.
- System instructions: on request (or on the Cloud Scheduler-triggered
  call), fetch the report and present it as a short personalized
  summary per watchlist symbol — signal, reasoning, and current risk
  budget used today.

## 4. Wire the orchestrator's handoffs

Use Gemini Enterprise's native agent-to-agent handoff/routing config
to connect Orchestrator -> each specialist above. This handoff graph
*is* your "agent registry" for the judging rubric — screenshot it for
the architecture diagram.
