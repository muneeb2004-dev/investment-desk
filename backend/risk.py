"""
Risk & Sizing Agent logic.

This module is the security/governance backbone of the whole system:
the Execution Agent is NOT allowed to place an order without a valid,
unexpired, correctly-signed token from `approve_or_reject()` below —
so no other agent (and no prompt-injected instruction reaching an
agent) can cause a trade to fire without passing through the daily
loss cap check first.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time

from . import firestore_client as fs
from . import mt5_client
from .config import settings

TOKEN_TTL_SECONDS = 120  # a risk approval is only valid for 2 minutes


def _sign(payload: dict) -> str:
    body = json.dumps(payload, sort_keys=True).encode()
    mac = hmac.new(settings.RISK_TOKEN_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return f"{body.hex()}.{mac}"


def _verify(token: str) -> dict | None:
    try:
        body_hex, mac = token.split(".")
        body = bytes.fromhex(body_hex)
        expected = hmac.new(settings.RISK_TOKEN_SECRET.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(mac, expected):
            return None
        payload = json.loads(body)
        if payload["expires_at"] < time.time():
            return None
        return payload
    except Exception:
        return None


def compute_position_size(
    account_balance: float,
    risk_per_trade_pct: float,
    stop_loss_pips: float,
    pip_value_per_lot: float,
) -> float:
    if stop_loss_pips <= 0 or pip_value_per_lot <= 0:
        return 0.0
    risk_amount = account_balance * (risk_per_trade_pct / 100)
    lots = risk_amount / (stop_loss_pips * pip_value_per_lot)
    # round down to broker's typical 0.01 lot step, floor at 0
    return max(0.0, round(lots - 0.005, 2))


def approve_or_reject(user_id: str, symbol: str, direction: str, stop_loss_pips: float) -> dict:
    """
    The single choke point every order must pass through. Checks the
    user's daily loss cap against risk already committed + realized
    P&L today, sizes the position, and — only if it clears the cap —
    issues a short-lived signed approval token for /execute-order.
    """
    profile = fs.get_risk_profile(user_id)
    risk_state = fs.get_today_risk_state(user_id)
    account = mt5_client.get_account_summary()

    cap_amount = account["balance"] * (profile["daily_loss_cap_pct"] / 100)
    used_today = risk_state["risk_committed_today"] - min(0, risk_state["realized_pnl_today"])
    remaining = cap_amount - used_today

    risk_amount = account["balance"] * (profile["risk_per_trade_pct"] / 100)

    result = {
        "user_id": user_id,
        "symbol": symbol,
        "direction": direction,
        "account_balance": account["balance"],
        "daily_loss_cap_pct": profile["daily_loss_cap_pct"],
        "cap_amount": round(cap_amount, 2),
        "used_today": round(used_today, 2),
        "remaining_today": round(remaining, 2),
        "planned_risk_amount": round(risk_amount, 2),
    }

    if remaining <= 0:
        result.update(approved=False, reason="Daily loss cap already reached — no new orders today.")
        fs.append_audit_log(user_id, "risk_agent", "reject", result)
        return result

    if risk_amount > remaining:
        # scale this trade's risk down to whatever budget is left
        risk_amount = remaining
        result["planned_risk_amount"] = round(risk_amount, 2)
        result["note"] = "Risk per trade scaled down to remaining daily budget."

    pip_value = mt5_client.get_pip_value_per_lot(symbol)
    lot_size = compute_position_size(account["balance"], (risk_amount / account["balance"]) * 100, stop_loss_pips, pip_value)

    if lot_size <= 0:
        result.update(approved=False, reason="Computed lot size rounded to 0 — stop loss too wide for remaining risk budget.")
        fs.append_audit_log(user_id, "risk_agent", "reject", result)
        return result

    payload = {
        "user_id": user_id,
        "symbol": symbol,
        "direction": direction,
        "lot_size": lot_size,
        "risk_amount": round(risk_amount, 2),
        "expires_at": time.time() + TOKEN_TTL_SECONDS,
    }
    token = _sign(payload)

    result.update(approved=True, lot_size=lot_size, approval_token=token, expires_in_seconds=TOKEN_TTL_SECONDS)
    fs.append_audit_log(user_id, "risk_agent", "approve", result)
    return result


def consume_approval(token: str) -> dict | None:
    """Verify a token and mark its risk as committed. Returns the payload, or None if invalid/expired."""
    payload = _verify(token)
    if payload is None:
        return None
    fs.add_committed_risk(payload["user_id"], payload["risk_amount"])
    return payload
