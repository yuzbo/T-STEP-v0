"""Semantic validators for the Phase 0 executable-ledger boundary."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any, Iterable, Mapping, Sequence

from .ledger_schema import (
    CorruptionSpec,
    EntityRef,
    EventOperator,
    IdentityScope,
    QuerySpec,
    RecordKind,
    StateInterval,
    StateLedger,
    StateRecord,
    TransitionBoundary,
)


class ValidationError(ValueError):
    pass


def validate_time_spans(
    intervals: Iterable[StateInterval] = (),
    boundaries: Iterable[TransitionBoundary] = (),
) -> None:
    for interval in intervals:
        if interval.start_ms < 0 or interval.end_ms <= interval.start_ms:
            raise ValidationError(
                f"invalid half-open StateInterval {interval.interval_id}: "
                f"[{interval.start_ms}, {interval.end_ms})"
            )
    for boundary in boundaries:
        if boundary.lo_ms < 0 or boundary.hi_ms < boundary.lo_ms:
            raise ValidationError(
                f"invalid TransitionBoundary {boundary.boundary_id}: "
                f"[{boundary.lo_ms}, {boundary.hi_ms}]"
            )


def validate_identity_scope(
    entity: EntityRef,
    *,
    require_persistent: bool = False,
) -> None:
    scope = IdentityScope(entity.identity_scope)
    if require_persistent and scope is not IdentityScope.PERSISTENT_ID:
        raise ValidationError(
            f"entity {entity.entity_id!r} requires persistent_id, got {scope.value}"
        )
    if scope is IdentityScope.PERSISTENT_ID and not entity.identity_anchors:
        raise ValidationError(
            f"persistent entity {entity.entity_id!r} requires identity anchors"
        )


def validate_operator_signature(event: EventOperator) -> None:
    if event.t_start < 0 or event.t_end <= event.t_start:
        raise ValidationError(
            f"invalid EventOperator span for {event.event_id}: "
            f"[{event.t_start}, {event.t_end})"
        )
    if not event.participants.get("affected"):
        raise ValidationError(f"EventOperator {event.event_id} lacks affected participant")
    if not event.effects:
        raise ValidationError(f"EventOperator {event.event_id} has no effects")
    for effect in event.effects:
        if not effect.entity_ref or not effect.state_key:
            raise ValidationError(f"EventOperator {event.event_id} has malformed effect")


def validate_record_provenance(
    record: StateRecord,
    *,
    event_ids: Sequence[str],
) -> None:
    if not record.producer:
        raise ValidationError(f"StateRecord {record.record_id} has no producer")
    if record.record_kind is RecordKind.DERIVED and record.producer not in event_ids:
        raise ValidationError(
            f"derived StateRecord {record.record_id} has orphan producer {record.producer!r}"
        )
    if record.valid_to_ms is not None and record.valid_from_ms is not None:
        if record.valid_to_ms <= record.valid_from_ms:
            raise ValidationError(
                f"StateRecord {record.record_id} has invalid validity interval"
            )


def validate_no_orphan_records(ledger: StateLedger) -> None:
    event_ids = [event.event_id for event in ledger.events]
    for record in ledger.records:
        validate_record_provenance(record, event_ids=event_ids)


def validate_query_applicability(query: QuerySpec) -> None:
    applicability = query.metric_applicability
    if not applicability.ledger_query_accuracy:
        raise ValidationError("every accepted QuerySpec must support ledger_query_accuracy")
    if applicability.transition_f1 and not query.proof_requirements.required_event_ids:
        raise ValidationError(
            "transition_f1 requires at least one proof-required EventOperator"
        )
    if applicability.object_id_swap and not query.proof_requirements.identity_dependent:
        raise ValidationError("object_id_swap requires identity_dependent proof")


def validate_corruption_spec(spec: CorruptionSpec) -> None:
    if spec.corruption_type not in {"transition_drop", "object_id_swap"}:
        raise ValidationError(f"unsupported Phase 0 corruption: {spec.corruption_type!r}")
    if not spec.target_ids:
        raise ValidationError("corruption target_ids cannot be empty")
    if spec.expected_relation_to_clean not in {"SAME", "DIFFERENT", "UNKNOWN"}:
        raise ValidationError("invalid expected_relation_to_clean")


def validate_no_answer_access(payload: Any) -> None:
    """Reject gold-answer material from builder/compiler/executor inputs."""

    forbidden = {"answer", "gold_answer", "gt_answer", "correct_answer"}
    for path, key in _walk_keys(payload):
        if key.lower() in forbidden:
            raise ValidationError(f"answer leakage field at {path}: {key}")


def validate_ledger(ledger: StateLedger) -> None:
    validate_time_spans(ledger.intervals, ledger.boundaries)
    for entity in ledger.entities:
        validate_identity_scope(entity)
    for event in ledger.events:
        validate_operator_signature(event)
    validate_no_orphan_records(ledger)


def _walk_keys(payload: Any, path: str = "$") -> Iterable[tuple[str, str]]:
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            key_text = str(key)
            yield path, key_text
            yield from _walk_keys(value, f"{path}.{key_text}")
        return
    if is_dataclass(payload):
        for field_info in fields(payload):
            value = getattr(payload, field_info.name)
            yield path, field_info.name
            yield from _walk_keys(value, f"{path}.{field_info.name}")
        return
    if isinstance(payload, (list, tuple)):
        for index, value in enumerate(payload):
            yield from _walk_keys(value, f"{path}[{index}]")
