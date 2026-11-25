# Runbook

## Setup

```bash
uv sync
uv run pytest -q
```

## Raw data flow

```bash
uv run ny-oca-conviction discover-sources
uv run ny-oca-conviction fetch-oca-stat --years all
uv run ny-oca-conviction register-manual-oca-stat --path data/raw/oca_stat
uv run ny-oca-conviction validate-raw
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
uv run ny-oca-conviction fetch-supplemental-pretrial
uv run ny-oca-conviction register-manual-supplemental-pretrial --path data/raw/supplemental_pretrial
uv run ny-oca-conviction validate-supplemental-pretrial
uv run ny-oca-conviction summarize-supplemental-pretrial
uv run ny-oca-conviction replicate-supplemental-pretrial
uv run ny-oca-conviction build-supplemental-pretrial-policy-sample
uv run ny-oca-conviction build-supplemental-pretrial-policy-tables
uv run ny-oca-conviction build-supplemental-pretrial-policy-effects
```

This source is kept in a separate data branch from `OCA-STAT`. The public supplemental pretrial
file is a criminal-cycle dataset and should not be merged directly into the defendant-docket
`OCA-STAT` table without a deliberate linkage design.

## Modeling flow

```bash
uv run ny-oca-conviction build-dataset --snapshot-date 2026-03-07
uv run ny-oca-conviction train --config configs/train_baseline.yaml
uv run ny-oca-conviction evaluate --run-id latest
uv run ny-oca-conviction report --run-id latest
uv run ny-oca-conviction build-public-figures
```

## Reference run

- run id: `20260320_231413`
- model table rows: `1,609,252`
- best baseline: `logistic_regression`
- note: run outputs are generated locally under `artifacts/` and are not committed to the repo
