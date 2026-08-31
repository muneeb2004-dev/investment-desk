#!/usr/bin/env bash
# Creates the Cloud Scheduler job that fires the 8am daily report.
#
# Usage:
#   BACKEND_URL="https://xxxx.trycloudflare.com" \
#   BACKEND_API_KEY="your-key" \
#   USER_ID="muneeb" \
#   GCP_PROJECT="your-gcp-project-id" \
#   ./setup_cloud_scheduler.sh
#
# NOTE: quick tunnels (cloudflared / ngrok free tier) get a NEW url
# every time you restart them. If you restart the tunnel, re-run this
# script (or `gcloud scheduler jobs update http ...`) with the new URL
# before recording the demo video — otherwise the job will 404.
# For anything past the hackathon, swap in a named Cloudflare Tunnel
# (stable subdomain, needs a Cloudflare account + domain) or deploy
# this backend piece behind a static Cloud Run URL instead.

set -euo pipefail

: "${BACKEND_URL:?Set BACKEND_URL to your tunnel URL, e.g. https://xxxx.trycloudflare.com}"
: "${BACKEND_API_KEY:?Set BACKEND_API_KEY to match backend/.env}"
: "${USER_ID:?Set USER_ID to the user this report is for, e.g. muneeb}"
: "${GCP_PROJECT:?Set GCP_PROJECT to your GCP project id}"
TIMEZONE="${TIMEZONE:-America/Los_Angeles}"

gcloud config set project "$GCP_PROJECT"

gcloud services enable cloudscheduler.googleapis.com

gcloud scheduler jobs create http investment-desk-daily-report \
  --schedule="0 8 * * *" \
  --time-zone="$TIMEZONE" \
  --uri="${BACKEND_URL}/daily-report" \
  --http-method=POST \
  --headers="Content-Type=application/json,X-Backend-Api-Key=${BACKEND_API_KEY}" \
  --message-body="{\"user_id\": \"${USER_ID}\"}" \
  --description="Investment Desk — personalized 8am daily report (Reporting Agent trigger)" \
  || gcloud scheduler jobs update http investment-desk-daily-report \
  --schedule="0 8 * * *" \
  --time-zone="$TIMEZONE" \
  --uri="${BACKEND_URL}/daily-report" \
  --http-method=POST \
  --headers="Content-Type=application/json,X-Backend-Api-Key=${BACKEND_API_KEY}" \
  --message-body="{\"user_id\": \"${USER_ID}\"}"

echo "Done. Trigger it once right now to prove it works, without waiting for 8am:"
echo "  gcloud scheduler jobs run investment-desk-daily-report"
