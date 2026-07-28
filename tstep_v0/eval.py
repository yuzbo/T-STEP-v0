"""Minimal evaluation runner for ledger query smoke tests."""

from __future__ import annotations

import re
import string
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from .datasets import sample_to_ledger, sample_to_query, validate_unified_sample
from .ledger_schema import LedgerQuery, StateLedger
from .metrics import (
    corruption_sensitivity,
    event_recall_at_budget,
    ledger_query_accuracy,
    risk_coverage_auc,
    transition_f1,
)
from .query_executor import execute_query


QueryExample = Tuple[LedgerQuery, Any]


def evaluate_ledger_queries(
    ledger: StateLedger,
    queries: Iterable[QueryExample],
    *,
    corrupted_ledger: Optional[StateLedger] = None,
) -> Dict[str, Any]:
    examples = list(queries)
    gold = [target for _, target in examples]
    predictions = [execute_query(ledger, query).answer for query, _ in examples]
    report: Dict[str, Any] = {
        "num_queries": len(examples),
        "predictions": predictions,
        "targets": gold,
        "ledger_query_accuracy": ledger_query_accuracy(predictions, gold),
    }
    if corrupted_ledger is not None:
        corrupted_predictions = [
            execute_query(corrupted_ledger, query).answer for query, _ in examples
        ]
        report["corrupted_predictions"] = corrupted_predictions
        report["corruption_sensitivity"] = corruption_sensitivity(
            predictions,
            corrupted_predictions,
            gold,
        )
    return report


def normalize_answer(value: Any) -> Any:
    """Apply the deterministic Phase 0 answer normalization policy."""

    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        numeric = float(value)
        return str(int(numeric)) if numeric.is_integer() else str(numeric)
    text = str(value).lower().strip()
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    return " ".join(text.split())


def evaluate_samples(
    samples: Sequence[Dict[str, Any]],
    *,
    corruption_mode: Optional[str] = None,
    run_id: str = "phase0_toy_smoke",
) -> Dict[str, Any]:
    """Evaluate unified toy samples through ledger construction and execution.

    This runner intentionally consumes annotated transition operators. It is a
    schema/executor/metric smoke test, not a learned baseline.
    """

    if corruption_mode not in (None, "drop_last"):
        raise ValueError(f"unsupported corruption_mode: {corruption_mode!r}")

    rows = []
    predictions = []
    targets = []
    correctness = []
    confidences = []
    corrupted_correctness = []
    for sample in samples:
        validate_unified_sample(sample)
        ledger = sample_to_ledger(sample)
        query = sample_to_query(sample)
        result = execute_query(ledger, query)
        target = sample["question"]["gt_answer_normalized"]
        normalized_prediction = normalize_answer(result.answer)
        normalized_target = normalize_answer(target)
        is_correct = normalized_prediction == normalized_target
        confidence = float(sample.get("audit", {}).get("smoke_confidence", 1.0))

        corruption_answer = None
        corruption_correct = None
        corruption_drop = None
        if corruption_mode == "drop_last":
            corrupted_events = list(sample["events"][:-1])
            corrupted_ledger = sample_to_ledger(sample, events=corrupted_events)
            corruption_result = execute_query(corrupted_ledger, query)
            corruption_answer = corruption_result.answer
            corruption_correct = normalize_answer(corruption_answer) == normalized_target
            corruption_drop = float(is_correct) - float(corruption_correct)
            corrupted_correctness.append(corruption_correct)

        event_recall = _sample_event_recall(sample)
        sample_transition_f1 = _sample_transition_f1(sample)
        rows.append(
            _result_row(
                sample,
                run_id=run_id,
                answer=result.answer,
                normalized_answer=normalized_prediction,
                target=normalized_target,
                is_correct=is_correct,
                confidence=confidence,
                ledger=ledger,
                event_recall=event_recall,
                transition_score=sample_transition_f1,
                corruption_mode=corruption_mode,
                corruption_answer=corruption_answer,
                corruption_correct=corruption_correct,
                corruption_drop=corruption_drop,
            )
        )
        predictions.append(normalized_prediction)
        targets.append(normalized_target)
        correctness.append(is_correct)
        confidences.append(confidence)

    report: Dict[str, Any] = {
        "run_id": run_id,
        "run_kind": "annotated_ledger_smoke",
        "num_samples": len(samples),
        "results": rows,
        "ledger_query_accuracy": ledger_query_accuracy(predictions, targets),
        "risk_coverage_auc": risk_coverage_auc(confidences, correctness),
    }
    if corruption_mode is not None:
        report["corruption_mode"] = corruption_mode
        report["corruption_sensitivity"] = (
            sum(
                float(clean) - float(corrupted)
                for clean, corrupted in zip(correctness, corrupted_correctness)
            )
            / len(correctness)
            if correctness
            else 0.0
        )
    return report


def _sample_event_recall(sample: Mapping[str, Any]) -> Optional[float]:
    selected = sample.get("audit", {}).get("smoke_selected_spans_sec")
    gold = [
        (float(row["start_sec"]), float(row["end_sec"]))
        for row in sample["evidence"]
        if row.get("transition_critical", False)
    ]
    if selected is None or not gold:
        return None
    selected_spans = [(float(span[0]), float(span[1])) for span in selected]
    return event_recall_at_budget(selected_spans, gold, iou_threshold=0.3)


def _sample_transition_f1(sample: Mapping[str, Any]) -> float:
    gold = [
        (
            event["operator"]["target_object"],
            event["operator"]["variable"],
            event["operator"].get("before"),
            event["operator"].get("after"),
        )
        for event in sample["events"]
    ]
    predicted = sample.get("audit", {}).get("smoke_predicted_transitions", gold)
    return transition_f1((tuple(row) for row in predicted), (tuple(row) for row in gold))


def _result_row(
    sample: Mapping[str, Any],
    *,
    run_id: str,
    answer: Any,
    normalized_answer: Any,
    target: Any,
    is_correct: bool,
    confidence: float,
    ledger: StateLedger,
    event_recall: Optional[float],
    transition_score: float,
    corruption_mode: Optional[str],
    corruption_answer: Any,
    corruption_correct: Optional[bool],
    corruption_drop: Optional[float],
) -> Dict[str, Any]:
    audit = sample.get("audit", {})
    selected_spans = audit.get("smoke_selected_spans_sec", [])
    return {
        "schema_version": "tstep-result-v0.1",
        "run_id": run_id,
        "sample_id": sample["sample_id"],
        "dataset": sample["dataset"],
        "split": sample["split"],
        "variant_id": "toy_ledger_oracle",
        "variant_family": "oracle",
        "seed": int(audit.get("seed", 20260706)),
        "seed_effective": False,
        "budget_name": audit.get("budget_name", f"B{len(selected_spans)}"),
        "corruption_id": "clean",
        "run_status": "ok",
        "failure_reason": None,
        "input_refs": {
            "video_id": sample["video"]["video_id"],
            "question_id": sample["question"]["question_id"],
            "ledger_id": f"{sample['sample_id']}:toy_ledger_oracle",
            "selector_id": "annotated_smoke_spans",
        },
        "question": {
            "type": sample["question"]["type"],
            "text": sample["question"]["text"],
            "gt_answer_normalized": target,
        },
        "selection": {
            "selected_spans_sec": selected_spans,
            "selected_clip_count": len(selected_spans),
        },
        "prediction": {
            "raw_answer": answer,
            "normalized_answer": normalized_answer,
            "confidence": confidence,
            "abstained": False,
            "rationale": "answer produced by deterministic ledger query executor",
        },
        "ledger_outputs": {
            "ledger_available": True,
            "transition_count": len(ledger.events),
            "state_entry_count": len(ledger.records),
            "conflict_count": len(ledger.conflicts),
            "executor_answer": answer,
            "executor_answer_normalized": normalized_answer,
            "executor_confidence": confidence,
        },
        "metrics": {
            "final_qa_correct": is_correct,
            "ledger_query_correct": is_correct,
            "event_recall_at_budget": event_recall,
            "transition_f1": transition_score,
        },
        "diagnostics": {
            "corruption_type": corruption_mode,
            "corrupted_executor_answer": corruption_answer,
            "corrupted_correct": corruption_correct,
            "corruption_drop": corruption_drop,
        },
        "notes": "Phase 0 annotated-ledger smoke result; not a learned-model score.",
    }
