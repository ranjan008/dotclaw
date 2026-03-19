# Skill: scada-feeder

## Purpose

Fetch real-time SCADA telemetry for a specific distribution feeder from the Mock OT API.
Reports current load (MW), voltage (kV), power factor, capacity utilisation, and operational
status. Raises a capacity warning when utilisation exceeds 85%.

---

## When to Use

- "What is the current load on feeder FDR-002?"
- "Check the status of feeder FDR-006 — is it overloaded?"
- "Show me live SCADA data for FDR-004."
- "What is the voltage and power factor on FDR-009 right now?"
- "Is feeder FDR-002 above safe capacity limits?"

---

## Usage

```bash
python ~/.openclaw/skills/scada-feeder/scripts/fetch_feeder.py --feeder <FEEDER_ID>
```

**Arguments**

| Argument    | Required | Description                          |
|-------------|----------|--------------------------------------|
| `--feeder`  | Yes      | Feeder ID (e.g. FDR-002, FDR-006)   |

**Example**

```bash
python ~/.openclaw/skills/scada-feeder/scripts/fetch_feeder.py --feeder FDR-002
```

---

## Example Output

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

  ⚠️  CAPACITY WARNING: Feeder FDR-002 is at 93.5% capacity.
      Immediate load-shedding or feeder augmentation advised.
============================================================
```
