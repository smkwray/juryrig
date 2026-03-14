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

The current configuration (`include_all`) includes `Gender`, `Ethnicity`, and `Race` in the
training feature set.

