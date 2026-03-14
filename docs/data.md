# Data Notes

- Dataset: New York OCA-STAT Act extract
- Row grain: one unique, de-identified defendant-docket
- Refresh cadence: monthly
- Acquisition policy: programmatic discovery/download first, manual browser download second
- Provenance file: `data/raw/oca_stat/manifest.json`

## Supplemental pretrial track

- Dataset: DCJS/OCA Supplemental Pretrial Release Data File
- Row grain: one criminal cycle, which may span multiple offenses or dockets
- Current public release in scope: October 2025 bundle covering arraignments from `2019` through `2024`
- Primary landing directory: `data/raw/supplemental_pretrial/`
- Provenance file: `data/raw/supplemental_pretrial/manifest.json`
- First-pass commands:
  - `scripts/uvsafe python -m ny_oca_conviction.cli fetch-supplemental-pretrial`
  - `scripts/uvsafe python -m ny_oca_conviction.cli register-manual-supplemental-pretrial --path data/raw/supplemental_pretrial`
  - `scripts/uvsafe python -m ny_oca_conviction.cli validate-supplemental-pretrial`
  - `scripts/uvsafe python -m ny_oca_conviction.cli summarize-supplemental-pretrial`

Raw CSVs and processed parquet outputs are intentionally ignored by git.
