# Skill: po-status

## Purpose
Fetch the status of a Purchase Order from the Supply Chain system.
Reports vendor, plant, category, order value, current status, expected vs actual delivery, and delay flags.

## When to Use
- "What is the status of PO-1002?"
- "Is PO-1004 delayed?"
- "Show me details for purchase order PO-1001"
- "Which POs are delayed at PLANT-DEL?"

## Usage
```bash
python ~/.openclaw/skills/po-status/scripts/fetch_po.py --po <PO_ID> [--allowed-plants P1,P2] [--allowed-vendors V1,V2]
```

| Argument | Required | Description |
|---|---|---|
| `--po` | Yes | PO number (e.g. PO-1002) |
| `--allowed-plants` | No | RBAC scope — comma-separated plant whitelist |
| `--allowed-vendors` | No | RBAC scope — comma-separated vendor whitelist |

## Example Output
```
============================================================
  PO STATUS — PO-1002
  Retrieved : 2026-03-29T08:15:00Z
============================================================
  Vendor     : VND-0011 — SunTech Electronics
  Plant      : PLANT-DEL
  Category   : CAT-ELEC
  Items      : 3
  Value      : ₹8.70 Lakh
  Status     : DELAYED  ⚠️
  Ordered    : 2026-03-15
  Expected   : 2026-03-28
  Delay      : +1 day
  Remarks    : Delayed — customs clearance at Chennai port
============================================================
```
