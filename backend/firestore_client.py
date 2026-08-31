"""
Firestore persistence layer — this is the "long-term state persistence"
and "audit trail" piece the Fortified Enterprise Fleet track is judged
on. Collections:

  users/{user_id}
      .risk_profile              (daily_loss_cap_pct, risk_per_trade_pct)
      strategies/{strategy_id}   (preset or custom, per Trading/Investment desk)
      watchlist/{symbol}         (which desk + strategy to run per symbol)
      risk_state/{yyyy-mm-dd}    (risk committed / realized P&L today)
      audit_log/{entry_id}       (every agent decision — approvals, rejections, orders)
  reports/{user_id}/entries/{yyyy-mm-dd}   (daily report content)

Requires GOOGLE_CLOUD_PROJECT + credentials (service account JSON via
GOOGLE_APPLICATION_CREDENTIALS, or `gcloud auth application-default login`).
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from google.cloud import firestore

from .config import settings

_db: firestore.Client | None = None


def db() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(project=settings.GOOGLE_CLOUD_PROJECT or None)
    return _db


def _today() -> str:
    return dt.date.today().isoformat()


# --------------------------------------------------------------------------
# Risk profile
# --------------------------------------------------------------------------

def get_risk_profile(user_id: str) -> dict:
    doc = db().collection("users").document(user_id).get()
    data = (doc.to_dict() or {}).get("risk_profile") if doc.exists else None
    return data or {
        "daily_loss_cap_pct": settings.DEFAULT_DAILY_LOSS_CAP_PCT,
        "risk_per_trade_pct": settings.DEFAULT_RISK_PER_TRADE_PCT,
    }


def set_risk_profile(user_id: str, daily_loss_cap_pct: float, risk_per_trade_pct: float) -> None:
    db().collection("users").document(user_id).set(
        {"risk_profile": {"daily_loss_cap_pct": daily_loss_cap_pct, "risk_per_trade_pct": risk_per_trade_pct}},
        merge=True,
    )


# --------------------------------------------------------------------------
# Risk state (today's committed risk vs cap)
# --------------------------------------------------------------------------

def get_today_risk_state(user_id: str) -> dict:
    ref = db().collection("users").document(user_id).collection("risk_state").document(_today())
    doc = ref.get()
    if doc.exists:
        return doc.to_dict()
    state = {"date": _today(), "risk_committed_today": 0.0, "realized_pnl_today": 0.0}
    ref.set(state)
    return state


def add_committed_risk(user_id: str, amount: float) -> dict:
    ref = db().collection("users").document(user_id).collection("risk_state").document(_today())
    ref.set(
        {"date": _today(), "risk_committed_today": firestore.Increment(amount)},
        merge=True,
    )
    return ref.get().to_dict()


def sync_realized_pnl(user_id: str, realized_pnl_today: float) -> None:
    ref = db().collection("users").document(user_id).collection("risk_state").document(_today())
    ref.set({"date": _today(), "realized_pnl_today": realized_pnl_today}, merge=True)


# --------------------------------------------------------------------------
# Strategies (preset selections + custom, from the Strategy Builder Agent)
# --------------------------------------------------------------------------

def save_strategy(user_id: str, name: str, desk: str, mode: str, definition: dict) -> str:
    """desk: 'trading' | 'investment'.  mode: 'preset' | 'custom'."""
    strategy_id = str(uuid.uuid4())[:8]
    db().collection("users").document(user_id).collection("strategies").document(strategy_id).set(
        {
            "strategy_id": strategy_id,
            "name": name,
            "desk": desk,
            "mode": mode,
            "definition": definition,
            "created_at": dt.datetime.utcnow().isoformat(),
        }
    )
    return strategy_id


def list_strategies(user_id: str, desk: str | None = None) -> list[dict]:
    ref = db().collection("users").document(user_id).collection("strategies")
    docs = ref.stream()
    items = [d.to_dict() for d in docs]
    if desk:
        items = [i for i in items if i.get("desk") == desk]
    return items


# --------------------------------------------------------------------------
# Watchlist
# --------------------------------------------------------------------------

def set_watchlist_entry(user_id: str, symbol: str, desk: str, strategy_id: str) -> None:
    db().collection("users").document(user_id).collection("watchlist").document(symbol).set(
        {"symbol": symbol, "desk": desk, "strategy_id": strategy_id}
    )


def get_watchlist(user_id: str) -> list[dict]:
    docs = db().collection("users").document(user_id).collection("watchlist").stream()
    return [d.to_dict() for d in docs]


# --------------------------------------------------------------------------
# Audit log — every agent decision, approval, rejection, and order
# --------------------------------------------------------------------------

def append_audit_log(user_id: str, agent: str, action: str, details: dict[str, Any]) -> str:
    entry_id = str(uuid.uuid4())
    db().collection("users").document(user_id).collection("audit_log").document(entry_id).set(
        {
            "entry_id": entry_id,
            "timestamp": dt.datetime.utcnow().isoformat(),
            "agent": agent,
            "action": action,
            "details": details,
        }
    )
    return entry_id


def get_audit_log(user_id: str, limit: int = 50) -> list[dict]:
    docs = (
        db().collection("users").document(user_id).collection("audit_log")
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit).stream()
    )
    return [d.to_dict() for d in docs]


# --------------------------------------------------------------------------
# Daily reports
# --------------------------------------------------------------------------

def save_report(user_id: str, content: dict) -> None:
    db().collection("reports").document(user_id).collection("entries").document(_today()).set(
        {"date": _today(), "generated_at": dt.datetime.utcnow().isoformat(), **content}
    )


def get_report(user_id: str, date: str | None = None) -> dict | None:
    doc = (
        db().collection("reports").document(user_id).collection("entries")
        .document(date or _today()).get()
    )
    return doc.to_dict() if doc.exists else None
