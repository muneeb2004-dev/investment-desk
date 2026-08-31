@echo off
REM Run this in a SECOND terminal, after start_backend.bat is already running.
REM Exposes your local backend at a public https:// URL that Gemini
REM Enterprise (and Cloud Scheduler) can reach.
REM
REM If you don't have cloudflared installed:
REM   winget install --id Cloudflare.cloudflared
REM (or download from https://github.com/cloudflare/cloudflared/releases)
REM
REM The URL printed below (something like https://xxxx.trycloudflare.com)
REM is the BACKEND_URL you paste into the Gemini Enterprise tool config
REM and into scripts\setup_cloud_scheduler.sh. It changes every time you
REM restart this — if you restart it, update both places again.

cloudflared tunnel --url http://localhost:8000
