# Strategy: RSI Divergence

**Desk:** Trading Desk
**Preset name:** `rsi_divergence`

## What it looks for
Disagreement between price and the RSI (Relative Strength Index,
14-period) momentum indicator at swing points.

## Signal logic
- **Bullish divergence (buy):** price makes a lower low, but RSI makes
  a higher low at the same time — momentum is fading even as price
  pushes down further, often an early reversal-up warning.
- **Bearish divergence (sell):** price makes a higher high, but RSI
  makes a lower high — momentum is fading even as price pushes up
  further, often an early reversal-down warning.

## What it returns
A signal, a confidence score, a plain-language explanation of which
kind of divergence fired, and the current RSI reading.

## Notes
This strategy is intentionally conservative — it only compares the two
most recent swing highs or the two most recent swing lows, so it can
take a while to produce a signal on calm/ranging price action. That's
expected behavior, not a bug.
