# Strategy: Currency Strength

**Desk:** Trading Desk
**Preset name:** `currency_strength` (multi-symbol — needs several
related pairs at once, e.g. EURUSD, GBPUSD, USDJPY, to compare)

## What it looks for
Ranks each individual currency (EUR, USD, GBP, JPY, etc.) by how much
it has moved, on average, across every pair it appears in over a
lookback window — not just one pair in isolation.

## Signal logic
- Computes each currency's average % contribution across all supplied
  pairs.
- The strongest currency and the weakest currency are identified.
- The suggested trade is going long the pair formed by strongest vs.
  weakest (e.g. if JPY is strongest and GBP is weakest, the idea is
  long JPY against GBP).

## What it returns
A ranked list of every currency's relative strength score, plus the
suggested pairing and a confidence score based on how wide the
strongest/weakest gap is.

## Why it's useful
Trading a pair based on strength/weakness of both legs (not just chart
patterns on one pair) tends to filter out weaker setups where a pair
is only moving because of noise on one side.
