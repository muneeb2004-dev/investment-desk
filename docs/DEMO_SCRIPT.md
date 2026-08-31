# ~4-minute demo video script

Keep every segment on-camera proof, not slides — the rubric explicitly
wants live demonstration evidence and GCP deployment proof.

**0:00–0:20 — Hook**
"This is Investment Desk — a fleet of Gemini Enterprise agents that
run a personal trading and investing desk: pick a strategy or describe
your own, and the fleet analyzes, risk-checks, executes on a demo MT5
account, and reports back every morning — all with a hard-enforced
daily loss cap and a full audit trail."

**0:20–1:00 — Architecture (show `docs/architecture.svg`)**
Point at: Orchestrator + 5 specialist agents in Gemini Enterprise, the
FastAPI backend as the tool layer, Firestore for state/audit,
Cloud Scheduler for the 8am trigger. One sentence on why the backend
runs locally (MT5's Windows-only API) and is reached over a tunnel —
show the live GCP console tabs (Firestore data, Cloud Scheduler job)
briefly here as deployment proof.

**1:00–1:40 — Trading Desk, preset strategy**
In the Gemini Enterprise chat: ask for an analysis on a symbol using
the Order Block/SMC preset. Show the agent calling `/analyze-technical`
and explaining the consensus signal and reasoning in plain language.

**1:40–2:10 — Strategy Builder, natural language**
Describe a simple custom strategy out loud/typed ("buy when price
breaks above yesterday's high and RSI is above 50"). Show the agent
turning it into a structured definition and confirming it saved.

**2:10–2:45 — Investment Desk**
Run the value/quality screen against a couple of symbols' fundamentals
and show the pass/fail breakdown per rule — emphasize this is
explainable, not a black box.

**2:45–3:20 — Risk-gated execution (the security story)**
Ask the Risk & Execution Agent to act on the earlier signal. Show it
call `/risk-size` first, state the computed lot size and dollar risk
out loud, then execute — then show the Firestore audit log entry that
was just written. If time allows, show a SECOND attempt that gets
rejected because the daily cap is now used up — this is the strongest
single proof point for the "security enforcement" criterion.

**3:20–3:50 — Reporting**
Trigger the daily report on demand (`gcloud scheduler jobs run
investment-desk-daily-report` or the equivalent chat request) and walk
through the personalized feed for the watchlist.

**3:50–4:00 — Close**
One sentence on the Phase 2 roadmap (Discord/Telegram signal ingestion
routed through the same risk gate) and why it's deliberately not built
yet, then wrap.
