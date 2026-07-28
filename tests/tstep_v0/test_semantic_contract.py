import pytest

import tstep_v0.conversion as conversion
from tstep_v0.conversion import (
    candidate_to_event_operator,
    interval_triplet_to_state_change_candidate,
    state_interval_to_observed_record,
)
from tstep_v0.ledger_schema import (
    ConversionCertificate,
    EntityRef,
    EventOperator,
    IdentityAnchor,
    IdentityScope,
    MetricApplicability,
    ProofRequirements,
    Provenance,
    QuerySpec,
    QueryStatus,
    RecordKind,
    StateInterval,
    StateLedger,
    StateRecord,
)
from tstep_v0.ledger_update import LedgerExecutionError, apply_event_operator
from tstep_v0.query_executor import execute_query
from tstep_v0.ledger_schema import LedgerQuery
from tstep_v0.validators import (
    ValidationError,
    validate_identity_scope,
    validate_no_answer_access,
    validate_no_orphan_records,
    validate_query_applicability,
    validate_time_spans,
)


def _interval(
    interval_id: str,
    value: str,
    start_ms: int,
    end_ms: int,
) -> StateInterval:
    return StateInterval(
        interval_id=interval_id,
        entity_ref="cup_1",
        state_key="location",
        typed_value=value,
        start_ms=start_ms,
        end_ms=end_ms,
        provenance=Provenance(source="manual"),
    )


def test_state_interval_is_observation_not_automatic_operator():
    interval = _interval("i0", "table", 0, 1000)

    record = state_interval_to_observed_record(interval)

    assert record.record_kind is RecordKind.OBSERVED
    assert record.producer == "observation:i0"
    assert not hasattr(conversion, "interval_to_event_operator")


def test_interval_triplet_only_becomes_operator_with_complete_certificate():
    candidate = interval_triplet_to_state_change_candidate(
        _interval("before", "table", 0, 1000),
        _interval("transition", "moving", 1000, 2000),
        _interval("after", "shelf", 2000, 3000),
    )
    incomplete = ConversionCertificate(
        same_persistent_object=True,
        same_state_key=True,
        explicit_before_after=True,
        explicit_operator_type=True,
        participant_roles_verified=True,
        commit_boundary_verified=False,
        operator_type="location",
        participants={"affected": "cup_1"},
        apply_boundary_id="b1",
        reviewer="annotator-a",
        provenance=Provenance(source="manual"),
    )
    with pytest.raises(ValidationError, match="commit_boundary_verified"):
        candidate_to_event_operator(candidate, incomplete)

    complete = ConversionCertificate(
        **{
            **incomplete.__dict__,
            "commit_boundary_verified": True,
        }
    )
    event = candidate_to_event_operator(candidate, complete)

    assert event.effects[0].typed_value == "shelf"
    assert event.apply_boundary_id == "b1"


def test_semantic_label_cannot_satisfy_persistent_identity_query():
    semantic = EntityRef(
        entity_id="cup",
        entity_type="container",
        identity_scope=IdentityScope.SEMANTIC_LABEL,
    )
    with pytest.raises(ValidationError, match="requires persistent_id"):
        validate_identity_scope(semantic, require_persistent=True)

    persistent = EntityRef(
        entity_id="cup_1",
        entity_type="container",
        identity_scope=IdentityScope.PERSISTENT_ID,
        identity_anchors=(
            IdentityAnchor(t_ms=0, visibility="visible", bbox_xyxy=(0, 0, 10, 10)),
            IdentityAnchor(t_ms=2000, visibility="visible", bbox_xyxy=(2, 0, 12, 10)),
        ),
    )
    validate_identity_scope(persistent, require_persistent=True)


def test_answer_fields_are_rejected_from_builder_inputs():
    validate_no_answer_access({"query_ast": {"operator": "final_state"}})
    with pytest.raises(ValidationError, match="answer leakage"):
        validate_no_answer_access(
            {"query_ast": {"operator": "final_state"}, "gold_answer": "sink"}
        )


def test_invalid_half_open_interval_is_rejected():
    with pytest.raises(ValidationError, match="invalid half-open"):
        validate_time_spans((_interval("bad", "table", 1000, 1000),))


def test_missing_state_returns_unknown_not_false():
    result = execute_query(
        StateLedger(),
        LedgerQuery("final_state", object_id="cup_1", variable="location"),
    )

    assert result.status is QueryStatus.UNKNOWN
    assert result.answer is None
    assert result.answer is not False


def test_orphan_derived_record_is_rejected():
    orphan = StateRecord(
        object_id="cup_1",
        variable="location",
        value="shelf",
        t=2.0,
        event_id="missing_event",
        producer="missing_event",
        record_kind=RecordKind.DERIVED,
    )
    with pytest.raises(ValidationError, match="orphan producer"):
        validate_no_orphan_records(StateLedger(records=(orphan,)))


def test_strict_replay_rejects_failed_precondition():
    ledger = StateLedger.from_initial_state({"cup_1": {"location": "table"}})
    invalid = EventOperator(
        "move",
        1.0,
        2.0,
        "location",
        "cup_1",
        "location",
        "drawer",
        "shelf",
    )

    with pytest.raises(LedgerExecutionError, match="expected"):
        apply_event_operator(ledger, invalid, strict=True)


def test_metric_applicability_requires_proof_events_and_identity_dependency():
    bad_transition = QuerySpec(
        query_id="q1",
        query_ast={"operator": "final_state"},
        target_entity_ids=("cup_1",),
        expected_answer_type="short_text",
        metric_applicability=MetricApplicability(transition_f1=True),
    )
    with pytest.raises(ValidationError, match="proof-required"):
        validate_query_applicability(bad_transition)

    good = QuerySpec(
        query_id="q2",
        query_ast={"operator": "final_state"},
        target_entity_ids=("cup_1",),
        expected_answer_type="short_text",
        proof_requirements=ProofRequirements(
            required_event_ids=("move",),
            identity_dependent=True,
        ),
        metric_applicability=MetricApplicability(
            transition_f1=True,
            object_id_swap=True,
        ),
    )
    validate_query_applicability(good)
