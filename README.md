# DISCOM OT Intelligence POC

A self-hosted proof-of-concept that connects simulated DISCOM OT data (SCADA, OMS, MDMS/AMI)
to an OpenClaw AI agent and delivers responses via WhatsApp.

---

## Architecture Overview

```
┌─────────────────────────────────┐
│   Mock OT API Server (Flask)    │  ← port 5000
│  /scada  /oms  /mdms            │
└────────────────┬────────────────┘
                 │ HTTP (Bearer token)
        ┌────────▼────────┐
        │  OpenClaw Skills │
        │  scada-feeder    │
        │  outage-status   │
        │  atc-analytics   │
        │  ami-meters      │
        └────────┬─────────┘
                 │
        ┌────────▼────────┐
        │  OpenClaw Agent  │  ← port 18789
        │  discom-ot-agent │
        └────────┬─────────┘
                 │ WhatsApp
        ┌────────▼────────┐
        │  Field Operator  │
        └─────────────────┘
```

---

## Project Structure

```
dotclaw/
├── mock_ot_api/
│   └── app.py                     # Flask mock OT API server
├── skills/
│   ├── scada-feeder/
│   │   ├── SKILL.md
│   │   └── scripts/fetch_feeder.py
│   ├── outage-status/
│   │   ├── SKILL.md
│   │   └── scripts/fetch_outages.py
│   ├── atc-analytics/
│   │   ├── SKILL.md
│   │   └── scripts/run_atc.py
│   └── ami-meters/
│       ├── SKILL.md
│       └── scripts/fetch_anomalies.py
├── trigger_fault.sh               # One-shot fault alert webhook
├── daily_atc_report.sh            # Cron-compatible daily report webhook
├── .env                           # Environment variables
├── requirements.txt               # Python dependencies
└── README.md
```

---

## Setup Instructions

### Step 1 — Install Dependencies

```bash
# Enter the project directory
cd ~/dotclaw

# Create and activate a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

---

### Step 2 — Start the Mock OT API Server

Run the Flask server as a background service:

```bash
# From the project root
cd ~/dotclaw

# Start in background, redirect logs
python mock_ot_api/app.py &> /tmp/ot_api.log &
echo "Mock OT API PID: $!"

# Verify it is running
curl -s -H "Authorization: Bearer OT-POC-TOKEN-2026" \
     http://localhost:5000/scada/feeders/FDR-002/live | python3 -m json.tool
```

Expected response:
```json
{
    "feeder_id": "FDR-002",
    "load_mw": 18.7,
    "voltage_kv": 10.8,
    "power_factor": 0.91,
    "capacity_percent": 93.5,
    "status": "overload",
    "timestamp": "2026-03-19T08:34:12Z"
}
```

To stop the server:
```bash
kill $(lsof -ti:5000)
```

---

### Step 3 — Install OpenClaw Skills

Copy the skill directories into OpenClaw's skills folder:

```bash
# Create the OpenClaw skills directory if it doesn't exist
mkdir -p ~/.openclaw/skills

# Copy all four skills
cp -r ~/dotclaw/skills/scada-feeder  ~/.openclaw/skills/
cp -r ~/dotclaw/skills/outage-status ~/.openclaw/skills/
cp -r ~/dotclaw/skills/atc-analytics ~/.openclaw/skills/
cp -r ~/dotclaw/skills/ami-meters    ~/.openclaw/skills/

# Make scripts executable
chmod +x ~/.openclaw/skills/*/scripts/*.py

# Verify installation
ls ~/.openclaw/skills/
```

---

### Step 4 — Run Test Queries

**Scenario 1 — SCADA Feeder Status (check overloaded feeder)**

```bash
python ~/.openclaw/skills/scada-feeder/scripts/fetch_feeder.py --feeder FDR-002
```

Check a degraded feeder:
```bash
python ~/.openclaw/skills/scada-feeder/scripts/fetch_feeder.py --feeder FDR-006
```

**Scenario 2 — OMS Outage Status (all zones)**

```bash
python ~/.openclaw/skills/outage-status/scripts/fetch_outages.py
```

Filtered by zone:
```bash
python ~/.openclaw/skills/outage-status/scripts/fetch_outages.py --zone Zone-A
```

**Scenario 3 — AT&C Analytics (7-day executive summary)**

```bash
python ~/.openclaw/skills/atc-analytics/scripts/run_atc.py
```

3-day report:
```bash
python ~/.openclaw/skills/atc-analytics/scripts/run_atc.py --days 3
```

**Scenario 4 — AMI Meter Anomalies (all types)**

```bash
python ~/.openclaw/skills/ami-meters/scripts/fetch_anomalies.py
```

Tamper events only:
```bash
python ~/.openclaw/skills/ami-meters/scripts/fetch_anomalies.py --type tamper
```

Communication failures:
```bash
python ~/.openclaw/skills/ami-meters/scripts/fetch_anomalies.py --type comm_failure
```

---

### Step 5 — Fire the Fault Alert Webhook

Ensure OpenClaw is running with the `discom-ot-agent` configured and listening on port 18789.

**Immediate fault alert:**
```bash
cd ~/dotclaw
./trigger_fault.sh
```

**Daily AT&C report (manual trigger):**
```bash
cd ~/dotclaw
./daily_atc_report.sh
```

**Add to cron for automated daily delivery at 06:00:**
```bash
crontab -e
```

Add this line:
```
0 6 * * * /home/user/dotclaw/daily_atc_report.sh >> /var/log/atc_report.log 2>&1
```

---

## API Reference

The Mock OT API requires the header `Authorization: Bearer OT-POC-TOKEN-2026` on all requests.

| Endpoint                          | Method | Description                     |
|-----------------------------------|--------|---------------------------------|
| `/scada/feeders/<feeder_id>/live` | GET    | Live SCADA telemetry            |
| `/oms/outages`                    | GET    | Active outages (`?zone=Zone-A`) |
| `/mdms/atc`                       | GET    | AT&C loss data (`?days=7`)      |
| `/mdms/meters/anomalies`          | GET    | Meter anomalies (`?type=tamper`)|

**Seeded Feeders:** FDR-001 through FDR-010
- FDR-002: 93.5% capacity (overload)
- FDR-004: 87.0% capacity (warning)
- FDR-006: degraded status

**Seeded Outages:** 3 outages across Zone-A (2) and Zone-B (1)

**Seeded Anomalies:** 14 anomalies across DT-001, DT-002, DT-003

---

## Environment Variables

| Variable                 | Default                              | Description                  |
|--------------------------|--------------------------------------|------------------------------|
| `OT_API_BASE`            | `http://localhost:5000`              | Mock OT API base URL         |
| `OT_API_TOKEN`           | `OT-POC-TOKEN-2026`                  | Bearer token for OT API      |
| `OPENCLAW_WEBHOOK_URL`   | `http://localhost:18789/hooks/agent` | OpenClaw webhook endpoint    |
| `OPENCLAW_WEBHOOK_TOKEN` | `WEBHOOK-SECRET-2026`                | OpenClaw webhook secret      |
| `WHATSAPP_TEST_NUMBER`   | `+919999999999`                      | WhatsApp delivery target     |

Edit `.env` in the project root to override defaults.

---

## Troubleshooting

**API returns 401:** Verify `OT_API_TOKEN` in `.env` matches `OT-POC-TOKEN-2026`.

**API returns connection refused:** Start the mock server with `python mock_ot_api/app.py &`.

**Webhook returns connection refused:** Ensure OpenClaw agent is running on port 18789.

**Skills not found by OpenClaw:** Confirm skills are copied to `~/.openclaw/skills/` and
the SKILL.md files are present in each skill root directory.
