import pandas as pd

from ny_oca_conviction.dataset.labels import LABEL_COLUMN, LABEL_STATUS_COLUMN, add_label_columns


def test_label_mapping_assigns_positive_and_negative_values():
    frame = pd.DataFrame({"Disposition Type": ["Plea", "Dismissed", "Pending"]})
    labeled = add_label_columns(frame)
    assert labeled[LABEL_COLUMN].iloc[0] == 1
    assert labeled[LABEL_COLUMN].iloc[1] == 0
    assert pd.isna(labeled[LABEL_COLUMN].iloc[2])
    assert labeled[LABEL_STATUS_COLUMN].tolist() == ["modeled", "modeled", "excluded"]
