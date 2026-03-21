# Model Card

## Run identity

- snapshot date: `2026-03-07`
- run id: `20260320_231413`
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
(`audit_only`) excludes `Gender`, `Ethnicity`, and `Race` from training but retains them
for subgroup auditing. Feature count: 16.

An `include_all` comparison (19 features) showed no meaningful performance difference
(AUROC 0.8643 vs 0.8653), supporting the `audit_only` default.

## Model selection

Best model is selected by Brier score on the validation split. Test metrics are reported
separately and are not used for selection.

## Baseline metrics

| Model | AUROC | PR-AUC | Brier |
|---|---:|---:|---:|
| dummy | 0.5000 | 0.4316 | 0.2461 |
| **logistic_regression** | **0.8643** | **0.8364** | **0.1474** |
| hist_gradient_boosting | 0.8639 | 0.8314 | 0.1499 |

## Audit notes

- Subgroup and county outputs are under `artifacts/runs/20260320_231413/`.
- Error and calibration quality vary materially across counties and demographic subgroups.

## Intended use

System-pattern research, benchmarking, and methodological evaluation.

## Non-use

Do not use this output for charging, plea bargaining, release, sentencing, supervision, or any
individual legal decision.
