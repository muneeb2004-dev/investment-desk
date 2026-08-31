"""
Small adapter between backend/ (FastAPI, MT5, Firestore) and the
top-level strategies/ package (pure functions, no I/O) — keeps the
strategy library dependency-free and independently testable.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from strategies.technical import PRESET_STRATEGIES, run_preset  # noqa: E402
from strategies.investment import Fundamentals, screen, screen_many  # noqa: E402


def run_all_technical_presets(candles) -> list[dict]:
    return [fn(candles) for fn in PRESET_STRATEGIES.values()]


__all__ = ["run_preset", "run_all_technical_presets", "Fundamentals", "screen", "screen_many"]
