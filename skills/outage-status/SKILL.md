# Skill: outage-status

## Purpose

Retrieve and display active power outage incidents from the OMS (Outage Management System).
Summarises each outage by zone, affected feeder, duration, consumers impacted, crew deployment
status, and outage type (planned / unplanned). Optionally filters by zone.

---

## When to Use

- "What outages are currently active?"
- "Are there any unplanned outages in Zone-A?"
- "How many consumers are affected by the current outages?"
- "What is the crew status for the ongoing fault on FDR-004?"
- "Give me an OMS summary for Zone-B."

---

## Usage

```bash
python ~/.openclaw/skills/outage-status/scripts/fetch_outages.py [--zone <ZONE>]
```

**Arguments**

| Argument  | Required | Description                               |
|-----------|----------|-------------------------------------------|
| `--zone`  | No       | Filter by zone name (e.g. Zone-A, Zone-B) |

**Examples**

```bash
# All active outages
python ~/.openclaw/skills/outage-status/scripts/fetch_outages.py

# Filtered by zone
python ~/.openclaw/skills/outage-status/scripts/fetch_outages.py --zone Zone-A
```

---

## Example Output

```
============================================================
  OMS — ACTIVE OUTAGE REPORT
  Generated : 2026-03-19 08:34:15
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
