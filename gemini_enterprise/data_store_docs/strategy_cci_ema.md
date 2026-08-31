# Strategy: CCI + EMA

**Desk:** Trading Desk
**Preset name:** `cci_ema_strategy`

## What it looks for
Combines a trend filter (50-period EMA) with a momentum-exhaustion
signal (20-period CCI, Commodity Channel Index) so trades only trigger
in the direction of the broader trend.

## Signal logic
- **Buy:** price is above the EMA (uptrend filter satisfied) AND CCI
  is crossing back up through -100 (recovering out of oversold).
- **Sell:** price is below the EMA (downtrend filter satisfied) AND
  CCI is crossing back down through +100 (falling out of overbought).
- Without both conditions agreeing, it returns "none."

## What it returns
A signal, a confidence score, a plain-language reason, and the current
EMA and CCI values.

## Why combine the two
The EMA alone doesn't say *when* to enter, and CCI alone can whipsaw
in a ranging market — requiring both to agree cuts down on
counter-trend false signals.
