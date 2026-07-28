"""Deterministic state ledger update engine."""

from __future__ import annotations

from typing import Iterable, List

from .ledger_schema import ConflictRecord, EventOperator, RecordKind, StateLedger, StateRecord
from .validators import validate_operator_signature


class LedgerExecutionError(RuntimeError):
    pass


def apply_event_operator(
    ledger: StateLedger,
    event: EventOperator,
    *,
    strict: bool = False,
) -> StateLedger:
    """Apply one typed transition operator.

    The v0 policy is deliberately conservative: if an explicit ``before`` value
    is supplied and does not match the current ledger state, the event is logged
    as a conflict and the state is not changed.
    """

    validate_operator_signature(event)
    conflicts = []
    for precondition in event.preconditions:
        current = ledger.get_state(precondition.entity_ref, precondition.state_key)
        if current != precondition.typed_value:
            conflicts.append(
                ConflictRecord(
                    event_id=event.event_id,
                    object_id=precondition.entity_ref,
                    variable=precondition.state_key,
                    expected=precondition.typed_value,
                    actual=current,
                    message="precondition_mismatch",
                )
            )

    if conflicts:
        if strict:
            first = conflicts[0]
            raise LedgerExecutionError(
                f"{event.event_id}: expected "
                f"{first.object_id}.{first.variable}={first.expected!r}, "
                f"got {first.actual!r}"
            )
        return ledger.with_conflicts(conflicts, event)

    commit_time = (
        event.event_span_ms[1] / 1000.0
        if event.event_span_ms is not None
        else event.t_end
    )
    records = [
        StateRecord(
            object_id=effect.entity_ref,
            variable=effect.state_key,
            value=effect.typed_value,
            t=commit_time,
            event_id=event.event_id,
            confidence=event.confidence,
            evidence=event.evidence,
            producer=event.event_id,
            record_kind=RecordKind.DERIVED,
            source=event.source,
            provenance=event.provenance,
        )
        for effect in event.effects
    ]
    return ledger.with_records(records, event)


def apply_event_operators(
    ledger: StateLedger,
    events: Iterable[EventOperator],
    *,
    sort_by_time: bool = True,
    strict: bool = False,
) -> StateLedger:
    ordered_events = list(events)
    if sort_by_time:
        ordered_events.sort(key=lambda event: (event.t_start, event.t_end, event.event_id))

    updated = ledger
    for event in ordered_events:
        updated = apply_event_operator(updated, event, strict=strict)
    return updated


def detect_missing_transitions(
    ledger: StateLedger,
    expected_events: Iterable[EventOperator],
) -> List[EventOperator]:
    """Return expected events whose IDs are absent from the ledger.

    This is a simple Phase 0 helper, not a learned missing-transition detector.
    """

    seen = {event.event_id for event in ledger.events}
    return [event for event in expected_events if event.event_id not in seen]
