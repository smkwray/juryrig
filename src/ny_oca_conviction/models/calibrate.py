from __future__ import annotations

from sklearn.calibration import CalibratedClassifierCV


def maybe_calibrate(estimator, enabled: bool, method: str):
    if not enabled:
        return estimator
    return CalibratedClassifierCV(estimator=estimator, method=method, cv=3)
