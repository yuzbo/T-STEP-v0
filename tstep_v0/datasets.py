"""Unified sample schema and JSONL helpers for T-STEP-v0."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Mapping, Optional, Sequence

from .ledger_schema import EvidenceSpan, EventOperator, LedgerQuery, StateLedger, StateRecord
from .ledger_update import apply_event_operators


SCHEMA_VERSION = "tstep-ledger-core-v0.1"
QUERY_TYPE_ALIASES = {
    "final_state": "final_state",
    "intermediate_state": "state_at",
    "state_at": "state_at",
    "event_order": "event_order",
    "count": "count_transitions",
    "count_transitions": "count_transitions",
    "changed_to": "changed_to",
}
TRANSITION_TYPES = {
    "location",
    "visibility",
    "possession",
    "relation",
    "attribute",
    "state_change",
}
COVERAGE_FLAGS = {
    "has_video",
    "has_question",
    "has_answer",
    "has_temporal_evidence",
    "has_bbox_or_track",
    "has_object_identity",
    "has_state_label",
    "has_transition_boundary",
    "has_relation_label",
    "has_counterfactual_label",
    "can_define_stable_state_variable",
    "requires_manual_state_annotation",
}


@dataclass(frozen=True)
class UnifiedSample:
    schema_version: str
    sample_id: str
    dataset: str
    split: str
    video: Mapping[str, Any]
    question: Mapping[str, Any]
    ledger_query: Mapping[str, Any]
    objects: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    events: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    states: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    relations: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    evidence: Sequence[Mapping[str, Any]] = field(default_factory=tuple)
    coverage: Mapping[str, bool] = field(default_factory=dict)
    audit: Mapping[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_mapping(cls, sample: Mapping[str, Any]) -> "UnifiedSample":
        validate_unified_sample(sample)
        return cls(
            schema_version=str(sample["schema_version"]),
            sample_id=str(sample["sample_id"]),
            dataset=str(sample["dataset"]),
            split=str(sample["split"]),
            video=dict(sample["video"]),
            question=dict(sample["question"]),
            ledger_query=dict(sample["ledger_query"]),
            objects=tuple(sample["objects"]),
            events=tuple(sample["events"]),
            states=tuple(sample["states"]),
            relations=tuple(sample["relations"]),
            evidence=tuple(sample["evidence"]),
            coverage=dict(sample["coverage"]),
            audit=dict(sample["audit"]),
        )


def validate_unified_sample(sample: Mapping[str, Any]) -> None:
    required = {
        "schema_version",
        "sample_id",
        "dataset",
        "split",
        "video",
        "question",
        "ledger_query",
        "objects",
        "events",
        "states",
        "relations",
        "evidence",
        "coverage",
        "audit",
    }
    missing = required - set(sample)
    if missing:
        raise ValueError(f"missing required sample fields: {sorted(missing)}")
    if sample["schema_version"] != SCHEMA_VERSION:
        raise ValueError(
            f"unsupported schema_version: {sample['schema_version']!r}; expected {SCHEMA_VERSION!r}"
        )
    for field_name in ("sample_id", "dataset", "split"):
        if not isinstance(sample[field_name], str) or not sample[field_name].strip():
            raise ValueError(f"{field_name} must be a non-empty string")

    video = _require_mapping(sample["video"], "video")
    question = _require_mapping(sample["question"], "question")
    ledger_query = _require_mapping(sample["ledger_query"], "ledger_query")
    coverage = _require_mapping(sample["coverage"], "coverage")
    _require_mapping(sample["audit"], "audit")
    for field_name in ("objects", "events", "states", "relations", "evidence"):
        _require_sequence(sample[field_name], field_name)

    _require_keys(
        video,
        {"video_id", "path_or_uri", "duration_sec", "fps", "frame_count"},
        "video",
    )
    _require_keys(
        question,
        {
            "question_id",
            "text",
            "type",
            "answer_type",
            "choices",
            "gt_answer",
            "gt_answer_normalized",
        },
        "question",
    )
    _require_keys(
        ledger_query,
        {
            "query_type",
            "target_time_sec",
            "target_event_id",
            "object_refs",
            "variables",
            "relation_refs",
            "intervention",
        },
        "ledger_query",
    )
    query_type = ledger_query["query_type"]
    if query_type not in QUERY_TYPE_ALIASES:
        raise ValueError(f"unsupported ledger_query.query_type: {query_type!r}")

    missing_flags = COVERAGE_FLAGS - set(coverage)
    if missing_flags:
        raise ValueError(f"coverage is missing flags: {sorted(missing_flags)}")
    non_boolean_flags = sorted(key for key in COVERAGE_FLAGS if not isinstance(coverage[key], bool))
    if non_boolean_flags:
        raise ValueError(f"coverage flags must be boolean: {non_boolean_flags}")

    event_ids = set()
    for index, event_value in enumerate(sample["events"]):
        event = _require_mapping(event_value, f"events[{index}]")
        _require_keys(
            event,
            {
                "event_id",
                "event_type",
                "start_sec",
                "end_sec",
                "actors",
                "objects",
                "operator",
                "evidence_span_ids",
            },
            f"events[{index}]",
        )
        if event["event_id"] in event_ids:
            raise ValueError(f"duplicate event_id: {event['event_id']!r}")
        event_ids.add(event["event_id"])
        if float(event["end_sec"]) < float(event["start_sec"]):
            raise ValueError(f"events[{index}] has end_sec before start_sec")
        operator = _require_mapping(event["operator"], f"events[{index}].operator")
        _require_keys(
            operator,
            {"op_type", "target_object", "variable", "before", "after", "confidence"},
            f"events[{index}].operator",
        )
        if operator["op_type"] not in TRANSITION_TYPES:
            raise ValueError(f"unsupported transition type: {operator['op_type']!r}")


def sample_to_ledger(
    sample: Mapping[str, Any],
    *,
    events: Optional[Sequence[Mapping[str, Any]]] = None,
) -> StateLedger:
    """Build and replay the deterministic ledger encoded by one unified sample."""

    validate_unified_sample(sample)
    evidence_by_id = {
        str(row["evidence_span_id"]): _evidence_span(sample, row)
        for row in sample["evidence"]
    }
    initial_records = []
    for row in sample["states"]:
        state = _require_mapping(row, "states[]")
        if state.get("source_event_id") not in (None, "__initial__") and not state.get(
            "is_initial", False
        ):
            continue
        initial_records.append(
            StateRecord(
                object_id=str(state["object_id"]),
                variable=str(state["variable"]),
                value=state.get("value"),
                t=float(state.get("time_sec", float("-inf"))),
                event_id="__initial__",
                confidence=float(state.get("confidence", 1.0)),
            )
        )

    ledger = StateLedger(records=tuple(initial_records))
    operators = []
    for event in sample["events"] if events is None else events:
        operator = _require_mapping(event["operator"], "event.operator")
        evidence = tuple(
            evidence_by_id[evidence_id]
            for evidence_id in event.get("evidence_span_ids", ())
            if evidence_id in evidence_by_id
        )
        operators.append(
            EventOperator(
                event_id=str(event["event_id"]),
                t_start=float(event["start_sec"]),
                t_end=float(event["end_sec"]),
                op_type=str(operator["op_type"]),
                object_id=str(operator["target_object"]),
                variable=str(operator["variable"]),
                before=operator.get("before"),
                after=operator.get("after"),
                target_object_id=operator.get("target_object_id"),
                confidence=float(operator.get("confidence", 1.0)),
                evidence=evidence,
                metadata={"event_type": event.get("event_type")},
            )
        )
    return apply_event_operators(ledger, operators)


def sample_to_query(sample: Mapping[str, Any]) -> LedgerQuery:
    """Map the experiment-plan query object to the v0 executor query."""

    validate_unified_sample(sample)
    raw = sample["ledger_query"]
    query_type = QUERY_TYPE_ALIASES[str(raw["query_type"])]
    object_refs = tuple(raw.get("object_refs") or ())
    variables = tuple(raw.get("variables") or ())
    event_ids = tuple(raw.get("event_ids") or ())
    if not event_ids and raw.get("target_event_id") is not None:
        target_event = raw["target_event_id"]
        event_ids = (
            tuple(target_event)
            if isinstance(target_event, (list, tuple))
            else (str(target_event),)
        )
    return LedgerQuery(
        query_type=query_type,
        object_id=str(object_refs[0]) if object_refs else None,
        variable=str(variables[0]) if variables else None,
        time=(
            float(raw["target_time_sec"])
            if raw.get("target_time_sec") is not None
            else None
        ),
        event_ids=event_ids,
        value=raw.get("value"),
        parameters={
            "relation_refs": tuple(raw.get("relation_refs") or ()),
            "intervention": raw.get("intervention"),
        },
    )


def read_jsonl(path: str | Path) -> Iterator[Dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            record = json.loads(stripped)
            if not isinstance(record, dict):
                raise ValueError(f"line {line_number} is not a JSON object")
            yield record


def write_jsonl(path: str | Path, rows: Iterable[Mapping[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False) + "\n")


def _evidence_span(sample: Mapping[str, Any], row: Mapping[str, Any]) -> EvidenceSpan:
    return EvidenceSpan(
        video_id=str(sample["video"]["video_id"]),
        start=float(row["start_sec"]),
        end=float(row["end_sec"]),
        object_ids=tuple(str(value) for value in row.get("object_ids", ())),
        score=float(row.get("score", 1.0)),
    )


def _require_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field_name} must be an object")
    return value


def _require_sequence(value: Any, field_name: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{field_name} must be an array")
    return value


def _require_keys(value: Mapping[str, Any], keys: set[str], field_name: str) -> None:
    missing = keys - set(value)
    if missing:
        raise ValueError(f"{field_name} is missing fields: {sorted(missing)}")
