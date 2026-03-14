import pandas as pd

from ny_oca_conviction.dataset.maturity import (
    DISPOSED_SHARE_COLUMN,
    MATURE_FLAG_COLUMN,
    add_maturity_flags,
)


def test_maturity_is_computed_per_cohort():
    frame = pd.DataFrame(
        {
            "Arraign Year": ["2024", "2024", "2024"],
            "Arraign Month": ["1", "1", "2"],
            "Docket Status": ["Disposed", "Disposed", "Pending"],
        }
    )
    matured = add_maturity_flags(frame, threshold=0.9)
    january = matured[matured["Arraign Month"] == 1]
    february = matured[matured["Arraign Month"] == 2]
    assert january[MATURE_FLAG_COLUMN].all()
    assert float(january[DISPOSED_SHARE_COLUMN].iloc[0]) == 1.0
    assert not february[MATURE_FLAG_COLUMN].iloc[0]
