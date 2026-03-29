# Skill: transaction-report

## Purpose
Retrieve daily transaction volume summary by branch. Shows credit/debit counts, total volume, and channel-wise split (UPI, NEFT/RTGS, Cash).

## When to Use
- "Show transaction report for BR-MUM-001"
- "What was the transaction volume at Mumbai Main last 7 days?"
- "How many UPI transactions at BR-PUN-001?"
- "Give me a 3-day transaction summary for all branches"

## Usage
```bash
python ~/.openclaw/skills/transaction-report/scripts/fetch_transactions.py [--branch B] [--days N] [--allowed-branches B1,B2]
```

## Example Output
```
============================================================
  TRANSACTION REPORT — BR-MUM-001 (last 7 days)
============================================================
  Date         Credits  Debits  Volume(Cr)  UPI   NEFT  Cash
  2026-03-23   1,240      980      48.2     521   223   496
  2026-03-24   1,380    1,120      52.4     580   248   552
  ...
  Total        9,350    7,530     355.0
============================================================
```
