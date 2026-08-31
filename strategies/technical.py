"""
Trading Desk strategy library — Muneeb's existing SMC / technical rules,
ported from his MQL5 Expert Advisors into pure Python functions.

Each strategy function takes a pandas DataFrame of OHLC(V) candles
(columns: time, open, high, low, close, volume — oldest first) and
returns a dict:

    {
        "strategy": str,
        "signal": "buy" | "sell" | "none",
        "confidence": float,        # 0..1, rough heuristic strength
        "reasoning": str,           # human-readable explanation
        "levels": {...}             # any key prices worth surfacing
    }

These are called by the Technical Analyst Agent (via the FastAPI
/analyze-technical endpoint) — Gemini reasons over the *output* of
these functions rather than raw candles, which keeps the agent's
reasoning grounded in deterministic, testable logic instead of
hallucinated technicals.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------
# Shared indicator helpers
# --------------------------------------------------------------------------

def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def _cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    sma = typical_price.rolling(period).mean()
    mean_dev = typical_price.rolling(period).apply(
        lambda x: np.mean(np.abs(x - x.mean())), raw=True
    )
    return (typical_price - sma) / (0.015 * mean_dev.replace(0, np.nan))


def _swing_points(df: pd.DataFrame, left: int = 2, right: int = 2):
    """Return indices of local swing highs and swing lows."""
    highs, lows = [], []
    for i in range(left, len(df) - right):
        window_high = df["high"].iloc[i - left : i + right + 1]
        window_low = df["low"].iloc[i - left : i + right + 1]
        if df["high"].iloc[i] == window_high.max():
            highs.append(i)
        if df["low"].iloc[i] == window_low.min():
            lows.append(i)
    return highs, lows


# --------------------------------------------------------------------------
# 1. Order Block / SMC structure (BOS / CHoCH)
# --------------------------------------------------------------------------

def order_block_smc(df: pd.DataFrame) -> dict:
    """
    Smart Money Concepts: locate the most recent bullish/bearish Order
    Block and check for a Break of Structure (BOS, trend continuation)
    or Change of Character (CHoCH, trend reversal) since then.
    """
    if len(df) < 30:
        return _empty("order_block_smc", "Not enough candles (need >= 30).")

    highs, lows = _swing_points(df)
    if len(highs) < 2 or len(lows) < 2:
        return _empty("order_block_smc", "No clear swing structure yet.")

    last_high_idx, prev_high_idx = highs[-1], highs[-2]
    last_low_idx, prev_low_idx = lows[-1], lows[-2]

    higher_high = df["high"].iloc[last_high_idx] > df["high"].iloc[prev_high_idx]
    higher_low = df["low"].iloc[last_low_idx] > df["low"].iloc[prev_low_idx]
    lower_high = df["high"].iloc[last_high_idx] < df["high"].iloc[prev_high_idx]
    lower_low = df["low"].iloc[last_low_idx] < df["low"].iloc[prev_low_idx]

    close = df["close"].iloc[-1]
    structure_break_up = close > df["high"].iloc[prev_high_idx]
    structure_break_down = close < df["low"].iloc[prev_low_idx]

    # last down-close candle before an up-move = bullish order block (and vice versa)
    bullish_ob_idx = None
    bearish_ob_idx = None
    for i in range(len(df) - 2, 0, -1):
        if df["close"].iloc[i] < df["open"].iloc[i] and df["close"].iloc[i + 1] > df["open"].iloc[i + 1]:
            bullish_ob_idx = i
            break
    for i in range(len(df) - 2, 0, -1):
        if df["close"].iloc[i] > df["open"].iloc[i] and df["close"].iloc[i + 1] < df["open"].iloc[i + 1]:
            bearish_ob_idx = i
            break

    signal, reasoning, confidence = "none", "No actionable structure break.", 0.3

    if structure_break_up and (higher_high or higher_low):
        signal = "buy"
        tag = "BOS (continuation)" if higher_low else "CHoCH (reversal up)"
        reasoning = f"Price broke above prior swing high ({tag})."
        confidence = 0.7 if higher_low else 0.6
    elif structure_break_down and (lower_high or lower_low):
        signal = "sell"
        tag = "BOS (continuation)" if lower_high else "CHoCH (reversal down)"
        reasoning = f"Price broke below prior swing low ({tag})."
        confidence = 0.7 if lower_high else 0.6

    levels = {}
    if bullish_ob_idx is not None:
        levels["bullish_order_block"] = {
            "low": float(df["low"].iloc[bullish_ob_idx]),
            "high": float(df["high"].iloc[bullish_ob_idx]),
        }
    if bearish_ob_idx is not None:
        levels["bearish_order_block"] = {
            "low": float(df["low"].iloc[bearish_ob_idx]),
            "high": float(df["high"].iloc[bearish_ob_idx]),
        }
    levels["last_swing_high"] = float(df["high"].iloc[last_high_idx])
    levels["last_swing_low"] = float(df["low"].iloc[last_low_idx])

    return {
        "strategy": "order_block_smc",
        "signal": signal,
        "confidence": confidence,
        "reasoning": reasoning,
        "levels": levels,
    }


# --------------------------------------------------------------------------
# 2. RSI divergence
# --------------------------------------------------------------------------

def rsi_divergence(df: pd.DataFrame, period: int = 14) -> dict:
    if len(df) < period + 20:
        return _empty("rsi_divergence", "Not enough candles for RSI divergence.")

    rsi = _rsi(df["close"], period)
    highs, lows = _swing_points(df)

    signal, reasoning, confidence = "none", "No divergence detected.", 0.3

    if len(lows) >= 2:
        i2, i1 = lows[-2], lows[-1]
        price_lower_low = df["low"].iloc[i1] < df["low"].iloc[i2]
        rsi_higher_low = rsi.iloc[i1] > rsi.iloc[i2]
        if price_lower_low and rsi_higher_low:
            signal, confidence = "buy", 0.65
            reasoning = "Bullish divergence: price made a lower low while RSI made a higher low."

    if signal == "none" and len(highs) >= 2:
        i2, i1 = highs[-2], highs[-1]
        price_higher_high = df["high"].iloc[i1] > df["high"].iloc[i2]
        rsi_lower_high = rsi.iloc[i1] < rsi.iloc[i2]
        if price_higher_high and rsi_lower_high:
            signal, confidence = "sell", 0.65
            reasoning = "Bearish divergence: price made a higher high while RSI made a lower high."

    return {
        "strategy": "rsi_divergence",
        "signal": signal,
        "confidence": confidence,
        "reasoning": reasoning,
        "levels": {"rsi_last": float(rsi.iloc[-1])},
    }


# --------------------------------------------------------------------------
# 3. Currency strength
# --------------------------------------------------------------------------

def currency_strength(pair_data: dict[str, pd.DataFrame], lookback: int = 20) -> dict:
    """
    pair_data: e.g. {"EURUSD": df, "GBPUSD": df, "USDJPY": df, ...}
    Ranks each currency by average % return contribution across all
    pairs it appears in, then flags the strongest-vs-weakest pairing.
    """
    if len(pair_data) < 2:
        return _empty("currency_strength", "Need at least 2 pairs to compare.")

    scores: dict[str, list[float]] = {}
    for symbol, df in pair_data.items():
        if len(df) < lookback + 1:
            continue
        base, quote = symbol[:3], symbol[3:6]
        pct_change = (df["close"].iloc[-1] / df["close"].iloc[-lookback] - 1) * 100
        scores.setdefault(base, []).append(pct_change)
        scores.setdefault(quote, []).append(-pct_change)

    if not scores:
        return _empty("currency_strength", "Not enough history in provided pairs.")

    ranked = sorted(
        ((ccy, float(np.mean(vals))) for ccy, vals in scores.items()),
        key=lambda x: x[1],
        reverse=True,
    )
    strongest, strongest_score = ranked[0]
    weakest, weakest_score = ranked[-1]
    candidate_pair = f"{strongest}{weakest}"

    return {
        "strategy": "currency_strength",
        "signal": "buy" if candidate_pair[:3] == strongest else "sell",
        "confidence": min(0.9, 0.4 + abs(strongest_score - weakest_score) / 10),
        "reasoning": (
            f"{strongest} is strongest ({strongest_score:+.2f}%), "
            f"{weakest} is weakest ({weakest_score:+.2f}%) over last {lookback} candles. "
            f"Bias: long {candidate_pair}."
        ),
        "levels": {"ranking": ranked},
    }


# --------------------------------------------------------------------------
# 4. Heikin-Ashi trend read (5H chart per Muneeb's setup)
# --------------------------------------------------------------------------

def heikin_ashi_trend(df: pd.DataFrame, confirm_candles: int = 3) -> dict:
    if len(df) < confirm_candles + 1:
        return _empty("heikin_ashi_trend", "Not enough candles.")

    ha = pd.DataFrame(index=df.index)
    ha["close"] = (df["open"] + df["high"] + df["low"] + df["close"]) / 4
    ha_open = [(df["open"].iloc[0] + df["close"].iloc[0]) / 2]
    for i in range(1, len(df)):
        ha_open.append((ha_open[i - 1] + ha["close"].iloc[i - 1]) / 2)
    ha["open"] = ha_open
    ha["high"] = pd.concat([df["high"], ha["open"], ha["close"]], axis=1).max(axis=1)
    ha["low"] = pd.concat([df["low"], ha["open"], ha["close"]], axis=1).min(axis=1)

    recent = ha.tail(confirm_candles)
    bullish_run = (recent["close"] > recent["open"]).all()
    bearish_run = (recent["close"] < recent["open"]).all()
    no_lower_wick = (recent["low"] >= recent["open"] - 1e-9).all()
    no_upper_wick = (recent["high"] <= recent["open"] + 1e-9).all()

    if bullish_run:
        signal = "buy"
        confidence = 0.75 if no_lower_wick else 0.55
        reasoning = f"Last {confirm_candles} Heikin-Ashi candles are bullish" + (
            " with no lower wicks (strong trend)." if no_lower_wick else "."
        )
    elif bearish_run:
        signal = "sell"
        confidence = 0.75 if no_upper_wick else 0.55
        reasoning = f"Last {confirm_candles} Heikin-Ashi candles are bearish" + (
            " with no upper wicks (strong trend)." if no_upper_wick else "."
        )
    else:
        signal, confidence, reasoning = "none", 0.3, "Heikin-Ashi candles are mixed — no clean trend."

    return {
        "strategy": "heikin_ashi_trend",
        "signal": signal,
        "confidence": confidence,
        "reasoning": reasoning,
        "levels": {"ha_close_last": float(ha["close"].iloc[-1])},
    }


# --------------------------------------------------------------------------
# 5. CCI + EMA
# --------------------------------------------------------------------------

def cci_ema_strategy(df: pd.DataFrame, ema_period: int = 50, cci_period: int = 20) -> dict:
    if len(df) < max(ema_period, cci_period) + 5:
        return _empty("cci_ema_strategy", "Not enough candles.")

    ema = _ema(df["close"], ema_period)
    cci = _cci(df, cci_period)

    price_above_ema = df["close"].iloc[-1] > ema.iloc[-1]
    cci_cross_up = cci.iloc[-2] < -100 and cci.iloc[-1] >= -100
    cci_cross_down = cci.iloc[-2] > 100 and cci.iloc[-1] <= 100

    signal, reasoning, confidence = "none", "No CCI/EMA confirmation yet.", 0.3

    if price_above_ema and cci_cross_up:
        signal, confidence = "buy", 0.65
        reasoning = f"Price above EMA{ema_period} trend filter and CCI is recovering out of oversold (<-100)."
    elif not price_above_ema and cci_cross_down:
        signal, confidence = "sell", 0.65
        reasoning = f"Price below EMA{ema_period} trend filter and CCI is falling out of overbought (>100)."

    return {
        "strategy": "cci_ema_strategy",
        "signal": signal,
        "confidence": confidence,
        "reasoning": reasoning,
        "levels": {"ema": float(ema.iloc[-1]), "cci_last": float(cci.iloc[-1])},
    }


def _empty(name: str, reason: str) -> dict:
    return {"strategy": name, "signal": "none", "confidence": 0.0, "reasoning": reason, "levels": {}}


# --------------------------------------------------------------------------
# Dispatcher
# --------------------------------------------------------------------------

PRESET_STRATEGIES = {
    "order_block_smc": order_block_smc,
    "rsi_divergence": rsi_divergence,
    "heikin_ashi_trend": heikin_ashi_trend,
    "cci_ema_strategy": cci_ema_strategy,
    # currency_strength has a different signature (multi-symbol) and is
    # dispatched separately by the backend.
}


def run_preset(strategy_name: str, df: pd.DataFrame, **kwargs) -> dict:
    if strategy_name not in PRESET_STRATEGIES:
        raise ValueError(f"Unknown preset strategy: {strategy_name}")
    return PRESET_STRATEGIES[strategy_name](df, **kwargs)
