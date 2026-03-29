# Skill: compliance-report

## Purpose
Retrieve open compliance flags for a branch — KYC expiry, suspicious transactions (AML), CTR pending, and other regulatory items.

## When to Use
- "Are there any compliance issues at BR-MUM-001?"
- "Show high severity KYC flags"
- "Any AML alerts at Mumbai branches?"
- "What compliance items are due today?"

## Usage
```bash
python ~/.openclaw/skills/compliance-report/scripts/fetch_compliance.py [--branch B] [--severity high|medium|low] [--allowed-branches B1,B2]
```

## Example Output
```
============================================================
  COMPLIANCE FLAGS — BR-MUM-001
  Generated : 2026-03-29 08:15:00 UTC   Total: 4
============================================================
  🚨 HIGH    KYC-001  KYC_EXPIRY     ACC-884421  Due: 2026-04-01
             KYC due in 3 days
  🚨 HIGH    AML-001  SUSPICIOUS_TXN ACC-991234  Due: 2026-03-29
             3 cash deposits >2L in 7 days
  ⚠️  MEDIUM  REG-001  CTR_PENDING    ACC-556677  Due: 2026-03-30
             CTR filing due tomorrow
============================================================
  ⚠️  2 HIGH severity items require immediate action.
============================================================
```
