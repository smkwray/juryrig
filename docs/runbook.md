# Runbook

## Setup

```bash
python3.11 -m venv "${HOME}/venvs/juryrig"
scripts/uvsafe sync
scripts/uvsafe python -B -m pytest -q
```

This repo uses an external virtual environment at `${HOME}/venvs/juryrig` by default.
Do not create `.venv/`, `venv/`, caches, or `__pycache__` inside the repo.
Copy `.env.example` to `.env` only if you need to override the default paths.

## Raw data flow

```bash
scripts/uvsafe python -m ny_oca_conviction.cli discover-sources
scripts/uvsafe python -m ny_oca_conviction.cli fetch-oca-stat --years all
scripts/uvsafe python -m ny_oca_conviction.cli register-manual-oca-stat --path data/raw/oca_stat
scripts/uvsafe python -m ny_oca_conviction.cli validate-raw
```

If `discover-sources` or `fetch-oca-stat` hits HTTP 403 from the NY Courts host, use the browser
download path instead of retrying scripted fetches.

## Manual data download

The NY Courts host may return Cloudflare HTTP 403 to scripted requests. When this happens:

1. Download the yearly CSVs and reference PDFs in a normal browser.
2. Place CSVs in `data/raw/oca_stat/`.
3. Run `register-manual-oca-stat`.

## Supplemental pretrial flow

```bash
scripts/uvsafe python -m ny_oca_conviction.cli fetch-supplemental-pretrial
scripts/uvsafe python -m ny_oca_conviction.cli register-manual-supplemental-pretrial --path data/raw/supplemental_pretrial
scripts/uvsafe python -m ny_oca_conviction.cli validate-supplemental-pretrial
scripts/uvsafe python -m ny_oca_conviction.cli summarize-supplemental-pretrial
scripts/uvsafe python -m ny_oca_conviction.cli replicate-supplemental-pretrial
scripts/uvsafe python -m ny_oca_conviction.cli build-supplemental-pretrial-policy-sample
scripts/uvsafe python -m ny_oca_conviction.cli build-supplemental-pretrial-policy-tables
scripts/uvsafe python -m ny_oca_conviction.cli build-supplemental-pretrial-policy-effects
```

This source is kept in a separate data branch from `OCA-STAT`. The public supplemental pretrial
file is a criminal-cycle dataset and should not be merged directly into the defendant-docket
`OCA-STAT` table without a deliberate linkage design.

## Modeling flow

```bash
scripts/uvsafe python -m ny_oca_conviction.cli build-dataset --snapshot-date 2026-03-07
scripts/uvsafe python -m ny_oca_conviction.cli train --config configs/train_baseline.yaml
scripts/uvsafe python -m ny_oca_conviction.cli evaluate --run-id latest
scripts/uvsafe python -m ny_oca_conviction.cli report --run-id latest
scripts/uvsafe python -m ny_oca_conviction.cli build-public-figures
```

## Reference run

- run id: `20260320_231413`
- model table rows: `1,609,252`
- best baseline: `logistic_regression`
- note: run outputs are generated locally under `artifacts/` and are not committed to the repo
