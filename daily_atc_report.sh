#!/usr/bin/env bash
# daily_atc_report.sh
# Fires a daily AT&C analytics webhook to OpenClaw for management reporting.
# Cron example: 0 6 * * * /home/user/dotclaw/daily_atc_report.sh >> /var/log/atc_report.log 2>&1

set -euo pipefail

# Load .env if present
if [ -f "$(dirname "$0")/.env" ]; then
  # shellcheck source=.env
  set -a
  source "$(dirname "$0")/.env"
  set +a
fi

WEBHOOK_URL="${OPENCLAW_WEBHOOK_URL:-http://localhost:18789/hooks/agent}"
WEBHOOK_TOKEN="${OPENCLAW_WEBHOOK_TOKEN:-WEBHOOK-SECRET-2026}"
REPORT_DATE=$(date +"%Y-%m-%d")

PAYLOAD=$(cat <<EOF
{
  "message": "Daily AT&C Management Report — ${REPORT_DATE}. Please run the AT&C analytics skill for the past 7 days using the atc-analytics skill. Fetch the data from the MDMS API, compute week-over-week loss delta, identify the top 3 loss-contributing feeders, and format the output as a concise daily management summary suitable for WhatsApp delivery. Highlight any feeder above 20% AT&C loss in bold and recommend immediate field action. Deliver this report to the WhatsApp number on record.",
  "agentId": "discom-ot-agent",
  "wakeMode": "now",
  "deliver": true
}
EOF
)

echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Firing daily AT&C report webhook..."
echo "  URL        : ${WEBHOOK_URL}"
echo "  Report Date: ${REPORT_DATE}"
echo ""

HTTP_STATUS=$(curl -s -o /tmp/openclaw_atc_response.json -w "%{http_code}" \
  -X POST "${WEBHOOK_URL}" \
  -H "Content-Type: application/json" \
  -H "x-openclaw-token: ${WEBHOOK_TOKEN}" \
  -d "${PAYLOAD}")

echo "HTTP Status: ${HTTP_STATUS}"
if [ -f /tmp/openclaw_atc_response.json ]; then
  echo "Response:"
  cat /tmp/openclaw_atc_response.json
  echo ""
fi

if [ "${HTTP_STATUS}" -ge 200 ] && [ "${HTTP_STATUS}" -lt 300 ]; then
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] Daily AT&C report delivered successfully."
else
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] ERROR: Webhook delivery failed with HTTP ${HTTP_STATUS}." >&2
  exit 1
fi
