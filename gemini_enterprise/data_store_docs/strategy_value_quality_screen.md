# Strategy: Value / Quality Screen (Investment Desk)

**Desk:** Investment Desk
**Preset name:** `value_quality_screen`

## What it looks for
A transparent, rules-based "quality at a reasonable price" screen —
inspired by long-term, fundamentals-first investing rather than
short-term price action. This is an educational screening tool, not
personalized financial advice, and every result explains exactly
which rules passed or failed.

## The six criteria (a company is scored on however many it has data for)
1. **P/E ratio** between 0 and 25 — reasonably priced relative to
   earnings.
2. **Debt-to-equity** at or below 1.0 — conservative balance sheet.
3. **Return on equity** at or above 12% — efficient use of
   shareholder capital.
4. **5-year earnings growth** averaging at least 5%/year — consistent
   growth, not a one-off spike.
5. **Free cash flow positive** in at least 4 of the last 5 years —
   the business actually generates cash, not just accounting profit.
6. **Gross margin** at or above 30% — some evidence of pricing power.

## Verdicts
- **strong_candidate** — passed 80%+ of the scored criteria.
- **watchlist** — passed 50–79%.
- **does_not_meet_criteria** — below 50%.
- **insufficient_data** — fewer than 3 criteria had usable data.

## Disclaimer
Always relay the screen's `disclaimer` field verbatim: this is a
rules-based educational screen, not personalized investment advice,
and passing these criteria does not guarantee future returns.
