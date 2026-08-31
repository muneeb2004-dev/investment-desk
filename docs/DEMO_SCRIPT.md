# ~4-minute demo video script

Track: **The Taskmaster**. Max 4 minutes, public on YouTube or Vimeo.

Keep every segment on-camera proof, not slides — the rubric wants live
demonstration evidence, not a description of what the system would do.

---

## Before you hit record

```bash
# 1. backend up
uvicorn backend.main:app --port 8000

# 2. agent fleet up
adk web --port 8080

# 3. IMPORTANT — tighten the cap so the rejection lands on trade #2,
#    not trade #5. Run this between every take.
python scripts/reset_demo_risk.py --cap 0.5
```

Checklist:
- [ ] **"Algo Trading" is green in the MT5 terminal** — otherwise every
      order returns `retcode 10027` and the execution beat dies
- [ ] MT5 terminal visible in a window you can cut to
- [ ] Firestore console open on the `users/muneeb` document, audit_log
      subcollection
- [ ] `docs/architecture.svg` open in a tab
- [ ] Run one full rehearsal, then reset the risk budget again

> The cap trick: default is 2% of $100k = $2,000, and each trade commits
> 0.5% = $500 — that is four approvals before a rejection. `--cap 0.5`
> makes the cap $500, so trade #1 is approved and trade #2 is refused.

---

## 0:00–0:20 — Hook

> "Placing a trade properly is a messy, multi-step chore. Pick a
> strategy, read the chart, size the position against your risk limit,
> place the order, log it. Miss one step and you blow up the account.
> Investment Desk is an agent fleet that does the whole chore — and
> physically cannot skip the risk step."

## 0:20–0:50 — Architecture (show `docs/architecture.svg`)

Point at: Orchestrator + five specialists on **Google ADK**, driven by
**Gemini 3.5 Flash-Lite**; the FastAPI backend as the tool layer;
**Firestore** for state and the audit log; MT5 for real execution.

One line on why the backend is local: *MT5's Python API is Windows-only
and has to sit next to the terminal.*

Say the compliance sentence once, plainly:
> "Gemini 3.5 through the Gemini API, Google ADK as the agent framework,
> Firestore as the Cloud service."

## 0:50–1:30 — Trading Desk, live signal

Type into the ADK chat:

```
What's the technical signal on EURUSD right now?
```

**Point at the side panel** as it happens — the Orchestrator hands off to
`technical_analyst_agent`, which calls `analyze_technical`. Say out loud:

> "That signal came from deterministic Python running over live MT5
> candles. The model is explaining it, not inventing it."

## 1:30–2:00 — Strategy Builder, plain English

```
I want a strategy that buys when price closes above yesterday's high and RSI is above 50.
```

Show it turning that into a structured definition and saving it. Call out
the `strategy_id` coming back — that is Firestore persistence.

## 2:00–2:45 — Risk-gated execution ⭐

```
Buy EURUSD with a 20 pip stop loss. Size it and place it.
```

Narrate the two-step as it renders in the panel:

> "It calls risk-size *first*. That returns the lot size, the dollar
> risk, and a signed approval token. Only then does it call
> execute-order — and execute-order takes no symbol and no volume of its
> own, just that token."

Cut to the MT5 terminal showing the filled position.

## 2:45–3:20 — The rejection ⭐⭐ (do not skip this)

```
Now place that exact same trade again.
```

It gets **refused** — the daily cap is spent.

> "That refusal isn't the model being cautious. The backend computed
> that the daily loss cap was exhausted and never issued a token. If the
> model had made a token up, execute-order would have returned 403 —
> the signature wouldn't verify."

**This is the single strongest proof point in the video.** Let it breathe.

## 3:20–3:45 — Observability

```
Show me the audit log.
```

Then cut to the **Firestore console** and show the same entries server-side:
the approval, the order, and the rejection — each with a timestamp and
the agent that acted.

> "Append-only. Every agent decision, on the server, not in chat history."

## 3:45–4:00 — Close

> "Multi-step, autonomous, and safe by construction rather than by good
> intentions. Next up is a signal-ingestion agent that watches Discord
> channels — routed through this exact same risk gate, so it can never
> bypass the cap."

---

## If something breaks mid-take

| Symptom | Fix |
|---|---|
| `retcode 10027` | Algo Trading is off in MT5 — click it green |
| Order rejected too early | Budget spent: `python scripts/reset_demo_risk.py --cap 0.5` |
| `429 RESOURCE_EXHAUSTED` | Gemini free-tier rate limit — wait ~30s and retry the turn |
| Agent won't hand off | Start a new session in the ADK UI sidebar |
| Backend 500s on MT5 calls | MT5 terminal closed or logged out — reopen and log in |
