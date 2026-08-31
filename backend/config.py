"""
Central config, loaded from environment variables (via a local .env
file — see .env.example). Nothing in this file is a real secret;
Muneeb fills in the actual values on his own machine.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # --- MT5 demo account (fill in locally, never commit real values) ---
    MT5_LOGIN: int = int(os.getenv("MT5_LOGIN", "0") or 0)
    MT5_PASSWORD: str = os.getenv("MT5_PASSWORD", "")
    MT5_SERVER: str = os.getenv("MT5_SERVER", "")
    MT5_TERMINAL_PATH: str = os.getenv("MT5_TERMINAL_PATH", "")  # optional, path to terminal64.exe

    # --- Google Cloud ---
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    # GOOGLE_APPLICATION_CREDENTIALS env var (path to service account JSON)
    # is picked up automatically by the Firestore client library if set;
    # otherwise `gcloud auth application-default login` works too.

    # --- Risk defaults (per-user overrides live in Firestore) ---
    DEFAULT_DAILY_LOSS_CAP_PCT: float = float(os.getenv("DEFAULT_DAILY_LOSS_CAP_PCT", "2.0"))  # % of balance
    DEFAULT_RISK_PER_TRADE_PCT: float = float(os.getenv("DEFAULT_RISK_PER_TRADE_PCT", "0.5"))  # % of balance

    # --- Backend auth (Gemini Enterprise -> this API) ---
    BACKEND_API_KEY: str = os.getenv("BACKEND_API_KEY", "")  # shared secret, checked on every call

    # --- Signs risk-approval tokens so /execute-order can prove a real
    #     risk check happened (and wasn't skipped or replayed) ---
    RISK_TOKEN_SECRET: str = os.getenv("RISK_TOKEN_SECRET", "")

    # --- Reporting ---
    REPORT_RECIPIENTS: str = os.getenv("REPORT_RECIPIENTS", "")  # comma-separated, optional


settings = Settings()
