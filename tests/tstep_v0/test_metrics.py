import pytest

from tstep_v0.metrics import (
    corruption_sensitivity,
    event_recall_at_budget,
    risk_coverage_auc,
)


def test_event_recall_at_budget_counts_temporal_overlap():
    selected = [(0.0, 1.0), (5.0, 6.0)]
    gold = [(0.2, 0.8), (2.0, 3.0), (5.2, 5.7)]

    assert event_recall_at_budget(selected, gold, iou_threshold=0.1) == 2 / 3
    assert event_recall_at_budget(selected[:1], gold, budget=1, iou_threshold=0.1) == 1 / 3


def test_corruption_sensitivity_measures_accuracy_drop_against_gold():
    clean = ["sink", "open", "left"]
    corrupted = ["table", "open", "right"]
    gold = ["sink", "open", "left"]

    assert corruption_sensitivity(clean, corrupted, gold) == pytest.approx(2 / 3)


def test_risk_coverage_auc_rewards_correct_high_confidence_predictions():
    well_ranked = risk_coverage_auc([0.9, 0.8, 0.1], [True, False, False])
    badly_ranked = risk_coverage_auc([0.9, 0.8, 0.1], [False, False, True])

    assert well_ranked == pytest.approx((0.0 + 0.5 + 2 / 3) / 3)
    assert well_ranked < badly_ranked


def test_risk_coverage_auc_handles_empty_inputs_and_rejects_length_mismatch():
    assert risk_coverage_auc([], []) == 0.0
    with pytest.raises(ValueError):
        risk_coverage_auc([0.5], [])
