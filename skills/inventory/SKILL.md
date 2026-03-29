# Skill: inventory

## Purpose
Query stock levels across plants and warehouses from the Supply Chain inventory system.
Highlights critical and low-stock items, and shows reorder thresholds.

## When to Use
- "What is the stock level at PLANT-DEL?"
- "Show inventory for WH-DEL-01"
- "Are there any critical stock items at PLANT-NCR?"
- "Which SKUs are below reorder level?"

## Usage
```bash
python ~/.openclaw/skills/inventory/scripts/fetch_inventory.py [--plant P] [--warehouse W] [--allowed-plants P1,P2] [--allowed-warehouses W1,W2]
```

| Argument | Required | Description |
|---|---|---|
| `--plant` | No | Filter by plant (e.g. PLANT-DEL) |
| `--warehouse` | No | Filter by warehouse (e.g. WH-DEL-01) |
| `--allowed-plants` | No | RBAC scope whitelist |
| `--allowed-warehouses` | No | RBAC scope whitelist |

## Example Output
```
============================================================
  INVENTORY REPORT — PLANT-DEL
  Generated : 2026-03-29 08:15:00 UTC
============================================================
  SKU          Description          WH          On Hand   Unit  Status
  SKU-MAT-001  Steel Rods 6mm       WH-DEL-01   2400      kg    OK
  SKU-MAT-002  Copper Wire 2.5mm    WH-DEL-01    180      m     LOW ⚠️
  SKU-ELE-001  Circuit Breaker 32A  WH-DEL-02     45      pcs   CRITICAL 🚨
  SKU-PKG-001  Corrugated Box L     WH-DEL-02   8200      pcs   OK

  ⚠️  2 item(s) require attention: 1 CRITICAL, 1 LOW
============================================================
```
