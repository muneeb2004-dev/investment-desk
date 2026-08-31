"""
Thin wrapper around the `MetaTrader5` Python package.

IMPORTANT: this package only works on Windows, talking to a locally
installed MT5 terminal — that's why this whole backend runs on
Muneeb's machine rather than on Cloud Run. It is initialized against
whatever account is configured in backend/.env — for the hackathon
that MUST be a demo account, never a live one.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import pandas as pd

from .config import settings

logger = logging.getLogger("mt5_client")

_initialized = False


def _ensure_init():
    global _initialized
    import MetaTrader5 as mt5  # imported lazily so this module can be
    # unit-tested / imported on non-Windows machines without crashing.

    if _initialized:
        # Cheap liveness probe before trusting the cached flag. The
        # terminal can be closed, restarted, or logged out underneath us
        # — and without this check the stale _initialized=True makes
        # every later call fail with "IPC send failed" until the backend
        # process itself is restarted. Mid-demo that is fatal, so
        # reconnect transparently instead.
        try:
            if mt5.account_info() is not None:
                return
        except Exception:
            pass
        logger.warning("MT5 connection lost — reinitializing.")
        try:
            mt5.shutdown()
        except Exception:
            pass
        _initialized = False

    kwargs = {}
    if settings.MT5_TERMINAL_PATH:
        kwargs["path"] = settings.MT5_TERMINAL_PATH
    ok = mt5.initialize(
        login=settings.MT5_LOGIN,
        password=settings.MT5_PASSWORD,
        server=settings.MT5_SERVER,
        **kwargs,
    )
    if not ok:
        raise RuntimeError(f"MT5 initialize() failed: {mt5.last_error()}")

    account = mt5.account_info()
    if account is not None and getattr(account, "trade_mode", None) == 0:
        # trade_mode 0 == ACCOUNT_TRADE_MODE_DEMO in the MT5 API
        logger.info("Connected to MT5 DEMO account #%s", account.login)
    else:
        # Refuse to proceed against anything that isn't clearly a demo
        # account — this backend is not meant to place live orders.
        mt5.shutdown()
        raise RuntimeError(
            "Connected MT5 account does not report as a DEMO account. "
            "Refusing to initialize — this hackathon build only trades demo accounts."
        )
    _initialized = True


def get_candles(symbol: str, timeframe: str = "H1", count: int = 300) -> pd.DataFrame:
    _ensure_init()
    import MetaTrader5 as mt5

    tf_map = {
        "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1,
    }
    tf = tf_map.get(timeframe.upper())
    if tf is None:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"No candle data returned for {symbol} {timeframe}: {mt5.last_error()}")

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df = df.rename(columns={"tick_volume": "volume"})
    return df[["time", "open", "high", "low", "close", "volume"]]


def get_quote(symbol: str) -> dict:
    _ensure_init()
    import MetaTrader5 as mt5

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"No tick data for {symbol}: {mt5.last_error()}")
    return {"symbol": symbol, "bid": tick.bid, "ask": tick.ask, "time": datetime.fromtimestamp(tick.time).isoformat()}


def get_pip_value_per_lot(symbol: str) -> float:
    """
    Value in account currency of a 1-pip move for 1.0 standard lot,
    read from the live symbol spec rather than assumed.
    """
    _ensure_init()
    import MetaTrader5 as mt5

    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"No symbol info for {symbol}: {mt5.last_error()}")
    pip_size = info.point * 10 if info.digits in (3, 5) else info.point
    return (info.trade_tick_value / info.trade_tick_size) * pip_size if info.trade_tick_size else 0.0


def get_account_summary() -> dict:
    _ensure_init()
    import MetaTrader5 as mt5

    acc = mt5.account_info()
    if acc is None:
        raise RuntimeError(f"account_info() failed: {mt5.last_error()}")
    return {
        "login": acc.login,
        "balance": acc.balance,
        "equity": acc.equity,
        "currency": acc.currency,
        "is_demo": acc.trade_mode == 0,
    }


def get_todays_closed_pnl() -> float:
    _ensure_init()
    import MetaTrader5 as mt5

    now = datetime.now()
    start_of_day = datetime(now.year, now.month, now.day)
    deals = mt5.history_deals_get(start_of_day, now + timedelta(minutes=1))
    if deals is None:
        return 0.0
    return float(sum(d.profit + d.swap + d.commission for d in deals))


def _filling_modes(symbol: str) -> list:
    """Fill policies to try for `symbol`, best guess first.

    symbol_info().filling_mode is a bitmask of what the broker allows
    (1 = FOK, 2 = IOC). We put the advertised ones first and still keep
    the others as fallbacks, because some demo servers under-report.
    """
    import MetaTrader5 as mt5

    mt5.symbol_select(symbol, True)
    info = mt5.symbol_info(symbol)
    mask = getattr(info, "filling_mode", 0) if info is not None else 0

    preferred, fallback = [], []
    (preferred if mask & 1 else fallback).append(mt5.ORDER_FILLING_FOK)
    (preferred if mask & 2 else fallback).append(mt5.ORDER_FILLING_IOC)
    fallback.append(mt5.ORDER_FILLING_RETURN)
    return preferred + fallback


def place_order(
    symbol: str,
    direction: str,          # "buy" | "sell"
    lot_size: float,
    stop_loss: float | None = None,
    take_profit: float | None = None,
    comment: str = "investment-desk",
) -> dict:
    _ensure_init()
    import MetaTrader5 as mt5

    acc = mt5.account_info()
    if acc is None or acc.trade_mode != 0:
        raise RuntimeError("Refusing to place order: account is not a demo account.")

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"No tick for {symbol}: {mt5.last_error()}")

    order_type = mt5.ORDER_TYPE_BUY if direction == "buy" else mt5.ORDER_TYPE_SELL
    price = tick.ask if direction == "buy" else tick.bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": order_type,
        "price": price,
        "deviation": 20,
        "magic": 20260831,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
    }
    if stop_loss is not None:
        request["sl"] = stop_loss
    if take_profit is not None:
        request["tp"] = take_profit

    # Brokers differ on which fill policies they accept, and a symbol that
    # rejects IOC returns 10030 "Unsupported filling mode" rather than
    # telling you what it wants. Ask the symbol what it supports, then
    # fall back through the alternatives if it still refuses.
    for filling in _filling_modes(symbol):
        request["type_filling"] = filling
        result = mt5.order_send(request)
        if result is None:
            raise RuntimeError(f"order_send returned None: {mt5.last_error()}")
        if result.retcode != mt5.TRADE_RETCODE_INVALID_FILL:
            break
        logger.warning("Filling mode %s rejected for %s, trying the next one.", filling, symbol)

    return {
        "retcode": result.retcode,
        "success": result.retcode == mt5.TRADE_RETCODE_DONE,
        "order_id": result.order,
        "deal_id": result.deal,
        "price": result.price,
        "volume": result.volume,
        "comment": result.comment,
    }
