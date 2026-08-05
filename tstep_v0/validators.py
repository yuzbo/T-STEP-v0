"""Semantic validators for the Phase 0 executable-ledger boundary."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any, Iterable, Mapping, Sequence

from .ledger_schema import (
    ConversionCertificate,
    CorruptionSpec,
    EntityRef,
    EventPresuppositionStatus,
    EventOperator,
    IdentityAmbiguity,
    IdentityCertificate,
    IdentityEvidenceBasis,
    IdentityScope,
    QuerySpec,
    RecordKind,
    StateInterval,
    StateLedger,
    StateRecord,
    TerminalPredicate,
    TransitionBoundary,
    VerificationStatus,
    VisibilityObservation,
    VisibilityState,
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
    if event.op_type in {"disappears_for_good", "terminal_predicate"}:
        raise ValidationError(
            f"terminal assertion {event.op_type!r} cannot be an EventOperator"
        )
    if event.op_type == "leaves_frame":
        if not any(
            effect.state_key == "visibility"
            and effect.typed_value == VisibilityState.OUT_OF_FRAME.value
            for effect in event.effects
        ):
            raise ValidationError(
                "leaves_frame operator must commit visibility=out_of_frame"
            )
    if event.event_span_ms is None:
        raise ValidationError(f"EventOperator {event.event_id} lacks event_span_ms")
    start_ms, end_ms = event.event_span_ms
    if start_ms < 0 or end_ms <= start_ms:
        raise ValidationError(
            f"invalid EventOperator PTS span for {event.event_id}: [{start_ms}, {end_ms})"
        )
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
    status = EventPresuppositionStatus(query.event_presupposition_status)
    applicability = query.metric_applicability
    required_event_ids = query.proof_requirements.required_event_ids
    query_operator = str(query.query_ast.get("operator", ""))

    if query_operator == "event_exists" and status is not EventPresuppositionStatus.NOT_REQUIRED:
        raise ValidationError("event_exists queries must use not_required presupposition status")
    if status is EventPresuppositionStatus.OBSERVED:
        if not required_event_ids:
            raise ValidationError("observed presupposition requires proof-required events")
        if not query.presupposed_event_refs:
            raise ValidationError("observed presupposition requires presupposed_event_refs")
        if not query.presupposition_evidence_refs:
            raise ValidationError("observed presupposition requires evidence refs")
        if query.reviewed_span_ms is None:
            raise ValidationError("observed presupposition requires reviewed_span_ms")
        if not set(required_event_ids).issubset(query.presupposed_event_refs):
            raise ValidationError("proof-required events must be presupposed event refs")
    elif status in {
        EventPresuppositionStatus.UNSUPPORTED,
        EventPresuppositionStatus.AMBIGUOUS,
        EventPresuppositionStatus.OUTSIDE_CLIP,
    }:
        if required_event_ids:
            raise ValidationError(f"{status.value} query cannot require an EventOperator")
        if any(vars(applicability).values()):
            raise ValidationError(f"{status.value} query must be excluded from metrics/corruption")
        if not query.presupposition_reason_code:
            raise ValidationError(f"{status.value} query requires a reason code")
    elif status is EventPresuppositionStatus.NOT_REQUIRED:
        if required_event_ids:
            raise ValidationError("not_required query cannot list proof-required events")
        if applicability.transition_f1 or applicability.transition_drop:
            raise ValidationError("not_required query cannot enable event metrics/corruption")

    if applicability.transition_f1 and not required_event_ids:
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
    if spec.validator_version != "tstep-corruption-v0.2":
        raise ValidationError("corruption spec must use tstep-corruption-v0.2")


def classify_visibility_observation(observation: VisibilityObservation) -> VisibilityState:
    lo = float(observation.visible_fraction_lo)
    hi = float(observation.visible_fraction_hi)
    if not 0.0 <= lo <= hi <= 1.0:
        raise ValidationError(
            f"invalid visible-fraction interval for {observation.observation_id}: [{lo}, {hi}]"
        )
    if lo >= 0.95:
        return VisibilityState.FULLY_VISIBLE
    if lo > 0.05 and hi < 0.95:
        return VisibilityState.PARTLY_HIDDEN
    if hi <= 0.05:
        if observation.frame_boundary_crossing:
            return VisibilityState.OUT_OF_FRAME
        if (
            observation.occluder_ref
            or observation.continuous_track
            or observation.manual_identity_evidence
        ):
            return VisibilityState.FULLY_HIDDEN
    return VisibilityState.UNKNOWN


def validate_visibility_observation(observation: VisibilityObservation) -> None:
    if observation.start_ms < 0 or observation.end_ms <= observation.start_ms:
        raise ValidationError(
            f"invalid VisibilityObservation span {observation.observation_id}"
        )
    derived = classify_visibility_observation(observation)
    if VisibilityState(observation.state) is not derived:
        raise ValidationError(
            f"visibility label {observation.state.value!r} conflicts with rubric-derived "
            f"state {derived.value!r} for {observation.observation_id}"
        )


def validate_terminal_predicate(predicate: TerminalPredicate) -> None:
    if predicate.predicate_type != "disappears_for_good":
        raise ValidationError(f"unsupported terminal predicate: {predicate.predicate_type!r}")
    if predicate.verification_status is not VerificationStatus.VERIFIED:
        raise ValidationError(f"terminal predicate {predicate.predicate_id} is not verified")
    if predicate.holds_from_ms < 0 or predicate.verified_through_ms != predicate.clip_end_ms:
        raise ValidationError(
            f"terminal predicate {predicate.predicate_id} must be verified through clip end"
        )
    if predicate.holds_from_ms > predicate.clip_end_ms:
        raise ValidationError(f"terminal predicate {predicate.predicate_id} starts after clip end")
    if not predicate.evidence_refs or predicate.provenance is None:
        raise ValidationError(
            f"terminal predicate {predicate.predicate_id} lacks evidence/provenance"
        )


def validate_identity_certificate(
    certificate: IdentityCertificate,
    entity: EntityRef,
    *,
    evidence_ids: Sequence[str] = (),
) -> None:
    if certificate.entity_ref != entity.entity_id:
        raise ValidationError("identity certificate entity does not match EntityRef")
    validate_identity_scope(entity, require_persistent=True)
    if certificate.identity_scope is not IdentityScope.PERSISTENT_ID:
        raise ValidationError("identity certificate must assert persistent_id scope")
    if certificate.ambiguity is not IdentityAmbiguity.NONE:
        raise ValidationError("identity certificate ambiguity must be none")
    if not certificate.manual_oracle_basis:
        raise ValidationError("identity certificate requires manual/oracle basis")
    if not certificate.competitor_inventory_reviewed:
        raise ValidationError("identity certificate requires reviewed competitor inventory")
    if not certificate.reviewer or certificate.provenance is None:
        raise ValidationError("identity certificate requires reviewer and provenance")

    anchors = {anchor.anchor_id: anchor for anchor in entity.identity_anchors if anchor.anchor_id}
    pre = anchors.get(certificate.pre_gap_anchor_id)
    post = anchors.get(certificate.post_gap_anchor_id)
    if pre is None or post is None or pre.t_ms >= post.t_ms:
        raise ValidationError("identity certificate requires ordered pre-gap and post-gap anchors")
    if pre.source_basis is IdentityEvidenceBasis.SUBJECT_LABEL or post.source_basis is IdentityEvidenceBasis.SUBJECT_LABEL:
        raise ValidationError("subject_label cannot certify persistent identity")
    if not certificate.evidence_refs:
        raise ValidationError("identity certificate requires evidence refs")
    missing_evidence = sorted(set(certificate.evidence_refs) - set(evidence_ids))
    if missing_evidence:
        raise ValidationError(f"identity certificate has dangling evidence refs: {missing_evidence}")


def validate_conversion_certificate(certificate: ConversionCertificate) -> None:
    checks = {
        "same_persistent_object": certificate.same_persistent_object,
        "same_state_key": certificate.same_state_key,
        "explicit_before_after": certificate.explicit_before_after,
        "explicit_operator_type": certificate.explicit_operator_type,
        "participant_roles_verified": certificate.participant_roles_verified,
        "commit_boundary_verified": certificate.commit_boundary_verified,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValidationError(f"incomplete conversion certificate: {failed}")
    if not certificate.certificate_id or not certificate.reviewer:
        raise ValidationError("conversion certificate requires id and reviewer")
    if not certificate.apply_boundary_id or not certificate.participants.get("affected"):
        raise ValidationError("conversion certificate lacks boundary/affected participant")


def validate_verified_operator_package(ledger: StateLedger, event: EventOperator) -> None:
    if event.verification_status is not VerificationStatus.VERIFIED:
        raise ValidationError(f"EventOperator {event.event_id} is not VERIFIED")
    if not event.conversion_certificate_id:
        raise ValidationError(f"verified EventOperator {event.event_id} lacks conversion certificate")
    certificates = {
        certificate.certificate_id: certificate
        for certificate in ledger.conversion_certificates
    }
    certificate = certificates.get(event.conversion_certificate_id)
    if certificate is None:
        raise ValidationError(
            f"verified EventOperator {event.event_id} has missing conversion certificate"
        )
    validate_conversion_certificate(certificate)
    if certificate.apply_boundary_id != event.apply_boundary_id:
        raise ValidationError("operator/certificate apply boundary mismatch")
    boundaries = {boundary.boundary_id: boundary for boundary in ledger.boundaries}
    boundary = boundaries.get(event.apply_boundary_id or "")
    if boundary is None:
        raise ValidationError(f"verified EventOperator {event.event_id} has missing boundary")
    affected = event.participants.get("affected")
    if affected != certificate.participants.get("affected") or affected != event.object_id:
        raise ValidationError("operator/certificate affected participant mismatch")
    if boundary.entity_ref != affected or boundary.state_key != event.variable:
        raise ValidationError("operator boundary does not match affected state variable")
    evidence_ids = {span.span_id for span in ledger.evidence_spans if span.span_id}
    missing_evidence = sorted(set(event.evidence_refs) - evidence_ids)
    if missing_evidence:
        raise ValidationError(f"operator has dangling evidence refs: {missing_evidence}")


def validate_query_package(query: QuerySpec, ledger: StateLedger) -> None:
    validate_query_applicability(query)
    status = EventPresuppositionStatus(query.event_presupposition_status)
    applied_ids = {event.event_id for event in ledger.events}
    if status is EventPresuppositionStatus.OBSERVED:
        missing = sorted(set(query.proof_requirements.required_event_ids) - applied_ids)
        if missing:
            raise ValidationError(f"query proof has missing applied events: {missing}")
    evidence_ids = {span.span_id for span in ledger.evidence_spans if span.span_id}
    dangling = sorted(set(query.presupposition_evidence_refs) - evidence_ids)
    if dangling:
        raise ValidationError(f"query has dangling presupposition evidence: {dangling}")
    if query.proof_requirements.identity_dependent:
        entities = {entity.entity_id: entity for entity in ledger.entities}
        certificates = {certificate.entity_ref: certificate for certificate in ledger.identity_certificates}
        for entity_id in query.target_entity_ids:
            entity = entities.get(entity_id)
            certificate = certificates.get(entity_id)
            if entity is None or certificate is None:
                raise ValidationError(f"identity-dependent query lacks certified entity {entity_id!r}")
            validate_identity_certificate(
                certificate,
                entity,
                evidence_ids=tuple(evidence_ids),
            )


def validate_corruption_package(
    spec: CorruptionSpec,
    query: QuerySpec,
    ledger: StateLedger,
) -> None:
    validate_corruption_spec(spec)
    validate_query_package(query, ledger)
    if query.event_presupposition_status is not EventPresuppositionStatus.OBSERVED:
        raise ValidationError("corruption requires observed event presupposition")
    if spec.corruption_type == "transition_drop":
        if not query.metric_applicability.transition_drop:
            raise ValidationError("transition_drop is not enabled for this query")
        illegal = sorted(
            set(spec.target_ids) - set(query.proof_requirements.required_event_ids)
        )
        if illegal:
            raise ValidationError(f"transition_drop targets non-required events: {illegal}")
        return
    if not query.metric_applicability.object_id_swap:
        raise ValidationError("object_id_swap is not enabled for this query")
    if not query.proof_requirements.identity_dependent:
        raise ValidationError("object_id_swap requires identity-dependent query")
    if len(spec.target_ids) != 2 or len(set(spec.target_ids)) != 2:
        raise ValidationError("object_id_swap requires two distinct certified IDs")
    entities = {entity.entity_id: entity for entity in ledger.entities}
    targets = [entities.get(entity_id) for entity_id in spec.target_ids]
    if any(entity is None for entity in targets):
        raise ValidationError("object_id_swap target is missing from entity package")
    if len({entity.entity_type for entity in targets if entity is not None}) != 1:
        raise ValidationError("object_id_swap requires same-class instances")
    certified = {certificate.entity_ref for certificate in ledger.identity_certificates}
    if not set(spec.target_ids).issubset(certified):
        raise ValidationError("object_id_swap targets must both have identity certificates")


def validate_no_answer_access(payload: Any) -> None:
    """Reject gold-answer material from builder/compiler/executor inputs."""

    forbidden = {
        "answer",
        "gold_answer",
        "gold_answer_normalized",
        "gt_answer",
        "gt_answer_normalized",
        "correct_answer",
        "correct_order",
        "allowed_answers",
    }
    for path, key in _walk_keys(payload):
        if key.lower() in forbidden:
            raise ValidationError(f"answer leakage field at {path}: {key}")


def validate_ledger(ledger: StateLedger) -> None:
    validate_time_spans(ledger.intervals, ledger.boundaries)
    evidence_ids = [span.span_id for span in ledger.evidence_spans if span.span_id]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValidationError("evidence span IDs must be unique")
    evidence_id_set = set(evidence_ids)
    interval_ids = {interval.interval_id for interval in ledger.intervals}
    if len(interval_ids) != len(ledger.intervals):
        raise ValidationError("state interval IDs must be unique")
    boundary_ids = {boundary.boundary_id for boundary in ledger.boundaries}
    if len(boundary_ids) != len(ledger.boundaries):
        raise ValidationError("transition boundary IDs must be unique")
    for boundary in ledger.boundaries:
        dangling = sorted(set(boundary.linked_interval_ids) - interval_ids)
        if dangling:
            raise ValidationError(f"boundary has dangling interval refs: {dangling}")
    for entity in ledger.entities:
        validate_identity_scope(entity)
        for anchor in entity.identity_anchors:
            dangling = sorted(set(anchor.evidence_refs) - evidence_id_set)
            if dangling:
                raise ValidationError(f"identity anchor has dangling evidence refs: {dangling}")
    entities = {entity.entity_id: entity for entity in ledger.entities}
    for certificate in ledger.identity_certificates:
        entity = entities.get(certificate.entity_ref)
        if entity is None:
            raise ValidationError("identity certificate refers to missing entity")
        validate_identity_certificate(certificate, entity, evidence_ids=evidence_ids)
    for observation in ledger.visibility_observations:
        validate_visibility_observation(observation)
        dangling = sorted(set(observation.evidence_refs) - evidence_id_set)
        if dangling:
            raise ValidationError(f"visibility observation has dangling evidence refs: {dangling}")
    for predicate in ledger.terminal_predicates:
        validate_terminal_predicate(predicate)
        dangling = sorted(set(predicate.evidence_refs) - evidence_id_set)
        if dangling:
            raise ValidationError(f"terminal predicate has dangling evidence refs: {dangling}")
    candidates = {candidate.candidate_id: candidate for candidate in ledger.state_change_candidates}
    for certificate in ledger.conversion_certificates:
        validate_conversion_certificate(certificate)
        if certificate.candidate_id and certificate.candidate_id not in candidates:
            raise ValidationError("conversion certificate refers to missing candidate")
        if certificate.apply_boundary_id not in boundary_ids:
            raise ValidationError("conversion certificate refers to missing boundary")
        dangling_intervals = sorted(set(certificate.linked_interval_ids) - interval_ids)
        if dangling_intervals:
            raise ValidationError(
                f"conversion certificate has dangling interval refs: {dangling_intervals}"
            )
        dangling_evidence = sorted(set(certificate.evidence_refs) - evidence_id_set)
        if dangling_evidence:
            raise ValidationError(
                f"conversion certificate has dangling evidence refs: {dangling_evidence}"
            )
    identity_certificate_ids = {
        certificate.certificate_id for certificate in ledger.identity_certificates
    }
    for event in ledger.events:
        validate_operator_signature(event)
        validate_verified_operator_package(ledger, event)
        if (
            event.identity_certificate_id is not None
            and event.identity_certificate_id not in identity_certificate_ids
        ):
            raise ValidationError("operator refers to missing identity certificate")
    applied_boundary_ids = [
        event.apply_boundary_id for event in ledger.events if event.apply_boundary_id is not None
    ]
    if len(applied_boundary_ids) != len(set(applied_boundary_ids)):
        raise ValidationError("one commit boundary cannot certify multiple executable events")
    for event in ledger.rejected_events:
        validate_operator_signature(event)
        if event.verification_status is VerificationStatus.VERIFIED:
            validate_verified_operator_package(ledger, event)
    for correction in ledger.correction_records:
        dangling = sorted(set(correction.evidence_refs) - evidence_id_set)
        if dangling:
            raise ValidationError(f"correction record has dangling evidence refs: {dangling}")
        if correction.gold_correct_before is not None or correction.gold_correct_after is not None:
            raise ValidationError("production correction records cannot contain evaluator-only gold")
        if (
            correction.direction.value == "top_down_hypothesis"
            and correction.decision == "mutate_immutable_observation"
        ):
            raise ValidationError("top-down hypotheses cannot mutate immutable observations")
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
