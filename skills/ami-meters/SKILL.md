# Skill: ami-meters

## Purpose

Query the MDMS/AMI system for smart meter anomalies and produce a structured DT-cluster-grouped
report. Identifies tamper events, zero-read meters, and communication failures, then recommends
an appropriate field action for each anomaly category.

---

## When to Use

- "Show me all meter anomalies from the AMI system."
- "How many meters have tamper events in the field?"
- "Which DT clusters have the most communication failures?"
- "List zero-read meters grouped by distribution transformer."
- "Generate an AMI anomaly report — filter by tamper only."

---

## Usage

```bash
python ~/.openclaw/skills/ami-meters/scripts/fetch_anomalies.py [--type <anomaly_type>]
```

**Arguments**

| Argument  | Required | Description                                              |
|-----------|----------|----------------------------------------------------------|
| `--type`  | No       | Filter by anomaly type: `tamper`, `zero_read`, `comm_failure` |

**Examples**

```bash
# All anomalies
python ~/.openclaw/skills/ami-meters/scripts/fetch_anomalies.py

# Tamper events only
python ~/.openclaw/skills/ami-meters/scripts/fetch_anomalies.py --type tamper

# Communication failures
python ~/.openclaw/skills/ami-meters/scripts/fetch_anomalies.py --type comm_failure
```

---

## Example Output

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

  Recommended Action: Dispatch field team to DT-001 for
  physical meter inspection and anti-tamper audit.

  DT CLUSTER: DT-002  (5 anomalies)
  ...

  DT CLUSTER: DT-003  (4 anomalies)
  ...

============================================================
  SUMMARY BY ANOMALY TYPE
  ──────────────────────────────────────────────────────
  TAMPER       : 5 meters
  ZERO_READ    : 4 meters
  COMM_FAILURE : 5 meters
============================================================
```
