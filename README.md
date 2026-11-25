# juryrig

**[Browse the interactive results site](https://smkwray.github.io/juryrig/)**

`juryrig` analyzes public New York criminal-court records in two separate branches. The predictive branch models whether a case ends in conviction, using 1.61 million arraignment records (2021–2025) from the OCA-STAT data published by the New York Office of Court Administration (OCA). The pretrial branch compares release rates before and after New York's May 2022 and June 2023 bail-law amendments, using 853,976 cases (2021–2024) from the supplemental pretrial release file published by the Division of Criminal Justice Services (DCJS) and OCA.

Using only arraignment-time case fields, with race, ethnicity, and gender excluded from training, logistic regression reaches 0.864 AUROC and 78.2% accuracy on 271,701 held-out cases. Firearm charges that became newly eligible for detention in May 2022 saw release rates fall 20–32 percentage points more than other cases, though that group has only 186 cases. Both branches describe patterns in public records; neither is a causal estimate or a tool for deciding real cases.

## Headline findings

Predictive branch, held-out test set (AUROC is the area under the ROC curve, a measure of ranking quality; Brier is calibration error, lower is better):

| Model | Accuracy | AUROC | Brier |
|---|---:|---:|---:|
| Logistic regression (selected) | 0.7818 | 0.8643 | 0.1474 |
| Histogram gradient boosting | 0.7847 | 0.8639 | 0.1499 |
| Majority-class baseline | 0.5684 | 0.5000 | 0.2461 |

- Geography is the largest raw split: 23.4% of NYC cases end in conviction, against 69.3% outside NYC. Felonies are convicted at 65.8% and violations at 25.2%.
- Model ranking quality varies by race (AUROC 0.77 for Asian, 0.83 for Black, and 0.86 for White defendants) while calibration stays similar (Brier 0.145–0.150). Training with race, ethnicity, and gender included barely changes performance (AUROC 0.8653).
- After adjusting for county, charge, arrest type, age, gender, and other case fields, Black defendants are about 2.6–2.8 percentage points less likely than comparable White defendants to be convicted, and Asian defendants about 5–7 points less likely. Three different adjustment methods agree on the direction.

Pretrial branch, change in release rate relative to all other cases over 12 months before and after each amendment:

| Amendment | Proxy group | NYC | Outside NYC |
|---|---|---:|---:|
| May 2022 | New qualifying firearm charge (186 cases) | −20.2 pp | −32.0 pp |
| May 2022 | Repeat harm or theft (about 164,000 cases) | −3.7 pp | −3.7 pp |
| May 2022 | Second firearm offense (about 1,300 cases) | −1.3 pp | −7.9 pp |
| June 2023 | Repeat offender (about 164,000 cases) | −0.2 pp | −2.5 pp |

The site has the full subgroup, county, and figure detail.

## Documentation

- [Methods](docs/METHODS.md): models, preprocessing, and feature policy
- [Race-adjusted association](docs/race-adjusted-association.md): how the adjusted race gaps are estimated and what they mean
- [Reader FAQ](https://smkwray.github.io/juryrig/faq.html) on the results site
- [Runbook](docs/runbook.md): data download and the full command sequence

## Method

The predictive branch labels pleas and guilty verdicts as convictions and dismissals and acquittals as non-convictions, excluding pending and transferred cases. Fields recorded after arraignment (disposition, sentence, fines) are never used. It compares a majority-class baseline, logistic regression, and calibrated gradient boosting, and selects the model with the best validation Brier score. Race, ethnicity, and gender are kept for subgroup audits. The pretrial branch builds proxy groups for the charges each amendment targeted from public charge and case-history fields and compares their before-and-after release rates with all other cases, separately for NYC and the rest of the state.

## Data sources

| Source | Unit | Coverage |
|---|---|---|
| [OCA-STAT](https://ww2.nycourts.gov/oca-stat-act-31371) | De-identified defendant-docket | 2021–2025 cohorts |
| [DCJS/OCA Supplemental Pretrial Release Data File](https://www.criminaljustice.ny.gov/crimnet/ojsa/stats.htm) | Criminal cycle | January 2021 – December 2024 |

No row-level data are committed. The NY Courts site sometimes refuses scripted downloads (HTTP 403); the runbook explains the browser download path.

## Quickstart

Requires [uv](https://docs.astral.sh/uv/) and Python 3.11 or 3.12.

```bash
uv sync
uv run pytest -q
uv run ny-oca-conviction fetch-oca-stat --years all
uv run ny-oca-conviction validate-raw
uv run ny-oca-conviction build-dataset --snapshot-date YYYY-MM-DD
uv run ny-oca-conviction train --config configs/train_baseline.yaml
uv run ny-oca-conviction evaluate --run-id latest
uv run ny-oca-conviction report --run-id latest
```

Run outputs go to `artifacts/`, which is not committed. The pretrial branch has its own commands, listed in the [runbook](docs/runbook.md).

## Layout

| Directory | Contents |
|---|---|
| `src/ny_oca_conviction/` | Python package and `ny-oca-conviction` command-line tool |
| `configs/` | Dataset, training, and audit settings |
| `docs/` | Results site, figures, model card, and documentation |
| `scripts/` | Standalone entry points |
| `tests/` | Test suite |

## Limitations

- The predictive branch uses only OCA-STAT arraignment-time fields, with no post-arraignment or outside data.
- It reports associations in public records and does not explain why the patterns exist.
- Calibration varies across counties and demographic groups.
- The pretrial groups are proxies built from public fields and do not exactly match legal eligibility.
- The pretrial comparison is before-and-after, so it cannot separate the amendments from other changes in the courts at the same time.
- New York State only. For research use, not validated for any legal or operational decision.

## License

MIT. See [LICENSE](LICENSE).
