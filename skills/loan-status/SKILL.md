# Skill: loan-status

## Purpose
Retrieve loan book status by branch and product. Shows outstanding amounts, NPA values and %, and average EMI delay per product line.

## When to Use
- "What is the loan book for BR-MUM-001?"
- "Show NPA status for home loans at BR-PUN-001"
- "Which product has the highest NPA at Mumbai West?"
- "Give me loan summary across all branches"

## Usage
```bash
python ~/.openclaw/skills/loan-status/scripts/fetch_loans.py [--branch B] [--product P] [--allowed-branches B1,B2] [--allowed-products P1,P2]
```

## Example Output
```
============================================================
  LOAN BOOK STATUS — BR-MUM-001
============================================================
  Product       Accounts  O/S (Cr)  NPA (Cr)  NPA%   Avg EMI Delay
  Home Loan          280    548.2      8.4     1.53%     1.2 days
  Personal Loan      240    384.1      9.8     2.55%  ⚠️ 3.1 days
  SME/Business       160    192.4      4.2     2.18%     2.4 days
  ─────────────────────────────────────────────────────
  TOTAL              680  1,124.7     22.4     1.99%
============================================================
```
