# Skill: branch-performance

## Purpose
Retrieve branch performance dashboard — targets vs actual for CASA, loans, NPA, fee income, and new account acquisition.

## When to Use
- "How is BR-MUM-001 performing against targets?"
- "Show branch scorecard for Pune CBD"
- "Which branches are behind on CASA targets?"
- "Give me an overall branch performance summary"

## Usage
```bash
python ~/.openclaw/skills/branch-performance/scripts/fetch_branch_perf.py [--branch B] [--allowed-branches B1,B2]
```

## Example Output
```
============================================================
  BRANCH PERFORMANCE — BR-MUM-001 (Mumbai Main)
============================================================
  Metric              Target     Actual    Achievement
  CASA Balance (Cr)    300.0      284.6       94.9%  ⚠️
  Loan O/S (Cr)      1,200.0    1,124.7       93.7%  ⚠️
  NPA %                 2.00%      1.99%       ✅ Within limit
  Fee Income (Cr)       22.0       19.4       88.2%  ⚠️
  New Accounts           250        218       87.2%  ⚠️
============================================================
  Overall: 3 of 5 metrics below 95% target.
============================================================
```
