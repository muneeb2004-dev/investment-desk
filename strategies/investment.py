"""
Investment Desk preset — a transparent, rules-based "quality at a
reasonable price" screen (the long-term, Buffett-style investing
preset Muneeb asked for).

IMPORTANT: This is a configurable heuristic screen for the hackathon
demo, not licensed financial advice, and it does not predict returns.
Every score is fully explainable — the whole point is that a user (or
a judge) can see exactly which rule fired and why, which is also what
the Strategy Builder Agent needs to be able to explain custom
strategies later.

Input: a `Fundamentals` dict per company (the FastAPI layer is
responsible for fetching these from a market-data provider — this
module only scores what it's given, so it's provider-agnostic).
"""

from __future__ import annotations

from dataclasses import dataclass, field


DISCLAIMER = (
    "Rules-based educational screen, not personalized investment advice. "
    "Past patterns and preset criteria do not guarantee future results."
)


@dataclass
class Fundamentals:
    symbol: str
    pe_ratio: float | None = None
    debt_to_equity: float | None = None
    return_on_equity: float | None = None          # as a fraction, e.g. 0.18 = 18%
    revenue_growth_5y: float | None = None          # avg annual %, e.g. 0.08 = 8%
    earnings_growth_5y: float | None = None
    free_cash_flow_positive_years: int | None = None  # out of last 5
    gross_margin: float | None = None
    extras: dict = field(default_factory=dict)


# Preset thresholds — a simplified "quality + reasonable price" screen.
# These are intentionally conservative/legible so every pass/fail is
# easy to explain in the demo.
PRESET_RULES = [
    ("pe_ratio", lambda v: v is not None and 0 < v <= 25,
     "P/E ratio is reasonable (<=25) and positive"),
    ("debt_to_equity", lambda v: v is not None and v <= 1.0,
     "Debt-to-equity is conservative (<=1.0)"),
    ("return_on_equity", lambda v: v is not None and v >= 0.12,
     "Return on equity is strong (>=12%)"),
    ("earnings_growth_5y", lambda v: v is not None and v >= 0.05,
     "5-year earnings growth is consistent (>=5%/yr avg)"),
    ("free_cash_flow_positive_years", lambda v: v is not None and v >= 4,
     "Free cash flow positive in at least 4 of the last 5 years"),
    ("gross_margin", lambda v: v is not None and v >= 0.30,
     "Gross margin suggests pricing power (>=30%)"),
]


def screen(f: Fundamentals) -> dict:
    passed, failed, missing = [], [], []

    for field_name, test, description in PRESET_RULES:
        value = getattr(f, field_name)
        if value is None:
            missing.append(description)
            continue
        if test(value):
            passed.append(description)
        else:
            failed.append(description)

    scored_rules = len(passed) + len(failed)
    score = (len(passed) / scored_rules) if scored_rules else 0.0

    if scored_rules < 3:
        verdict = "insufficient_data"
    elif score >= 0.8:
        verdict = "strong_candidate"
    elif score >= 0.5:
        verdict = "watchlist"
    else:
        verdict = "does_not_meet_criteria"

    reasoning = (
        f"{f.symbol}: passed {len(passed)}/{scored_rules} scored criteria "
        f"({', '.join(passed) if passed else 'none'})."
    )
    if failed:
        reasoning += f" Missed: {', '.join(failed)}."
    if missing:
        reasoning += f" Not enough data for: {', '.join(missing)}."

    return {
        "strategy": "value_quality_screen",
        "symbol": f.symbol,
        "verdict": verdict,
        "score": round(score, 2),
        "passed": passed,
        "failed": failed,
        "missing_data": missing,
        "reasoning": reasoning,
        "disclaimer": DISCLAIMER,
    }


def screen_many(fundamentals: list[Fundamentals]) -> list[dict]:
    return sorted((screen(f) for f in fundamentals), key=lambda r: r["score"], reverse=True)
