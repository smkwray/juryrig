# Model Card

## Run identity

- snapshot date: `2026-03-07`
- run id: `20260307_224037`
- raw input manifest: `data/raw/oca_stat/manifest.json`
- dataset summary: `data/processed/model_table_summary.json`

## Task

Research-only binary forecast of conviction likelihood using OCA-STAT arraignment-time fields for
New York criminal cases.

## Data and cohort policy

- raw years landed: `2021` through `2026`
- maturity threshold: `>= 90%` disposed share by arraignment year-month cohort
- modeled rows: `1,609,252`
- label policy:
  - positive: `Plea`, `Verdict-TFG`
  - negative: `Dismissed`, `Dism-ACD`, `Verdict-ACQ`
  - excluded: pending, warrant, transfer, other, unknown states

## Feature policy

Default feature set excludes leakage-prone outcome fields. The current configuration
(`include_all`) includes `Gender`, `Ethnicity`, and `Race` in the training feature set.
Feature count: 19.

## Baseline metrics

| Model | AUROC | PR-AUC | Brier |
|---|---:|---:|---:|
| dummy | 0.5000 | 0.4316 | 0.2461 |
| logistic_regression | 0.8465 | 0.8148 | 0.1569 |
| hist_gradient_boosting | 0.8644 | 0.8302 | 0.1496 |

## Audit notes

- Subgroup and county outputs are under `artifacts/runs/20260307_224037/`.
- Error and calibration quality vary materially across counties and demographic subgroups.

## Intended use

System-pattern research, benchmarking, and methodological evaluation.

## Non-use

Do not use this output for charging, plea bargaining, release, sentencing, supervision, or any
individual legal decision.
