"""Unified sample schema and JSONL helpers for T-STEP-v0."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, Mapping, Optional, Sequence, Tuple

from .ledger_schema import (
    CompetingInstance,
    ConversionCertificate,
    CorrectionDirection,
    CorrectionRecord,
    CorruptionSpec,
    EntityRef,
    EvidenceSpan,
    EventOperator,
    EventPresuppositionStatus,
    IdentityAmbiguity,
    IdentityAnchor,
    IdentityCertificate,
    IdentityEvidenceBasis,
    IdentityScope,
    LedgerQuery,
    MetricApplicability,
    ProofRequirements,
    Provenance,
    QuerySpec,
    RecordKind,
    StateChangeCandidate,
    StateInterval,
    StateLedger,
    StatePredicate,
    StateRecord,
    TerminalPredicate,
    TransitionBoundary,
    VerificationStatus,
    VisibilityObservation,
    VisibilityState,
)
from .ledger_update import apply_event_operators
from .validators import validate_ledger, validate_no_answer_access


SCHEMA_VERSION = "tstep-ledger-core-v0.2"
DEEP_ANNOTATION_SCHEMA_VERSION = "tstep-deep-annotation-v0.2"
QUERY_TYPE_ALIASES = {
    "final_state": "final_state",
    "intermediate_state": "state_at",
    "state_at": "state_at",
    "event_order": "event_order",
    "count": "count_transitions",
    "count_transitions": "count_transitions",
    "changed_to": "changed_to",
    "event_exists": "event_exists",
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


@dataclass(frozen=True)
class LedgerBuildInput:
    """Answer-free, typed input accepted by the production ledger builder."""

    sample_id: str
    video_id: str
    initial_records: Tuple[StateRecord, ...] = ()
    operators: Tuple[EventOperator, ...] = ()
    entities: Tuple[EntityRef, ...] = ()
    intervals: Tuple[StateInterval, ...] = ()
    boundaries: Tuple[TransitionBoundary, ...] = ()
    evidence_spans: Tuple[EvidenceSpan, ...] = ()
    visibility_observations: Tuple[VisibilityObservation, ...] = ()
    terminal_predicates: Tuple[TerminalPredicate, ...] = ()
    state_change_candidates: Tuple[StateChangeCandidate, ...] = ()
    conversion_certificates: Tuple[ConversionCertificate, ...] = ()
    identity_certificates: Tuple[IdentityCertificate, ...] = ()
    correction_records: Tuple[CorrectionRecord, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "LedgerBuildInput":
        validate_no_answer_access(payload)
        if payload.get("schema_version") != DEEP_ANNOTATION_SCHEMA_VERSION:
            raise ValueError(
                "production LedgerBuildInput requires an answer-free "
                f"{DEEP_ANNOTATION_SCHEMA_VERSION!r} package"
            )
        return _deep_package_to_build_input(payload)


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
        if float(event["end_sec"]) <= float(event["start_sec"]):
            raise ValueError(f"events[{index}] must have a positive-length span")
        operator = _require_mapping(event["operator"], f"events[{index}].operator")
        _require_keys(
            operator,
            {"op_type", "target_object", "variable", "before", "after", "confidence"},
            f"events[{index}].operator",
        )
        if operator["op_type"] not in TRANSITION_TYPES:
            raise ValueError(f"unsupported transition type: {operator['op_type']!r}")


def build_ledger(
    build_input: LedgerBuildInput,
    *,
    allow_unverified_toy: bool = False,
) -> StateLedger:
    """Build a ledger without accepting any question or gold-answer payload."""

    if not isinstance(build_input, LedgerBuildInput):
        raise TypeError("build_ledger accepts LedgerBuildInput, not a full sample mapping")
    ledger = StateLedger(
        records=build_input.initial_records,
        metadata={"sample_id": build_input.sample_id, "video_id": build_input.video_id, **build_input.metadata},
        entities=build_input.entities,
        intervals=build_input.intervals,
        boundaries=build_input.boundaries,
        evidence_spans=build_input.evidence_spans,
        visibility_observations=build_input.visibility_observations,
        terminal_predicates=build_input.terminal_predicates,
        state_change_candidates=build_input.state_change_candidates,
        conversion_certificates=build_input.conversion_certificates,
        identity_certificates=build_input.identity_certificates,
        correction_records=build_input.correction_records,
    )
    ledger = apply_event_operators(
        ledger,
        build_input.operators,
        allow_unverified_toy=allow_unverified_toy,
    )
    if not allow_unverified_toy:
        validate_ledger(ledger)
    return ledger


def sample_to_ledger(build_input: LedgerBuildInput) -> StateLedger:
    """Production compatibility name: accepts only an answer-free typed input."""

    return build_ledger(build_input)


def project_synthetic_toy_build_input(
    sample: Mapping[str, Any],
    *,
    events: Optional[Sequence[Mapping[str, Any]]] = None,
) -> LedgerBuildInput:
    """Evaluator-only projection for legacy synthetic fixtures.

    The full sample is validated here, then only answer-free fields are copied
    into the builder input. This function is intentionally named synthetic/toy
    and must not be used for real-data result claims.
    """

    validate_unified_sample(sample)
    safe_payload = {
        "sample_id": sample["sample_id"],
        "video": sample["video"],
        "objects": sample["objects"],
        "events": list(sample["events"] if events is None else events),
        "states": sample["states"],
        "relations": sample["relations"],
        "evidence": sample["evidence"],
    }
    validate_no_answer_access(safe_payload)
    evidence_by_id = {
        str(row["evidence_span_id"]): _evidence_span(safe_payload, row)
        for row in safe_payload["evidence"]
    }
    initial_records = []
    for row in safe_payload["states"]:
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
                producer="__initial__",
                record_kind=RecordKind.INITIAL,
                source=str(state.get("source", "synthetic_toy")),
            )
        )

    operators = []
    for event in safe_payload["events"]:
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
                evidence_refs=tuple(str(value) for value in event.get("evidence_span_ids", ())),
                metadata={"event_type": event.get("event_type"), "synthetic_toy": True},
            )
        )
    return LedgerBuildInput(
        sample_id=str(safe_payload["sample_id"]),
        video_id=str(safe_payload["video"]["video_id"]),
        initial_records=tuple(initial_records),
        operators=tuple(operators),
        evidence_spans=tuple(evidence_by_id.values()),
        metadata={"build_kind": "synthetic_toy_projection"},
    )


def synthetic_toy_sample_to_ledger(
    sample: Mapping[str, Any],
    *,
    events: Optional[Sequence[Mapping[str, Any]]] = None,
) -> StateLedger:
    return build_ledger(
        project_synthetic_toy_build_input(sample, events=events),
        allow_unverified_toy=True,
    )


def sample_to_query(raw: Mapping[str, Any]) -> LedgerQuery:
    """Compile an answer-free ledger-query object."""

    validate_no_answer_access(raw)
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


def synthetic_toy_sample_to_query(sample: Mapping[str, Any]) -> LedgerQuery:
    validate_unified_sample(sample)
    return sample_to_query(dict(sample["ledger_query"]))


def query_spec_from_deep_package(payload: Mapping[str, Any]) -> QuerySpec:
    """Compile the answer-blind query contract stored beside a deep package."""

    validate_no_answer_access(payload)
    if payload.get("schema_version") != DEEP_ANNOTATION_SCHEMA_VERSION:
        raise ValueError("unsupported deep annotation schema version")
    row = _require_mapping(payload.get("query_spec"), "query_spec")
    proof = _require_mapping(row["proof_requirements"], "query_spec.proof_requirements")
    metrics = _require_mapping(row["metric_applicability"], "query_spec.metric_applicability")
    reviewed = row.get("reviewed_span_ms")
    return QuerySpec(
        query_id=str(row["query_id"]),
        query_ast=dict(row["query_ast"]),
        target_entity_ids=tuple(str(value) for value in row["target_entity_ids"]),
        expected_answer_type=str(row["expected_answer_type"]),
        event_presupposition_status=EventPresuppositionStatus(row["event_presupposition_status"]),
        proof_requirements=ProofRequirements(
            required_event_ids=tuple(str(value) for value in proof["required_event_ids"]),
            required_state_record_ids=tuple(
                str(value) for value in proof["required_state_record_ids"]
            ),
            identity_dependent=bool(proof["identity_dependent"]),
        ),
        metric_applicability=MetricApplicability(
            state_acc=bool(metrics["state_acc"]),
            transition_f1=bool(metrics["transition_f1"]),
            ledger_query_accuracy=bool(metrics["ledger_query_accuracy"]),
            transition_drop=bool(metrics["transition_drop"]),
            object_id_swap=bool(metrics["object_id_swap"]),
        ),
        question_text=str(payload["sample"].get("question_text", "")),
        presupposed_event_refs=tuple(str(value) for value in row["presupposed_event_refs"]),
        presupposition_evidence_refs=tuple(
            str(value) for value in row["presupposition_evidence_refs"]
        ),
        reviewed_span_ms=(
            tuple(int(value) for value in reviewed) if reviewed is not None else None
        ),
        presupposition_reason_code=row.get("presupposition_reason_code"),
    )


def corruption_specs_from_deep_package(
    payload: Mapping[str, Any],
) -> Tuple[CorruptionSpec, ...]:
    validate_no_answer_access(payload)
    return tuple(
        CorruptionSpec(
            corruption_id=str(row["corruption_id"]),
            corruption_type=str(row["corruption_type"]),
            target_ids=tuple(str(value) for value in row["target_ids"]),
            eligibility_reason=str(row["eligibility_reason"]),
            expected_relation_to_clean=str(row["expected_relation_to_clean"]),
            expected_corrupted_answer=row.get("expected_corrupted_answer"),
            validator_version=str(row["validator_version"]),
        )
        for row in payload.get("corruption_specs", ())
    )


def _deep_package_to_build_input(payload: Mapping[str, Any]) -> LedgerBuildInput:
    sample = _require_mapping(payload.get("sample"), "sample")
    evidence_spans = tuple(_parse_evidence_span(row, sample) for row in payload.get("evidence_spans", ()))
    evidence_by_id = {span.span_id: span for span in evidence_spans if span.span_id}

    entities = []
    for raw_entity in payload.get("entities", ()):
        entity = _require_mapping(raw_entity, "entities[]")
        anchors = tuple(
            IdentityAnchor(
                t_ms=int(anchor["t_ms"]),
                visibility=str(anchor["visibility"]),
                bbox_xyxy=(
                    tuple(float(value) for value in anchor["bbox_xyxy"])
                    if anchor.get("bbox_xyxy") is not None
                    else None
                ),
                reference=anchor.get("reference"),
                anchor_id=str(anchor["anchor_id"]),
                role=str(anchor["role"]),
                evidence_refs=tuple(str(value) for value in anchor.get("evidence_refs", ())),
                source_basis=IdentityEvidenceBasis(anchor["source_basis"]),
                provenance=_parse_provenance(anchor.get("provenance")),
            )
            for anchor in entity.get("identity_anchors", ())
        )
        entities.append(
            EntityRef(
                entity_id=str(entity["entity_id"]),
                entity_type=str(entity["entity_type"]),
                identity_scope=IdentityScope(entity["identity_scope"]),
                subject_label=entity.get("subject_label"),
                identity_anchors=anchors,
                identity_ambiguity=IdentityAmbiguity(entity["identity_ambiguity"]),
                provenance=_parse_provenance(entity.get("provenance")),
            )
        )

    intervals = tuple(
        StateInterval(
            interval_id=str(row["interval_id"]),
            entity_ref=str(row["entity_ref"]),
            state_key=str(row["state_key"]),
            typed_value=row.get("typed_value"),
            start_ms=int(row["start_ms"]),
            end_ms=int(row["end_ms"]),
            observation_status=str(row["observation_status"]),
            source=str(row["source"]),
            provenance=_parse_provenance(row.get("provenance")),
        )
        for row in payload.get("state_intervals", ())
    )
    boundaries = tuple(
        TransitionBoundary(
            boundary_id=str(row["boundary_id"]),
            entity_ref=str(row["entity_ref"]),
            state_key=str(row["state_key"]),
            boundary_kind=str(row["boundary_kind"]),
            lo_ms=int(row["lo_ms"]),
            hi_ms=int(row["hi_ms"]),
            linked_interval_ids=tuple(str(value) for value in row.get("linked_interval_ids", ())),
            source=str(row["source"]),
            provenance=_parse_provenance(row.get("provenance")),
        )
        for row in payload.get("transition_boundaries", ())
    )
    candidates = tuple(
        StateChangeCandidate(
            candidate_id=str(row["candidate_id"]),
            entity_ref=str(row["entity_ref"]),
            state_key=str(row["state_key"]),
            before_value=row.get("before_value"),
            after_value=row.get("after_value"),
            transition_span_ms=tuple(int(value) for value in row["transition_span_ms"]),
            linked_interval_ids=tuple(str(value) for value in row["linked_interval_ids"]),
            source=str(row["source"]),
            verification_status=VerificationStatus(row["verification_status"]),
        )
        for row in payload.get("state_change_candidates", ())
    )
    visibility = tuple(
        VisibilityObservation(
            observation_id=str(row["observation_id"]),
            entity_ref=str(row["entity_ref"]),
            start_ms=int(row["start_ms"]),
            end_ms=int(row["end_ms"]),
            visible_fraction_lo=float(row["visible_fraction_lo"]),
            visible_fraction_hi=float(row["visible_fraction_hi"]),
            state=VisibilityState(row["state"]),
            occluder_ref=row.get("occluder_ref"),
            continuous_track=bool(row.get("continuous_track", False)),
            manual_identity_evidence=bool(row.get("manual_identity_evidence", False)),
            frame_boundary_crossing=bool(row.get("frame_boundary_crossing", False)),
            evidence_refs=tuple(str(value) for value in row.get("evidence_refs", ())),
            provenance=_parse_provenance(row.get("provenance")),
        )
        for row in payload.get("visibility_observations", ())
    )
    terminal_predicates = tuple(
        TerminalPredicate(
            predicate_id=str(row["predicate_id"]),
            entity_ref=str(row["entity_ref"]),
            predicate_type=str(row["predicate_type"]),
            holds_from_ms=int(row["holds_from_ms"]),
            verified_through_ms=int(row["verified_through_ms"]),
            clip_end_ms=int(row["clip_end_ms"]),
            evidence_refs=tuple(str(value) for value in row.get("evidence_refs", ())),
            verification_status=VerificationStatus(row["verification_status"]),
            provenance=_parse_provenance(row.get("provenance")),
        )
        for row in payload.get("terminal_predicates", ())
    )
    identity_certificates = tuple(
        IdentityCertificate(
            certificate_id=str(row["certificate_id"]),
            entity_ref=str(row["entity_ref"]),
            pre_gap_anchor_id=str(row["pre_gap_anchor_id"]),
            post_gap_anchor_id=str(row["post_gap_anchor_id"]),
            competing_instances=tuple(
                CompetingInstance(
                    entity_ref=str(item["entity_ref"]),
                    same_class=bool(item["same_class"]),
                    evidence_refs=tuple(str(value) for value in item.get("evidence_refs", ())),
                    excluded_by=item.get("excluded_by"),
                )
                for item in row.get("competing_instances", ())
            ),
            identity_scope=IdentityScope(row["identity_scope"]),
            ambiguity=IdentityAmbiguity(row["ambiguity"]),
            evidence_refs=tuple(str(value) for value in row.get("evidence_refs", ())),
            reviewer=str(row["reviewer"]),
            provenance=_parse_provenance(row.get("provenance")),
            manual_oracle_basis=bool(row["manual_oracle_basis"]),
            competitor_inventory_reviewed=bool(row["competitor_inventory_reviewed"]),
        )
        for row in payload.get("identity_certificates", ())
    )
    conversion_certificates = tuple(
        ConversionCertificate(
            same_persistent_object=bool(row["same_persistent_object"]),
            same_state_key=bool(row["same_state_key"]),
            explicit_before_after=bool(row["explicit_before_after"]),
            explicit_operator_type=bool(row["explicit_operator_type"]),
            participant_roles_verified=bool(row["participant_roles_verified"]),
            commit_boundary_verified=bool(row["commit_boundary_verified"]),
            operator_type=str(row["operator_type"]),
            participants={str(key): str(value) for key, value in row["participants"].items()},
            apply_boundary_id=str(row["apply_boundary_id"]),
            reviewer=str(row["reviewer"]),
            provenance=_require_provenance(row.get("provenance"), "conversion certificate"),
            certificate_id=str(row["certificate_id"]),
            candidate_id=row.get("candidate_id"),
            linked_interval_ids=tuple(str(value) for value in row.get("linked_interval_ids", ())),
            evidence_refs=tuple(str(value) for value in row.get("evidence_refs", ())),
            identity_certificate_id=row.get("identity_certificate_id"),
        )
        for row in payload.get("conversion_certificates", ())
    )

    operators = []
    for row in payload.get("event_operators", ()):
        span_ms = tuple(int(value) for value in row["event_span_ms"])
        preconditions = tuple(_parse_predicate(value) for value in row.get("preconditions", ()))
        effects = tuple(_parse_predicate(value) for value in row.get("effects", ()))
        affected = str(row["participants"]["affected"])
        primary_effect = effects[0]
        evidence_refs = tuple(str(value) for value in row.get("evidence_refs", ()))
        operators.append(
            EventOperator(
                event_id=str(row["event_id"]),
                t_start=span_ms[0] / 1000.0,
                t_end=span_ms[1] / 1000.0,
                op_type=str(row["operator_type"]),
                object_id=affected,
                variable=primary_effect.state_key,
                before=preconditions[0].typed_value if preconditions else None,
                after=primary_effect.typed_value,
                confidence=float(row.get("confidence", 1.0)),
                evidence=tuple(evidence_by_id[value] for value in evidence_refs if value in evidence_by_id),
                participants={str(key): str(value) for key, value in row["participants"].items()},
                preconditions=preconditions,
                effects=effects,
                event_span_ms=span_ms,
                apply_boundary_id=str(row["apply_boundary_id"]),
                source=str(row["source"]),
                provenance=_parse_provenance(row.get("provenance")),
                verification_status=VerificationStatus(row["verification_status"]),
                evidence_refs=evidence_refs,
                conversion_certificate_id=str(row["conversion_certificate_id"]),
                identity_certificate_id=row.get("identity_certificate_id"),
            )
        )

    records = tuple(_parse_state_record(row) for row in payload.get("initial_state_records", ()))
    corrections = tuple(_parse_correction_record(row) for row in payload.get("correction_records", ()))
    return LedgerBuildInput(
        sample_id=str(sample["sample_id"]),
        video_id=str(sample["video_id"]),
        initial_records=records,
        operators=tuple(operators),
        entities=tuple(entities),
        intervals=intervals,
        boundaries=boundaries,
        evidence_spans=evidence_spans,
        visibility_observations=visibility,
        terminal_predicates=terminal_predicates,
        state_change_candidates=candidates,
        conversion_certificates=conversion_certificates,
        identity_certificates=identity_certificates,
        correction_records=corrections,
        metadata={"schema_version": DEEP_ANNOTATION_SCHEMA_VERSION},
    )


def _parse_evidence_span(row: Mapping[str, Any], sample: Mapping[str, Any]) -> EvidenceSpan:
    return EvidenceSpan(
        video_id=str(sample["video_id"]),
        start=int(row["start_ms"]) / 1000.0,
        end=int(row["end_ms"]) / 1000.0,
        object_ids=tuple(str(value) for value in row.get("object_ids", ())),
        score=float(row.get("score", 1.0)),
        span_id=str(row["evidence_id"]),
    )


def _parse_predicate(row: Mapping[str, Any]) -> StatePredicate:
    return StatePredicate(
        entity_ref=str(row["entity_ref"]),
        state_key=str(row["state_key"]),
        typed_value=row.get("typed_value"),
    )


def _parse_state_record(row: Mapping[str, Any]) -> StateRecord:
    valid_from_ms = int(row["valid_from_ms"])
    return StateRecord(
        object_id=str(row["entity_ref"]),
        variable=str(row["state_key"]),
        value=row.get("typed_value"),
        t=valid_from_ms / 1000.0,
        event_id=str(row["producer"]),
        record_id=str(row["record_id"]),
        valid_from_ms=valid_from_ms,
        valid_to_ms=(int(row["valid_to_ms"]) if row.get("valid_to_ms") is not None else None),
        producer=str(row["producer"]),
        record_kind=RecordKind(row["record_kind"]),
        source=str(row["source"]),
        provenance=_parse_provenance(row.get("provenance")),
    )


def _parse_correction_record(row: Mapping[str, Any]) -> CorrectionRecord:
    return CorrectionRecord(
        correction_id=str(row["correction_id"]),
        direction=CorrectionDirection(row["direction"]),
        before_hypothesis=row.get("before_hypothesis"),
        proposed_hypothesis=row.get("proposed_hypothesis"),
        final_hypothesis=row.get("final_hypothesis"),
        evidence_refs=tuple(str(value) for value in row.get("evidence_refs", ())),
        affected_layers=tuple(str(value) for value in row.get("affected_layers", ())),
        consistency_before=bool(row["consistency_before"]),
        consistency_after=bool(row["consistency_after"]),
        decision=str(row["decision"]),
        provenance=_require_provenance(row.get("provenance"), "correction record"),
        gold_correct_before=row.get("gold_correct_before"),
        gold_correct_after=row.get("gold_correct_after"),
    )


def _parse_provenance(value: Any) -> Optional[Provenance]:
    if value is None:
        return None
    row = _require_mapping(value, "provenance")
    return Provenance(
        source=str(row["source"]),
        annotator_id=row.get("annotator_id"),
        artifact_ref=row.get("artifact_ref"),
        metadata=dict(row.get("metadata") or {}),
    )


def _require_provenance(value: Any, owner: str) -> Provenance:
    provenance = _parse_provenance(value)
    if provenance is None:
        raise ValueError(f"{owner} requires provenance")
    return provenance


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
        span_id=str(row["evidence_span_id"]),
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
