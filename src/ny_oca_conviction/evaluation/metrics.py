from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)


def binary_metrics(y_true, y_prob) -> dict[str, Any]:
    y_true = np.asarray(y_true, dtype=float)
    y_prob = np.asarray(y_prob, dtype=float)
    y_pred = (y_prob >= 0.5).astype(int)
    unique = np.unique(y_true)
    auroc = roc_auc_score(y_true, y_prob) if len(unique) > 1 else None
    pr_auc = average_precision_score(y_true, y_prob) if len(unique) > 1 else None
    return {
        "row_count": int(len(y_true)),
        "positive_rate": float(y_true.mean()) if len(y_true) else 0.0,
        "accuracy": float(accuracy_score(y_true, y_pred)) if len(y_true) else 0.0,
        "brier_score": float(brier_score_loss(y_true, y_prob)) if len(y_true) else 0.0,
        "log_loss": float(log_loss(y_true, y_prob, labels=[0, 1])) if len(y_true) else 0.0,
        "auroc": None if auroc is None else float(auroc),
        "pr_auc": None if pr_auc is None else float(pr_auc),
    }
