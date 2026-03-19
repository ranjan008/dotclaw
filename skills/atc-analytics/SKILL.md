# Skill: atc-analytics

## Purpose

Pull AT&C (Aggregate Technical and Commercial) loss data from the MDMS API and produce an
executive-style management summary. Highlights week-over-week trend, highlights the top 3
loss-contributing feeders, and flags whether AT&C performance is improving or deteriorating.

---

## When to Use

- "What are our AT&C losses for the past week?"
- "Show me the distribution loss trend for the last 7 days."
- "Which feeders are driving the highest commercial losses?"
- "Generate a daily AT&C management report."
- "Has AT&C loss improved week over week?"

---

## Usage

```bash
python ~/.openclaw/skills/atc-analytics/scripts/run_atc.py [--days <N>]
```

**Arguments**

| Argument  | Required | Default | Description                     |
|-----------|----------|---------|---------------------------------|
| `--days`  | No       | 7       | Number of days of data to fetch |

**Examples**

```bash
# Default 7-day report
python ~/.openclaw/skills/atc-analytics/scripts/run_atc.py

# 3-day report
python ~/.openclaw/skills/atc-analytics/scripts/run_atc.py --days 3
```

---

## Example Output

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
  Week-over-Week    : -0.5 pp  [IMPROVING]

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
