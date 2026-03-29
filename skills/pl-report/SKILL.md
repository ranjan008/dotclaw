# Skill: pl-report

## Purpose
Retrieve branch-level P&L summary including revenue, expenses, NIM, PAT, and ROA for the last N days.

## When to Use
- "Show P&L for BR-MUM-001"
- "What is the profit for Mumbai Main this week?"
- "Give me NIM and ROA for all branches"
- "Revenue trend for BR-PUN-001 last 7 days"

## Usage
```bash
python ~/.openclaw/skills/pl-report/scripts/fetch_pl.py [--branch B] [--days N] [--allowed-branches B1,B2] [--allowed-cost-centers C1,C2]
```

## Example Output
```
============================================================
  P&L REPORT — BR-MUM-001 (last 7 days)
============================================================
  Date         Revenue  Expenses   NIM    PAT    ROA%
  2026-03-23     18.4      11.2    4.8    2.4    1.09%
  ...
  ─────────────────────────────────────────────────
  Avg / Day      19.3      11.8    5.0    2.6    1.14%
  7-Day Total   134.8      82.4   35.1   17.8
============================================================
```
