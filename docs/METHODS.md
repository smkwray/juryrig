# Methods

Every model, algorithm, library, and configuration used in the juryrig project.

---

## 1. Models

All predictive models are scikit-learn classifiers.

### 1.1 HistGradientBoostingClassifier (primary)

Histogram-based gradient boosting from scikit-learn. Uses default scikit-learn hyperparameters (no custom tuning). Post-hoc sigmoid calibration is applied via `CalibratedClassifierCV`.

| Setting | Value |
|---|---|
| Hyperparameters | scikit-learn defaults |
| Calibration | sigmoid (Platt scaling) via `CalibratedClassifierCV`, cv=3 |
| Preprocessing | `OrdinalEncoder` for categorical features, `SimpleImputer` for missing values |
| Random state | 7 |

### 1.2 LogisticRegression (baseline)

Linear classifier from scikit-learn.

| Setting | Value |
|---|---|
| solver | `saga` |
| max_iter | 2000 |
| tol | 1e-3 |
| C | 1.0 (default) |
| Preprocessing | `MaxAbsScaler` + `OneHotEncoder` for categorical features, `SimpleImputer` (median for numeric, most_frequent for categorical) |
| Random state | 7 |

### 1.3 DummyClassifier (floor baseline)

Scikit-learn's `DummyClassifier` with `strategy="prior"` — predicts the training-set class distribution for every sample. Establishes a performance floor.

### 1.4 Race-association regression models

Separate logistic regressions are used for adjusted race-association analysis (not for prediction):

| Specification | Controls | Hyperparameters |
|---|---|---|
| Core-adjusted | County, charge severity, arrest type, age, gender, ethnicity | `LogisticRegression(max_iter=300, C=1.0, solver="saga", random_state=7)` |
| Charge-detail-adjusted | Core controls + extended charge-detail features | Same hyperparameters |

Both use `OneHotEncoder(drop="first")` for categorical encoding. Implementation: `src/ny_oca_conviction/evaluation/race_association.py`.

---

## 2. Calibration

Calibration is applied to the HistGradientBoostingClassifier only.

| Setting | Value |
|---|---|
| Method | `sigmoid` (Platt scaling) |
| Cross-validation folds | 3 |
| Implementation | scikit-learn `CalibratedClassifierCV` |
| Configuration | `configs/train_baseline.yaml` → `calibration.enabled: true`, `calibration.method: sigmoid` |

Calibration evaluation uses 10 quantile-based bins (`pd.qcut`) to compute bin-wise average predictions vs. average outcomes.

Implementation: `src/ny_oca_conviction/models/calibrate.py`, `src/ny_oca_conviction/evaluation/calibration.py`.

---

## 3. Evaluation Metrics

| Metric | Role | Definition |
|---|---|---|
| **Accuracy** | Primary classification | Share of cases classified correctly |
| **AUROC** | Ranking quality | Area under the ROC curve |
| **PR-AUC** | Positive-class ranking | Area under the precision-recall curve |
| **Brier score** | Calibration quality | Mean squared error of predicted probabilities (lower is better) |

Model selection uses Brier score on the evaluation split. Subgroup metrics are computed by Race, Ethnicity, Gender, age_bucket, and Region. Per-run results are recorded in [`model-card.md`](model-card.md).

---

## 4. Feature Policy

See [`modeling.md`](modeling.md) for the full target definition, leakage-exclusion list, and feature-inclusion configuration.

Summary: 19 features from OCA-STAT arraignment-time fields. The default configuration (`include_all`) includes Gender, Ethnicity, and Race. Data sources and provenance: [`data.md`](data.md).

---

## 5. Libraries

| Library | Purpose |
|---|---|
| scikit-learn | All classifiers, calibration, preprocessing, metrics |
| pandas | Data manipulation and feature engineering |
| numpy | Numerical operations |
| pyarrow / parquet | Data storage format |

Python 3.10+. Dependencies managed via `uv` (`scripts/uvsafe`).
