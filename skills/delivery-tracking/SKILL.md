# Skill: delivery-tracking

## Purpose
Track active shipments to plants and warehouses. Shows dispatch date, ETA, delay status, vehicle number, and e-way bill details.

## When to Use
- "Track deliveries to PLANT-DEL"
- "Are there any delayed shipments?"
- "Show me in-transit deliveries for PLANT-NCR"
- "What is the status of shipment SHP-5002?"

## Usage
```bash
python ~/.openclaw/skills/delivery-tracking/scripts/fetch_deliveries.py [--plant P] [--vendor V] [--allowed-plants P1,P2] [--allowed-warehouses W1,W2]
```

| Argument | Required | Description |
|---|---|---|
| `--plant` | No | Filter by destination plant |
| `--vendor` | No | Filter by vendor |
| `--allowed-plants` | No | RBAC scope whitelist |
| `--allowed-warehouses` | No | RBAC scope whitelist |

## Example Output
```
============================================================
  DELIVERY TRACKING REPORT
  Generated : 2026-03-29 08:15:00 UTC   Shipments: 3
============================================================
  [1] SHP-5001  →  PLANT-DEL
      PO       : PO-1001   Vendor : VND-0010
      From     : Mumbai    ETA    : 2026-03-30
      Status   : IN TRANSIT (on schedule)
      Vehicle  : MH-04-AB-1234   E-Way: EWB-220300012345

  [2] SHP-5002  →  PLANT-DEL
      PO       : PO-1002   Vendor : VND-0011
      From     : Chennai   ETA    : 2026-03-28
      Status   : DELAYED (+1 day)  ⚠️
      Vehicle  : TN-09-CD-5678   E-Way: EWB-220300012346
============================================================
  ⚠️  1 delayed shipment(s) require attention.
============================================================
```
