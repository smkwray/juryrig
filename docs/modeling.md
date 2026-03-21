# Modeling Notes

## Target

Binary conviction label:

- positive: `Plea`, `Verdict-TFG`
- negative: `Dismissed`, `Dism-ACD`, `Verdict-ACQ`
- excluded: pending, warrant, transfer, other, unknown

## Leakage policy

Default training features exclude:

- `Docket Status`
- `Disposition Type`
- `Disposition Detail`
- `Dismissal Reason`
- `Most Severe Sentence`
- `Fines Imposed`
- `Fees Imposed`
- `Surcharges Imposed`

The current configuration (`audit_only`) excludes `Gender`, `Ethnicity`, and `Race` from
training but retains them for subgroup auditing. Use `include_all` to opt in explicitly.

