"""Lightweight metrics for Phase 0/1 T-STEP-v0 smoke tests."""

from __future__ import annotations

import math
from typing import Any, Iterable, Optional, Sequence, Tuple


Span = Tuple[float, float]


def temporal_iou(a: Span, b: Span) -> float:
    start = max(a[0], b[0])
    end = min(a[1], b[1])
    intersection = max(0.0, end - start)
    union = max(a[1], b[1]) - min(a[0], b[0])
    return 0.0 if union <= 0 else intersection / union


def event_recall_at_budget(
    selected_spans: Sequence[Span],
    gold_spans: Sequence[Span],
    *,
    budget: Optional[int] = None,
    iou_threshold: float = 0.1,
) -> float:
    if not gold_spans:
        return 1.0
    selected = list(selected_spans[:budget])
    matched = 0
    for gold in gold_spans:
        if any(temporal_iou(selected_span, gold) >= iou_threshold for selected_span in selected):
            matched += 1
    return matched / len(gold_spans)


def ledger_query_accuracy(predictions: Sequence[Any], targets: Sequence[Any]) -> float:
    if len(predictions) != len(targets):
        raise ValueError("predictions and targets must have the same length")
    if not targets:
        return 1.0
    return sum(pred == target for pred, target in zip(predictions, targets)) / len(targets)


def corruption_sensitivity(
    clean_predictions: Sequence[Any],
    corrupted_predictions: Sequence[Any],
    gold: Optional[Sequence[Any]] = None,
) -> float:
    if len(clean_predictions) != len(corrupted_predictions):
        raise ValueError("clean and corrupted predictions must have the same length")
    if not clean_predictions:
        return 0.0
    if gold is None:
        return sum(a != b for a, b in zip(clean_predictions, corrupted_predictions)) / len(
            clean_predictions
        )
    clean_acc = ledger_query_accuracy(clean_predictions, gold)
    corrupted_acc = ledger_query_accuracy(corrupted_predictions, gold)
    return clean_acc - corrupted_acc


def state_acc_at_t(predicted: Sequence[Any], gold: Sequence[Any]) -> float:
    return ledger_query_accuracy(predicted, gold)


def transition_f1(
    predicted: Iterable[Tuple[Any, ...]],
    gold: Iterable[Tuple[Any, ...]],
) -> float:
    pred_set = set(predicted)
    gold_set = set(gold)
    if not pred_set and not gold_set:
        return 1.0
    if not pred_set or not gold_set:
        return 0.0
    tp = len(pred_set & gold_set)
    precision = tp / len(pred_set)
    recall = tp / len(gold_set)
    return 0.0 if precision + recall == 0 else 2 * precision * recall / (precision + recall)


def relation_change_f1(predicted: Iterable[Tuple[Any, ...]], gold: Iterable[Tuple[Any, ...]]) -> float:
    return transition_f1(predicted, gold)


def ledger_faithfulness_score(
    query_consistency: float,
    corruption_sensitivity_score: float,
    evidence_alignment: float,
) -> float:
    return query_consistency * corruption_sensitivity_score * evidence_alignment


def risk_coverage_auc(
    confidences: Sequence[float],
    correctness: Sequence[Any],
) -> float:
    """Compute discrete area under the selective risk-coverage curve.

    Examples are retained from highest to lowest confidence. At each coverage
    step, risk is the cumulative error rate among retained examples; the
    returned value is the mean of those risks. Lower is better.
    """

    if len(confidences) != len(correctness):
        raise ValueError("confidences and correctness must have the same length")
    if not confidences:
        return 0.0
    if any(not math.isfinite(float(confidence)) for confidence in confidences):
        raise ValueError("confidences must be finite")

    ranked = sorted(
        enumerate(zip(confidences, correctness)),
        key=lambda item: (-float(item[1][0]), item[0]),
    )
    cumulative_errors = 0.0
    risks = []
    for retained_count, (_, (_, is_correct)) in enumerate(ranked, start=1):
        cumulative_errors += 0.0 if bool(is_correct) else 1.0
        risks.append(cumulative_errors / retained_count)
    return sum(risks) / len(risks)
