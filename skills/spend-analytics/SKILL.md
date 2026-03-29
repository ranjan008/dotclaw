# Skill: spend-analytics

## Purpose
Pull procurement spend analytics from the Supply Chain system. Shows budget vs actual spend by plant and category, variance, and savings/overrun flags.

## When to Use
- "What is our spend vs budget for PLANT-DEL?"
- "Show procurement spend by category"
- "Which categories are over budget?"
- "Give me a spend summary for PLANT-NCR"

## Usage
```bash
python ~/.openclaw/skills/spend-analytics/scripts/fetch_spend.py [--plant P] [--category C] [--allowed-plants P1,P2] [--allowed-categories C1,C2]
```

| Argument | Required | Description |
|---|---|---|
| `--plant` | No | Filter by plant |
| `--category` | No | Filter by procurement category |
| `--allowed-plants` | No | RBAC scope whitelist |
| `--allowed-categories` | No | RBAC scope whitelist |

## Example Output
```
============================================================
  PROCUREMENT SPEND ANALYTICS
  Generated : 2026-03-29 08:15:00 UTC
============================================================
  Plant        Category   Budget(L)  Actual(L)  Variance   POs
  PLANT-DEL    CAT-RAW      150.0      138.4    +11.6 ✅    12
  PLANT-DEL    CAT-ELEC      80.0       91.2    -11.2 🚨     7
  PLANT-DEL    CAT-PKG       40.0       38.7     +1.3 ✅     5
  PLANT-NCR    CAT-RAW      120.0      112.9     +7.1 ✅     9
  PLANT-NCR    CAT-ELEC      60.0       58.3     +1.7 ✅     4

  Total Budget : ₹450.0 Lakh
  Total Actual : ₹439.5 Lakh
  Net Savings  : ₹10.5 Lakh  ✅

  ⚠️  CAT-ELEC at PLANT-DEL is ₹11.2L over budget.
============================================================
```
