# Strategy: Heikin-Ashi Trend (5H)

**Desk:** Trading Desk
**Preset name:** `heikin_ashi_trend`

## What it looks for
Heikin-Ashi candles (a smoothed version of regular candlesticks that
filters out noise) on the 5-hour chart, looking for a clean run of
same-direction candles as trend confirmation.

## Signal logic
- **Buy:** the last 3 Heikin-Ashi candles are all bullish (close above
  open). If none of them have a lower wick, that's treated as an
  especially strong trend and given higher confidence.
- **Sell:** the mirror image — 3 bearish candles in a row, no upper
  wicks for extra confidence.
- If the recent candles are mixed, it returns "none" — no clean trend
  to follow yet.

## What it returns
A signal, a confidence score (higher when there are no opposing
wicks), a plain-language reason, and the latest Heikin-Ashi close.

## Why the 5H timeframe
This mirrors how it's actually traded day to day — 5H smooths out
lower-timeframe noise while still updating multiple times within the
New York trading session.
