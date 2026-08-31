# Strategy: Order Block / SMC (Smart Money Concepts)

**Desk:** Trading Desk
**Preset name:** `order_block_smc`

## What it looks for
Smart Money Concepts structure: the most recent bullish or bearish
"order block" (the last down-close candle before a strong up-move, or
the last up-close candle before a strong down-move — the candle where
large players are believed to have entered), combined with a check for
a structure break since then.

## Signal logic
- **Break of Structure (BOS):** price breaks past the prior swing
  high/low *in the direction of* the existing trend — treated as
  trend continuation.
- **Change of Character (CHoCH):** price breaks past the prior swing
  high/low *against* the existing trend — treated as an early
  reversal signal.
- A **buy** signal fires on a bullish BOS or CHoCH; a **sell** signal
  fires on the bearish equivalent.

## What it returns
A signal (buy/sell/none), a confidence score, a plain-language reason
(e.g. "Price broke above prior swing high (BOS, continuation)"), and
the key price levels involved (the order block zone, last swing high,
last swing low) so a user can see exactly where the setup is on the
chart.

## When it says nothing
If there isn't a clean two-swing structure yet, or price hasn't broken
either recent swing point, it returns "none" rather than forcing a
signal.
