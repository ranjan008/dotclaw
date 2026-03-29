# Skill: vendor-performance

## Purpose
Retrieve vendor performance scorecards from the Supply Chain system. Shows on-time delivery %, quality score, average delay, and overall rating (A–D).

## When to Use
- "How is VND-0010 performing?"
- "Show vendor scorecards for all vendors"
- "Which vendors are underperforming?"
- "What is the OTD percentage for VND-0011?"

## Usage
```bash
python ~/.openclaw/skills/vendor-performance/scripts/fetch_vendors.py [--vendor V] [--allowed-vendors V1,V2] [--allowed-categories C1,C2]
```

| Argument | Required | Description |
|---|---|---|
| `--vendor` | No | Specific vendor ID (e.g. VND-0010) |
| `--allowed-vendors` | No | RBAC scope whitelist |
| `--allowed-categories` | No | RBAC scope whitelist |

## Example Output
```
============================================================
  VENDOR PERFORMANCE SCORECARD
  Generated : 2026-03-29 08:15:00 UTC
============================================================
  Vendor     : VND-0010 — Reliance Materials Pvt Ltd
  Category   : CAT-RAW
  Orders     : 28 total / 26 on-time
  OTD %      : 92.8%
  Quality    : 4.4 / 5.0
  Avg Delay  : 0.3 days
  Rating     : A  ✅
  Remarks    : Preferred supplier — consistently high performance

  Vendor     : VND-0011 — SunTech Electronics
  OTD %      : 73.3%   Rating: C  ⚠️

  Vendor     : VND-0012 — PackRight Solutions
  OTD %      : 63.6%   Rating: D  🚨  PIP initiated
============================================================
```
