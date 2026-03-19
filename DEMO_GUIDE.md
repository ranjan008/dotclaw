# DISCOM OT Intelligence POC — Demo Guide

**Audience:** DISCOM leadership, operations managers, IT/OT teams
**Duration:** 30–45 minutes
**Format:** Laptop demo, terminal + WhatsApp side-by-side

---

## What This POC Demonstrates

OpenClaw connects your existing OT systems — SCADA, OMS, and MDMS/AMI — to a conversational
AI agent that any operator can query in plain language over WhatsApp. No dashboards to log in
to. No training on complex software. Just send a message and get an answer.

This demo simulates a realistic DISCOM environment with:
- 10 live feeders (2 overloaded, 1 degraded)
- 3 active outages across 2 zones
- 7 days of AT&C loss data
- 14 smart meter anomalies across 3 DT clusters

---

## Pre-Demo Checklist (Do Before the Meeting)

Run through this checklist at least 30 minutes before presenting.

```
[ ] Python 3.9+ is installed
[ ] Virtual environment created and dependencies installed
[ ] Mock OT API server is running and health-checked
[ ] All 4 OpenClaw skills are installed to ~/.openclaw/skills/
[ ] Terminal font size set to 18–20pt for readability
[ ] A second terminal tab is open for live queries
[ ] WhatsApp mock delivery is ready (or screen share arranged)
[ ] .env file has correct values
```

---

## Environment Setup (One-Time)

### 1. Clone and enter the project

```bash
git clone <repo-url> ~/dotclaw
cd ~/dotclaw
```

### 2. Create virtual environment and install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Confirm installed packages:

```bash
pip show flask requests python-dotenv tabulate | grep -E "^Name|^Version"
```

Expected output:
```
Name: Flask
Version: 3.x.x
Name: requests
Version: 2.x.x
Name: python-dotenv
Version: 1.x.x
Name: tabulate
Version: 0.9.x
```

### 3. Verify the .env file

```bash
cat .env
```

Expected output:
```
OT_API_BASE=http://localhost:5000
OT_API_TOKEN=OT-POC-TOKEN-2026
OPENCLAW_WEBHOOK_URL=http://localhost:18789/hooks/agent
OPENCLAW_WEBHOOK_TOKEN=WEBHOOK-SECRET-2026
WHATSAPP_TEST_NUMBER=+919999999999
```

### 4. Start the Mock OT API Server

```bash
source .venv/bin/activate
python mock_ot_api/app.py &> /tmp/ot_api.log &
echo "Server PID: $!"
```

Health check — this must return HTTP 200 before proceeding:

```bash
curl -s -o /dev/null -w "HTTP %{http_code}\n" \
  -H "Authorization: Bearer OT-POC-TOKEN-2026" \
  http://localhost:5000/scada/feeders/FDR-001/live
```

Expected: `HTTP 200`

Test the auth guard is working:

```bash
curl -s -o /dev/null -w "HTTP %{http_code}\n" \
  http://localhost:5000/scada/feeders/FDR-001/live
```

Expected: `HTTP 401`

### 5. Install OpenClaw Skills

```bash
mkdir -p ~/.openclaw/skills

cp -r ~/dotclaw/skills/scada-feeder  ~/.openclaw/skills/
cp -r ~/dotclaw/skills/outage-status ~/.openclaw/skills/
cp -r ~/dotclaw/skills/atc-analytics ~/.openclaw/skills/
cp -r ~/dotclaw/skills/ami-meters    ~/.openclaw/skills/

chmod +x ~/.openclaw/skills/*/scripts/*.py

ls ~/.openclaw/skills/
```

Expected:
```
ami-meters  atc-analytics  outage-status  scada-feeder
```

---

## Demo Flow

Run the scenarios in the order below. Each section includes:
- **Talking point** — what to say to the audience
- **Command to run** — exact terminal command
- **Expected output** — what they will see
- **Insight to highlight** — the business value to call out

---

### Scenario 1 — Real-Time Feeder Health Check (SCADA)

**Talking point:**
> "Right now an operator gets a call saying there's a problem with Feeder 2. Normally they'd
> log into the SCADA HMI, find the right screen, and read off the values. With OpenClaw, they
> just send a WhatsApp message. Let me show you what happens behind the scenes."

**Command:**

```bash
python ~/.openclaw/skills/scada-feeder/scripts/fetch_feeder.py --feeder FDR-002
```

**Expected output:**

```
============================================================
  SCADA LIVE TELEMETRY — FDR-002
  Timestamp : 2026-03-19T08:34:12Z
============================================================
  Load          : 18.7 MW
  Voltage       : 10.8 kV
  Power Factor  : 0.91
  Capacity Use  : 93.5%
  Status        : OVERLOAD

  *** CAPACITY WARNING: Feeder FDR-002 is at 93.5% capacity.
      Immediate load-shedding or feeder augmentation advised.
============================================================
```

**Insight to highlight:**
> "The system doesn't just return raw data — it interprets it. 93.5% capacity triggers an
> automatic warning with a recommended action. No analyst needed."

Now show a normal feeder for contrast:

```bash
python ~/.openclaw/skills/scada-feeder/scripts/fetch_feeder.py --feeder FDR-005
```

**Expected output:**

```
============================================================
  SCADA LIVE TELEMETRY — FDR-005
  Timestamp : 2026-03-19T08:34:15Z
============================================================
  Load          : 9.8 MW
  Voltage       : 11.2 kV
  Power Factor  : 0.97
  Capacity Use  : 49.0%
  Status        : NORMAL
============================================================
```

Now show a degraded feeder:

```bash
python ~/.openclaw/skills/scada-feeder/scripts/fetch_feeder.py --feeder FDR-006
```

**Expected output:**

```
============================================================
  SCADA LIVE TELEMETRY — FDR-006
  Timestamp : 2026-03-19T08:34:18Z
============================================================
  Load          : 15.3 MW
  Voltage       : 10.3 kV
  Power Factor  : 0.85
  Capacity Use  : 76.5%
  Status        : DEGRADED
============================================================
```

**Insight to highlight:**
> "FDR-006 shows degraded status — low voltage at 10.3 kV and poor power factor at 0.85.
> This is the kind of early signal that normally gets missed until it becomes an outage.
> The agent surfaces it proactively."

---

### Scenario 2 — Outage Management (OMS)

**Talking point:**
> "Shift supervisors spend a lot of time calling sub-station staff to understand which zones
> are affected and what the crew status is. Watch what a single query returns."

**Command — all active outages:**

```bash
python ~/.openclaw/skills/outage-status/scripts/fetch_outages.py
```

**Expected output:**

```
============================================================
  OMS — ACTIVE OUTAGE REPORT
  Generated : 2026-03-19 08:34:15 UTC
  Total Outages: 3  |  Total Consumers Affected: 3,920
============================================================

  ZONE: Zone-A  (2 outages)
  ──────────────────────────────────────────────────────
  [1] Feeder   : FDR-002
      Type     : UNPLANNED
      Started  : 2026-03-19 06:19 UTC  (2h 15m ago)
      Consumers: 1,240
      Crew     : On Site
      Note     : HT cable fault near substation SS-12

  [2] Feeder   : FDR-004
      Type     : UNPLANNED
      Started  : 2026-03-19 07:49 UTC  (0h 45m ago)
      Consumers: 580
      Crew     : Dispatched
      Note     : Transformer oil leakage reported

  ZONE: Zone-B  (1 outage)
  ──────────────────────────────────────────────────────
  [1] Feeder   : FDR-006
      Type     : PLANNED
      Started  : 2026-03-19 03:34 UTC  (5h 0m ago)
      Consumers: 2,100
      Crew     : Work in Progress
      Note     : Scheduled maintenance — conductor replacement

============================================================
```

**Insight to highlight:**
> "3,920 consumers affected across 3 feeders. The agent knows crew status, outage type,
> and duration — all in one place. A supervisor can assess field response without making
> a single phone call."

**Command — zone-specific query:**

```bash
python ~/.openclaw/skills/outage-status/scripts/fetch_outages.py --zone Zone-A
```

**Insight to highlight:**
> "Operators can narrow it down by zone. If the Circle SE manages Zone-A, they only see
> what's relevant to them."

---

### Scenario 3 — AT&C Loss Analytics (MDMS)

**Talking point:**
> "AT&C loss reporting today takes days — someone downloads MDMS data, builds an Excel,
> and presents it in the weekly meeting. This agent produces an executive-grade loss summary
> on demand, with trend analysis."

**Command — 7-day executive summary:**

```bash
python ~/.openclaw/skills/atc-analytics/scripts/run_atc.py
```

**Expected output:**

```
============================================================
  AT&C LOSS ANALYTICS — EXECUTIVE SUMMARY
  Report Period : 2026-03-13 to 2026-03-19  (7 days)
  Generated     : 2026-03-19 08:34:15 UTC
============================================================

  PERIOD OVERVIEW
  ──────────────────────────────────────────────────────
  Avg AT&C Loss     : 19.34%
  Latest Day Loss   : 18.9%   (2026-03-19)
  First Day Loss    : 18.4%   (2026-03-13)
  Week-over-Week    : +0.5 pp  [WORSENING]

  DAILY TREND
  ──────────────────────────────────────────────────────
  Date         Input(MU)  Billed(MU)  Loss%
  2026-03-13   120.00     97.92       18.4%
  2026-03-14   120.50     97.61       19.1%
  2026-03-15   121.00     99.68       17.8%
  2026-03-16   121.50     96.82       20.3%
  2026-03-17   122.00     98.00       19.7%
  2026-03-18   122.50     96.62       21.2%
  2026-03-19   123.00     99.73       18.9%

  TOP 3 LOSS FEEDERS (latest day)
  ──────────────────────────────────────────────────────
  #1  FDR-006  :  22.1%  [ACTION REQUIRED]
  #2  FDR-002  :  20.7%
  #3  FDR-004  :  19.8%

============================================================
  RECOMMENDATION: Review FDR-006 for commercial loss drivers
  (meter bypass, DT losses). Field verification advised.
============================================================
```

**Insight to highlight:**
> "Week-over-week trend is worsening — up 0.5 percentage points. The agent immediately
> identifies FDR-006 as the top loss feeder at 22.1% and flags it for action. This is
> the kind of insight that normally sits buried in a Monday morning report."

**Command — quick 3-day view:**

```bash
python ~/.openclaw/skills/atc-analytics/scripts/run_atc.py --days 3
```

> "You can ask for any window. A CMD can get a quick 3-day view before a review meeting
> without waiting for a report to be prepared."

---

### Scenario 4 — Smart Meter Anomaly Detection (AMI)

**Talking point:**
> "Revenue protection and AMI performance are major pain points. Right now, field teams
> do periodic checks and anomalies pile up in the MDMS. The agent gives you a live view
> of every anomaly, grouped by DT cluster, with a recommended action."

**Command — full anomaly report:**

```bash
python ~/.openclaw/skills/ami-meters/scripts/fetch_anomalies.py
```

**Expected output:**

```
============================================================
  AMI METER ANOMALY REPORT
  Generated : 2026-03-19 08:34:15 UTC
  Total Anomalies: 14   Filter: ALL
============================================================

  DT CLUSTER: DT-001  (5 anomalies)
  ──────────────────────────────────────────────────────
  Meter ID     Sector       Type           Days Silent
  MTR-10011    residential  TAMPER         3
  MTR-10012    residential  ZERO_READ      7
  MTR-10013    commercial   COMM_FAILURE   2
  MTR-10014    residential  TAMPER         5
  MTR-10015    residential  ZERO_READ      14

  Recommended Action: Multiple anomaly types detected. Prioritise
  tamper events first, followed by zero-read verification, then
  communication restoration.

  DT CLUSTER: DT-002  (5 anomalies)
  ──────────────────────────────────────────────────────
  Meter ID     Sector       Type           Days Silent
  MTR-20021    industrial   COMM_FAILURE   1
  MTR-20022    residential  TAMPER         4
  MTR-20023    residential  ZERO_READ      9
  MTR-20024    commercial   COMM_FAILURE   3
  MTR-20025    residential  TAMPER         6

  Recommended Action: Multiple anomaly types detected. Prioritise
  tamper events first, followed by zero-read verification, then
  communication restoration.

  DT CLUSTER: DT-003  (4 anomalies)
  ──────────────────────────────────────────────────────
  Meter ID     Sector       Type           Days Silent
  MTR-30031    residential  COMM_FAILURE   2
  MTR-30032    residential  ZERO_READ      11
  MTR-30033    commercial   TAMPER         8
  MTR-30034    residential  COMM_FAILURE   1

  Recommended Action: Multiple anomaly types detected. Prioritise
  tamper events first, followed by zero-read verification, then
  communication restoration.

============================================================
  SUMMARY BY ANOMALY TYPE
  ──────────────────────────────────────────────────────
  COMM FAILURE   : 5 meters
  TAMPER         : 5 meters
  ZERO READ      : 4 meters
============================================================
```

**Insight to highlight:**
> "14 anomalies, 3 DT clusters. MTR-10015 hasn't been read in 14 days — that's potential
> revenue leakage. MTR-30033 is flagged as tamper — that's a field visit with FIR potential.
> The agent doesn't just list anomalies, it tells the revenue protection team where to go first."

**Command — tamper-only filter:**

```bash
python ~/.openclaw/skills/ami-meters/scripts/fetch_anomalies.py --type tamper
```

> "A revenue protection officer on WhatsApp can ask: 'show me only tamper cases' and get
> a targeted list for field dispatch — no login, no report download."

---

### Scenario 5 — Fault Alert via WhatsApp Webhook

**Talking point:**
> "This is the proactive intelligence piece. When a fault is detected in SCADA — say a
> voltage deviation on FDR-002 — the system automatically fires an alert to the OpenClaw
> agent, which formats a human-readable message and delivers it to the Circle SE's WhatsApp.
> No one has to remember to check a dashboard."

**Command:**

```bash
./trigger_fault.sh
```

**Expected output:**

```
Firing fault alert webhook...
  URL      : http://localhost:18789/hooks/agent
  Feeder   : FDR-002
  Fault    : HT Cable Fault
  Voltage  : -12.5%

HTTP Status: 200
Response:
{"status": "accepted", "agentId": "discom-ot-agent"}

Fault alert delivered successfully.
```

**Explain the payload being sent:**

```json
{
  "message": "FAULT ALERT — Feeder FDR-002 has reported a HT Cable Fault.
              Voltage deviation of -12.5% detected (10.8 kV vs nominal 11.0 kV).
              Approximately 1,240 consumers are affected in Zone-A.
              Recommended action: Dispatch crew immediately, isolate the faulty section,
              and restore supply via alternate feeder FDR-003 if available.",
  "agentId": "discom-ot-agent",
  "wakeMode": "now",
  "deliver": true
}
```

**Insight to highlight:**
> "The agent wakes up immediately, formats this into a WhatsApp message, and sends it to
> the registered number. The SE gets the alert before the helpdesk even starts logging the
> complaint. This is shift from reactive to proactive operations."

---

### Scenario 6 — Daily AT&C Report Automation

**Talking point:**
> "Every morning at 6 AM, this script fires automatically via cron. The agent runs the
> AT&C analytics, formats a management summary, and delivers it to the CMD's WhatsApp
> before the morning meeting starts."

**Command (manual trigger to demonstrate):**

```bash
./daily_atc_report.sh
```

**Expected output:**

```
[2026-03-19T06:00:00Z] Firing daily AT&C report webhook...
  URL        : http://localhost:18789/hooks/agent
  Report Date: 2026-03-19

HTTP Status: 200
Response:
{"status": "accepted", "agentId": "discom-ot-agent"}

[2026-03-19T06:00:01Z] Daily AT&C report delivered successfully.
```

**Show the cron setup:**

```bash
crontab -l
# Add: 0 6 * * * /home/user/dotclaw/daily_atc_report.sh >> /var/log/atc_report.log 2>&1
```

**Insight to highlight:**
> "One line in cron. No server to manage, no scheduled report to configure in a BI tool.
> The management team gets their morning brief automatically on their personal WhatsApp."

---

## Troubleshooting During Demo

| Symptom | Likely Cause | Fix |
|---|---|---|
| `connection refused` on port 5000 | Server not running | `python mock_ot_api/app.py &` |
| `HTTP 401` from skill script | Wrong token in .env | Check `OT_API_TOKEN=OT-POC-TOKEN-2026` |
| `ModuleNotFoundError` | venv not activated | `source .venv/bin/activate` |
| Skill script not found | Wrong path | `ls ~/.openclaw/skills/` |
| Webhook returns 404 | OpenClaw not running | Start OpenClaw agent on port 18789 |
| Long output scrolls off screen | Terminal buffer | Pipe to `less`: `script | less` |

**Quick reset if anything breaks:**

```bash
# Kill the API server
kill $(lsof -ti:5000) 2>/dev/null || true

# Restart it
cd ~/dotclaw
source .venv/bin/activate
python mock_ot_api/app.py &> /tmp/ot_api.log &

# Verify
sleep 1 && curl -s -o /dev/null -w "HTTP %{http_code}\n" \
  -H "Authorization: Bearer OT-POC-TOKEN-2026" \
  http://localhost:5000/scada/feeders/FDR-001/live
```

---

## Common Questions and Suggested Answers

**Q: Is this connected to our real SCADA?**
A: This POC uses a simulated API that mirrors your actual SCADA data schema. Integration with
your real SCADA/OMS/MDMS systems requires an integration layer — typically 2–4 weeks of
connector development depending on the vendor and protocol (REST, SOAP, OPC-UA, or database).

**Q: How secure is it? Our OT network is air-gapped.**
A: The agent runs fully on-premise — no cloud dependency. The OT API can be deployed inside
your OT DMZ. OpenClaw communicates over your internal network. The only outbound connection is
to WhatsApp's servers for message delivery, which can be routed through your existing proxy.

**Q: Can operators talk to it in Hindi or regional languages?**
A: Yes. OpenClaw uses an LLM as the reasoning core, which supports multi-lingual input and
output. A lineman can message in Hindi and receive a response in Hindi.

**Q: What if the WhatsApp number changes or someone leaves?**
A: Phone number assignments are managed in the OpenClaw agent config. An admin can update the
delivery target in under a minute — no code change required.

**Q: How does it know which skill to use?**
A: Each SKILL.md file contains a "When to Use" section with natural language triggers. OpenClaw
reads these at startup and uses them to match incoming queries to the right skill. You can add
new skills at any time without restarting the system.

**Q: What's the latency from query to WhatsApp delivery?**
A: Typically 3–8 seconds end-to-end — skill execution + LLM formatting + WhatsApp delivery.
For fault alerts, `wakeMode: now` bypasses any queue and delivers immediately.

**Q: Can it take actions, not just report?**
A: In this POC it is read-only. Write-back actions (e.g., issuing load-shedding commands to
SCADA, updating OMS crew status) can be added as additional skills with appropriate
authorization controls and audit logging.

---

## Post-Demo Next Steps to Propose

1. **Integration scoping call** — identify which OT systems are API-ready vs. require
   an adapter (SOAP/OPC-UA/DB connector).

2. **Pilot zone selection** — pick 1 circle with active AMI deployment and a motivated
   Circle SE to run a 4-week live pilot.

3. **Agent persona design** — define which roles receive which alerts (CMD, SE, lineman,
   revenue protection officer) and what language/format each expects.

4. **Data residency and security review** — confirm network topology, firewall rules,
   and WhatsApp Business API account ownership.

5. **Success metrics agreement** — establish baseline for AT&C loss %, outage MTTR,
   and revenue protection recoveries to measure against at 90 days.

---

## Appendix — All Demo Commands in Sequence

Copy-paste this block to run the full demo without searching through the doc:

```bash
# --- SETUP (run once before demo) ---
cd ~/dotclaw
source .venv/bin/activate
python mock_ot_api/app.py &> /tmp/ot_api.log &
sleep 1

# Health check
curl -s -o /dev/null -w "HTTP %{http_code}\n" \
  -H "Authorization: Bearer OT-POC-TOKEN-2026" \
  http://localhost:5000/scada/feeders/FDR-001/live

# --- SCENARIO 1: SCADA Feeder Health ---
python ~/.openclaw/skills/scada-feeder/scripts/fetch_feeder.py --feeder FDR-002
python ~/.openclaw/skills/scada-feeder/scripts/fetch_feeder.py --feeder FDR-005
python ~/.openclaw/skills/scada-feeder/scripts/fetch_feeder.py --feeder FDR-006

# --- SCENARIO 2: Outage Status ---
python ~/.openclaw/skills/outage-status/scripts/fetch_outages.py
python ~/.openclaw/skills/outage-status/scripts/fetch_outages.py --zone Zone-A

# --- SCENARIO 3: AT&C Analytics ---
python ~/.openclaw/skills/atc-analytics/scripts/run_atc.py
python ~/.openclaw/skills/atc-analytics/scripts/run_atc.py --days 3

# --- SCENARIO 4: AMI Anomalies ---
python ~/.openclaw/skills/ami-meters/scripts/fetch_anomalies.py
python ~/.openclaw/skills/ami-meters/scripts/fetch_anomalies.py --type tamper

# --- SCENARIO 5: Fault Alert Webhook ---
./trigger_fault.sh

# --- SCENARIO 6: Daily AT&C Report ---
./daily_atc_report.sh
```
