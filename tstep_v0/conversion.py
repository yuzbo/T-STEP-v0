"""Explicit observation-to-execution conversions.

No unconditional StateInterval-to-EventOperator conversion exists by design.
"""

from __future__ import annotations

from .ledger_schema import (
    ConversionCertificate,
    EventOperator,
    RecordKind,
    StateChangeCandidate,
    StateInterval,
    StatePredicate,
    StateRecord,
    VerificationStatus,
)
from .validators import (
    ValidationError,
    validate_conversion_certificate,
    validate_time_spans,
)


def state_interval_to_observed_record(interval: StateInterval) -> StateRecord:
    validate_time_spans((interval,))
    return StateRecord(
        object_id=interval.entity_ref,
        variable=interval.state_key,
        value=interval.typed_value,
        t=interval.start_ms / 1000.0,
        event_id=f"observation:{interval.interval_id}",
        record_id=f"observed:{interval.interval_id}",
        valid_from_ms=interval.start_ms,
        valid_to_ms=interval.end_ms,
        producer=f"observation:{interval.interval_id}",
        record_kind=RecordKind.OBSERVED,
        source=interval.source,
        provenance=interval.provenance,
    )


def interval_triplet_to_state_change_candidate(
    before: StateInterval,
    transitioning: StateInterval,
    after: StateInterval,
) -> StateChangeCandidate:
    validate_time_spans((before, transitioning, after))
    if len({before.entity_ref, transitioning.entity_ref, after.entity_ref}) != 1:
        raise ValidationError("interval triplet must bind to one persistent object")
    if len({before.state_key, transitioning.state_key, after.state_key}) != 1:
        raise ValidationError("interval triplet must use one state key")
    if before.typed_value == after.typed_value:
        raise ValidationError("before and after values must differ")
    if not (
        before.end_ms <= transitioning.start_ms
        and transitioning.end_ms <= after.start_ms
    ):
        raise ValidationError("transition interval must lie between before and after")
    return StateChangeCandidate(
        candidate_id=f"candidate:{before.interval_id}:{after.interval_id}",
        entity_ref=before.entity_ref,
        state_key=before.state_key,
        before_value=before.typed_value,
        after_value=after.typed_value,
        transition_span_ms=(transitioning.start_ms, transitioning.end_ms),
        linked_interval_ids=(
            before.interval_id,
            transitioning.interval_id,
            after.interval_id,
        ),
        source="interval_triplet",
        verification_status=VerificationStatus.METADATA_ONLY,
    )


def candidate_to_event_operator(
    candidate: StateChangeCandidate,
    certificate: ConversionCertificate,
) -> EventOperator:
    validate_conversion_certificate(certificate)
    if certificate.candidate_id not in (None, candidate.candidate_id):
        raise ValidationError("certificate candidate_id does not match StateChangeCandidate")
    if certificate.linked_interval_ids and (
        tuple(certificate.linked_interval_ids) != tuple(candidate.linked_interval_ids)
    ):
        raise ValidationError("certificate interval links do not match candidate")
    if certificate.participants.get("affected") != candidate.entity_ref:
        raise ValidationError("certificate affected participant does not match candidate")

    start_ms, end_ms = candidate.transition_span_ms
    return EventOperator(
        event_id=f"event:{candidate.candidate_id}",
        t_start=start_ms / 1000.0,
        t_end=end_ms / 1000.0,
        op_type=certificate.operator_type,
        object_id=candidate.entity_ref,
        variable=candidate.state_key,
        before=candidate.before_value,
        after=candidate.after_value,
        participants=certificate.participants,
        preconditions=(
            StatePredicate(
                candidate.entity_ref,
                candidate.state_key,
                candidate.before_value,
            ),
        ),
        effects=(
            StatePredicate(
                candidate.entity_ref,
                candidate.state_key,
                candidate.after_value,
            ),
        ),
        event_span_ms=candidate.transition_span_ms,
        apply_boundary_id=certificate.apply_boundary_id,
        source="certified_conversion",
        provenance=certificate.provenance,
        verification_status=VerificationStatus.VERIFIED,
        evidence_refs=certificate.evidence_refs,
        conversion_certificate_id=certificate.certificate_id,
        identity_certificate_id=certificate.identity_certificate_id,
        metadata={
            "conversion_reviewer": certificate.reviewer,
            "linked_interval_ids": candidate.linked_interval_ids,
        },
    )
