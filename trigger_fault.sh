#!/usr/bin/env bash
# trigger_fault.sh
# Fires a fault alert webhook to OpenClaw for a DISCOM OT fault event.
# Usage: ./trigger_fault.sh

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

FEEDER_ID="FDR-002"
FAULT_TYPE="HT Cable Fault"
VOLTAGE_DEVIATION="-12.5"

PAYLOAD=$(cat <<EOF
{
  "message": "FAULT ALERT — Feeder ${FEEDER_ID} has reported a ${FAULT_TYPE}. Voltage deviation of ${VOLTAGE_DEVIATION}% detected (10.8 kV vs nominal 11.0 kV). Approximately 1,240 consumers are affected in Zone-A. Recommended action: Dispatch crew immediately, isolate the faulty section, and restore supply via alternate feeder FDR-003 if available. Update OMS crew status once team is en route.",
  "agentId": "discom-ot-agent",
  "wakeMode": "now",
  "deliver": true
}
EOF
)

echo "Firing fault alert webhook..."
echo "  URL      : ${WEBHOOK_URL}"
echo "  Feeder   : ${FEEDER_ID}"
echo "  Fault    : ${FAULT_TYPE}"
echo "  Voltage  : ${VOLTAGE_DEVIATION}%"
echo ""

HTTP_STATUS=$(curl -s -o /tmp/openclaw_fault_response.json -w "%{http_code}" \
  -X POST "${WEBHOOK_URL}" \
  -H "Content-Type: application/json" \
  -H "x-openclaw-token: ${WEBHOOK_TOKEN}" \
  -d "${PAYLOAD}")

echo "HTTP Status: ${HTTP_STATUS}"
if [ -f /tmp/openclaw_fault_response.json ]; then
  echo "Response:"
  cat /tmp/openclaw_fault_response.json
  echo ""
fi

if [ "${HTTP_STATUS}" -ge 200 ] && [ "${HTTP_STATUS}" -lt 300 ]; then
  echo "Fault alert delivered successfully."
else
  echo "ERROR: Webhook delivery failed with HTTP ${HTTP_STATUS}." >&2
  exit 1
fi
