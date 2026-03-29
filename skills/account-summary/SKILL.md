# Skill: account-summary

## Purpose
Retrieve branch-level CASA, FD, and loan account summaries from the core banking system. Shows account counts, balances, NPA %, and CASA ratio.

## When to Use
- "Show account summary for BR-MUM-001"
- "What is the CASA balance at our Mumbai branch?"
- "What is the NPA percentage for BR-PUN-001?"
- "Give me an overview of all branches"

## Usage
```bash
python ~/.openclaw/skills/account-summary/scripts/fetch_accounts.py [--branch B] [--allowed-branches B1,B2]
```

## Example Output
```
============================================================
  ACCOUNT SUMMARY — BR-MUM-001 (Mumbai Main)
  Generated : 2026-03-29 08:15:00 UTC
============================================================
  CASA Accounts  : 4,820   Balance : ₹284.6 Cr
  FD Accounts    : 1,240   Balance : ₹892.3 Cr
  Loan Accounts  :   680   O/S     : ₹1,124.7 Cr
  NPA Accounts   :    18   Amount  : ₹22.4 Cr  (1.99%)
  CASA Ratio     : 38.7%
============================================================
```
