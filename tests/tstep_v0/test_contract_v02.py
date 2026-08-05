from dataclasses import replace

import pytest

from scripts.tstep_phase0_render_targeted_windows import timestamps
from scripts.tstep_phase0_amend_r2_prompt_fields import amend_roster_prompt_fields
from scripts.tstep_phase0_score_r2_gate import validate_and_score_rows
from scripts.tstep_phase0_select_toc_candidates import candidate_row
from tstep_v0.datasets import LedgerBuildInput, build_ledger
from tstep_v0.corruptions import apply_corruption
from tstep_v0.ledger_schema import (
    CompetingInstance,
    ConversionCertificate,
    CorruptionSpec,
    EntityRef,
    EventOperator,
    EventPresuppositionStatus,
    EvidenceSpan,
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
    QueryStatus,
    RecordKind,
    StateLedger,
    StatePredicate,
    StateRecord,
    TerminalPredicate,
    TransitionBoundary,
    VerificationStatus,
    VisibilityObservation,
    VisibilityState,
)
from tstep_v0.ledger_update import LedgerExecutionError, apply_event_operator
from tstep_v0.metrics import event_recall_at_budget, ledger_query_accuracy, transition_f1
from tstep_v0.query_executor import execute_query
from tstep_v0.sampling import (
    inclusive_timestamps_ms,
    pts_tolerance_ms,
    uniform_frame_indices,
    validate_pts_observation,
)
from tstep_v0.validators import (
    ValidationError,
    validate_corruption_package,
    validate_identity_certificate,
    validate_query_applicability,
    validate_terminal_predicate,
    validate_visibility_observation,
)


PROV = Provenance(source="manual", annotator_id="reviewer-a")


def _toy_event(event_id="e1", before="table", after="shelf"):
    return EventOperator(
        event_id,
        1.0,
        2.0,
        "location",
        "cup_1",
        "location",
        before,
        after,
    )


def _verified_components(event_id="e1", boundary_id="b1", cert_id="c1"):
    boundary = TransitionBoundary(
        boundary_id=boundary_id,
        entity_ref="cup_1",
        state_key="location",
        boundary_kind="completion",
        lo_ms=1900,
        hi_ms=2000,
        provenance=PROV,
    )
    certificate = ConversionCertificate(
        same_persistent_object=True,
        same_state_key=True,
        explicit_before_after=True,
        explicit_operator_type=True,
        participant_roles_verified=True,
        commit_boundary_verified=True,
        operator_type="location",
        participants={"affected": "cup_1"},
        apply_boundary_id=boundary_id,
        reviewer="reviewer-a",
        provenance=PROV,
        certificate_id=cert_id,
        evidence_refs=("ev1",),
    )
    event = EventOperator(
        event_id=event_id,
        t_start=1.0,
        t_end=2.0,
        op_type="location",
        object_id="cup_1",
        variable="location",
        before="table",
        after="shelf",
        participants={"affected": "cup_1"},
        preconditions=(StatePredicate("cup_1", "location", "table"),),
        effects=(StatePredicate("cup_1", "location", "shelf"),),
        event_span_ms=(1000, 2000),
        apply_boundary_id=boundary_id,
        provenance=PROV,
        verification_status=VerificationStatus.VERIFIED,
        evidence_refs=("ev1",),
        conversion_certificate_id=cert_id,
    )
    return boundary, certificate, event


def _observed_query(**overrides):
    values = {
        "query_id": "q1",
        "query_ast": {"operator": "final_state", "state_key": "location"},
        "target_entity_ids": ("cup_1",),
        "expected_answer_type": "short_text",
        "event_presupposition_status": EventPresuppositionStatus.OBSERVED,
        "proof_requirements": ProofRequirements(required_event_ids=("e1",)),
        "metric_applicability": MetricApplicability(transition_f1=True),
        "presupposed_event_refs": ("e1",),
        "presupposition_evidence_refs": ("ev1",),
        "reviewed_span_ms": (0, 2500),
    }
    values.update(overrides)
    return QuerySpec(**values)


def _identity_entity(entity_id):
    return EntityRef(
        entity_id=entity_id,
        entity_type="cup",
        identity_scope=IdentityScope.PERSISTENT_ID,
        identity_ambiguity=IdentityAmbiguity.NONE,
        identity_anchors=(
            IdentityAnchor(
                t_ms=100,
                visibility="visible",
                anchor_id=f"{entity_id}:pre",
                role="pre_gap",
                evidence_refs=("ev-pre",),
                source_basis=IdentityEvidenceBasis.MANUAL_ORACLE,
                provenance=PROV,
            ),
            IdentityAnchor(
                t_ms=900,
                visibility="visible",
                anchor_id=f"{entity_id}:post",
                role="post_gap",
                evidence_refs=("ev-post",),
                source_basis=IdentityEvidenceBasis.MANUAL_ORACLE,
                provenance=PROV,
            ),
        ),
        provenance=PROV,
    )


def _identity_certificate(entity_id, competitor=None):
    competitors = (
        (CompetingInstance(competitor, True, ("ev-pre", "ev-post")),)
        if competitor
        else ()
    )
    return IdentityCertificate(
        certificate_id=f"idcert:{entity_id}",
        entity_ref=entity_id,
        pre_gap_anchor_id=f"{entity_id}:pre",
        post_gap_anchor_id=f"{entity_id}:post",
        competing_instances=competitors,
        identity_scope=IdentityScope.PERSISTENT_ID,
        ambiguity=IdentityAmbiguity.NONE,
        evidence_refs=("ev-pre", "ev-post"),
        reviewer="reviewer-a",
        provenance=PROV,
        manual_oracle_basis=True,
        competitor_inventory_reviewed=True,
    )


def test_unverified_operator_is_rejected_by_production_executor():
    with pytest.raises(LedgerExecutionError, match="requires a VERIFIED"):
        apply_event_operator(StateLedger.from_initial_state({"cup_1": {"location": "table"}}), _toy_event())


def test_unverified_operator_requires_explicit_toy_override():
    ledger = apply_event_operator(
        StateLedger.from_initial_state({"cup_1": {"location": "table"}}),
        _toy_event(),
        allow_unverified_toy=True,
    )
    assert ledger.get_state("cup_1", "location") == "shelf"


def test_failed_precondition_enters_rejected_not_applied_events():
    ledger = apply_event_operator(
        StateLedger.from_initial_state({"cup_1": {"location": "table"}}),
        _toy_event(before="drawer"),
        allow_unverified_toy=True,
    )
    assert ledger.events == ()
    assert [event.event_id for event in ledger.rejected_events] == ["e1"]


def test_verified_operator_missing_package_certificate_is_rejected():
    _, _, event = _verified_components()
    ledger = StateLedger.from_initial_state({"cup_1": {"location": "table"}})
    with pytest.raises(ValidationError, match="missing conversion certificate"):
        apply_event_operator(ledger, event)


def test_complete_verified_operator_package_executes():
    boundary, certificate, event = _verified_components()
    base = StateLedger.from_initial_state({"cup_1": {"location": "table"}})
    ledger = replace(
        base,
        boundaries=(boundary,),
        conversion_certificates=(certificate,),
        evidence_spans=(EvidenceSpan("v", 1.0, 2.0, span_id="ev1"),),
    )
    updated = apply_event_operator(ledger, event)
    assert updated.get_state("cup_1", "location") == "shelf"


def test_state_record_requires_explicit_producer():
    with pytest.raises(ValueError, match="producer must be explicit"):
        StateRecord("cup", "location", "table", 0.0, "__initial__")


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        (EventPresuppositionStatus.UNSUPPORTED, QueryStatus.INAPPLICABLE),
        (EventPresuppositionStatus.OUTSIDE_CLIP, QueryStatus.INAPPLICABLE),
        (EventPresuppositionStatus.AMBIGUOUS, QueryStatus.UNKNOWN),
    ],
)
def test_non_observed_presupposition_gate_never_executes(status, expected):
    query = QuerySpec(
        query_id="q",
        query_ast={"operator": "final_state", "state_key": "location"},
        target_entity_ids=("cup_1",),
        expected_answer_type="short_text",
        event_presupposition_status=status,
        metric_applicability=MetricApplicability(ledger_query_accuracy=False),
        presupposition_reason_code="event_not_certified",
    )
    result = execute_query(StateLedger.from_initial_state({"cup_1": {"location": "table"}}), query)
    assert result.status is expected
    assert result.answer is None


def test_not_required_state_query_executes_without_event():
    query = QuerySpec(
        query_id="q",
        query_ast={"operator": "final_state", "state_key": "location"},
        target_entity_ids=("cup_1",),
        expected_answer_type="short_text",
        event_presupposition_status=EventPresuppositionStatus.NOT_REQUIRED,
    )
    result = execute_query(StateLedger.from_initial_state({"cup_1": {"location": "table"}}), query)
    assert result.status is QueryStatus.OK
    assert result.answer == "table"


def test_observed_query_with_missing_required_event_is_unknown():
    ledger = replace(
        StateLedger.from_initial_state({"cup_1": {"location": "table"}}),
        evidence_spans=(EvidenceSpan("v", 0.0, 2.5, span_id="ev1"),),
    )
    result = execute_query(ledger, _observed_query())
    assert result.status is QueryStatus.UNKNOWN
    assert result.metadata["reason_code"] == "required_event_not_applied"


def test_event_exists_query_must_use_not_required_status():
    with pytest.raises(ValidationError, match="event_exists"):
        validate_query_applicability(
            _observed_query(query_ast={"operator": "event_exists", "event_ids": ["e1"]})
        )


def test_event_order_overlap_returns_unknown_not_false():
    first = _toy_event("e1")
    second = EventOperator("e2", 2.1, 3.0, "location", "cup_1", "location", "shelf", "sink")
    ledger = StateLedger(
        events=(first, second),
        boundaries=(
            TransitionBoundary("b1", "cup_1", "location", "completion", 1900, 2300),
            TransitionBoundary("b2", "cup_1", "location", "completion", 2200, 2500),
        ),
    )
    first = replace(first, apply_boundary_id="b1")
    second = replace(second, apply_boundary_id="b2")
    ledger = replace(ledger, events=(first, second))
    result = execute_query(ledger, LedgerQuery("event_order", event_ids=("e1", "e2")))
    assert result.status is QueryStatus.UNKNOWN
    assert result.answer is None


def test_terminal_predicate_cannot_enter_event_order_metric():
    terminal = TerminalPredicate(
        "terminal:cup",
        "cup_1",
        "disappears_for_good",
        2000,
        3000,
        3000,
        ("ev1",),
        VerificationStatus.VERIFIED,
        PROV,
    )
    result = execute_query(
        StateLedger(terminal_predicates=(terminal,)),
        LedgerQuery("event_order", event_ids=("terminal:cup", "e2")),
    )
    assert result.status is QueryStatus.INAPPLICABLE


@pytest.mark.parametrize(
    "observation",
    [
        VisibilityObservation("v1", "cup", 0, 100, 0.95, 1.0, VisibilityState.FULLY_VISIBLE),
        VisibilityObservation("v2", "cup", 0, 100, 0.1, 0.9, VisibilityState.PARTLY_HIDDEN),
        VisibilityObservation(
            "v3", "cup", 0, 100, 0.0, 0.05, VisibilityState.FULLY_HIDDEN, occluder_ref="box"
        ),
        VisibilityObservation(
            "v4", "cup", 0, 100, 0.0, 0.05, VisibilityState.OUT_OF_FRAME, frame_boundary_crossing=True
        ),
        VisibilityObservation("v5", "cup", 0, 100, 0.04, 0.96, VisibilityState.UNKNOWN),
    ],
)
def test_visibility_rubric_accepts_only_operationally_supported_labels(observation):
    validate_visibility_observation(observation)


def test_fully_hidden_without_identity_or_occlusion_cause_is_unknown():
    observation = VisibilityObservation(
        "v", "cup", 0, 100, 0.0, 0.05, VisibilityState.FULLY_HIDDEN
    )
    with pytest.raises(ValidationError, match="rubric-derived state 'unknown'"):
        validate_visibility_observation(observation)


def test_out_of_frame_requires_geometry_crossing():
    observation = VisibilityObservation(
        "v", "cup", 0, 100, 0.0, 0.05, VisibilityState.OUT_OF_FRAME
    )
    with pytest.raises(ValidationError, match="rubric-derived state 'unknown'"):
        validate_visibility_observation(observation)


def test_terminal_predicate_must_be_verified_through_clip_end():
    predicate = TerminalPredicate(
        "t", "cup", "disappears_for_good", 1000, 1900, 2000, ("ev",), VerificationStatus.VERIFIED, PROV
    )
    with pytest.raises(ValidationError, match="through clip end"):
        validate_terminal_predicate(predicate)


def test_identity_certificate_requires_manual_oracle_and_ordered_anchors():
    entity = _identity_entity("cup_1")
    certificate = replace(_identity_certificate("cup_1"), manual_oracle_basis=False)
    with pytest.raises(ValidationError, match="manual/oracle"):
        validate_identity_certificate(certificate, entity, evidence_ids=("ev-pre", "ev-post"))


def test_complete_identity_certificate_is_accepted():
    validate_identity_certificate(
        _identity_certificate("cup_1"),
        _identity_entity("cup_1"),
        evidence_ids=("ev-pre", "ev-post"),
    )


def test_object_swap_requires_two_same_class_certified_ids():
    entity_a = _identity_entity("cup_a")
    entity_b = _identity_entity("cup_b")
    cert_a = _identity_certificate("cup_a", "cup_b")
    cert_b = _identity_certificate("cup_b", "cup_a")
    ledger = StateLedger(
        entities=(entity_a, entity_b),
        identity_certificates=(cert_a, cert_b),
        evidence_spans=(
            EvidenceSpan("v", 0.0, 0.2, span_id="ev-pre"),
            EvidenceSpan("v", 0.8, 1.0, span_id="ev-post"),
            EvidenceSpan("v", 1.0, 2.0, span_id="ev1"),
        ),
        events=(_toy_event("e1"),),
    )
    query = _observed_query(
        target_entity_ids=("cup_a", "cup_b"),
        proof_requirements=ProofRequirements(required_event_ids=("e1",), identity_dependent=True),
        metric_applicability=MetricApplicability(transition_f1=True, object_id_swap=True),
    )
    spec = CorruptionSpec("swap", "object_id_swap", ("cup_a", "cup_b"), "two certified cups", "DIFFERENT")
    validate_corruption_package(spec, query, ledger)
    result = apply_corruption(ledger, query, spec)
    assert result.ledger is ledger
    assert result.query.target_entity_ids == ("cup_b", "cup_a")
    assert result.query.proof_requirements == query.proof_requirements


def test_object_swap_rejects_single_target():
    with pytest.raises(ValidationError, match="two distinct"):
        validate_corruption_package(
            CorruptionSpec("swap", "object_id_swap", ("cup_a",), "bad", "UNKNOWN"),
            _observed_query(
                target_entity_ids=("cup_a",),
                proof_requirements=ProofRequirements(required_event_ids=("e1",), identity_dependent=True),
                metric_applicability=MetricApplicability(transition_f1=True, object_id_swap=True),
            ),
            StateLedger(
                entities=(_identity_entity("cup_a"),),
                identity_certificates=(_identity_certificate("cup_a"),),
                evidence_spans=(
                    EvidenceSpan("v", 0, 0.2, span_id="ev-pre"),
                    EvidenceSpan("v", 0.8, 1.0, span_id="ev-post"),
                    EvidenceSpan("v", 1, 2, span_id="ev1"),
                ),
                events=(_toy_event("e1"),),
            ),
        )


def test_metrics_return_none_when_gold_or_prediction_is_absent():
    assert event_recall_at_budget([(0.0, 1.0)], []) is None
    assert transition_f1(None, [("cup", "location", "table", "shelf")]) is None
    assert ledger_query_accuracy([], []) is None


def test_query_accuracy_excludes_unknown_and_inapplicable_rows():
    score = ledger_query_accuracy(
        ["sink", "wrong", "wrong"],
        ["sink", "shelf", "table"],
        statuses=[QueryStatus.OK, QueryStatus.UNKNOWN, QueryStatus.INAPPLICABLE],
    )
    assert score == 1.0


def test_production_builder_rejects_full_sample_mapping():
    with pytest.raises(TypeError, match="LedgerBuildInput"):
        build_ledger({"question": {"gt_answer": "sink"}})  # type: ignore[arg-type]


def test_answer_free_build_input_rejects_nested_gold_material():
    with pytest.raises(ValidationError, match="answer leakage"):
        LedgerBuildInput.from_mapping(
            {
                "schema_version": "tstep-deep-annotation-v0.2",
                "sample": {"sample_id": "s", "video_id": "v"},
                "audit": {"gt_answer_normalized": "sink"},
            }
        )


def test_candidate_manifest_projects_only_safe_ordering_prompt_events():
    row = candidate_row(
        {
            "qa_id": "q",
            "video_id": "v",
            "question": "What happens?",
            "format": "ordering_3",
            "events": [
                {"label": "A", "event_text": "it enters", "chronological_index": 2},
                {"label": "B", "event_text": "it leaves", "chronological_index": 0},
                {"label": "C", "event_text": "it reappears", "chronological_index": 1},
            ],
            "correct_order": ["B", "C", "A"],
            "metadata": {
                "dim": "event_ordering",
                "tier": "tier1",
                "subject_label": "cup",
                "has_hallucination_distractor": False,
            },
        }
    )
    assert "events" not in row["question"]
    assert row["question"]["query_event_descriptions"] == [
        {"label": "A", "event_text": "it enters"},
        {"label": "B", "event_text": "it leaves"},
        {"label": "C", "event_text": "it reappears"},
    ]
    assert "correct_order" not in str(row)
    assert "chronological_index" not in str(row)


def test_non_ordering_candidate_never_copies_raw_events():
    row = candidate_row(
        {
            "qa_id": "q",
            "video_id": "v",
            "question": "What happens?",
            "format": "sp",
            "allowed_answers": ["A", "B"],
            "events": [{"answer_derived": True}],
            "metadata": {
                "dim": "reappear_or_disappear",
                "tier": "tier1",
                "subject_label": "cup",
                "has_hallucination_distractor": False,
            },
        }
    )
    assert "query_event_descriptions" not in row["question"]


def test_r2_prompt_amendment_changes_only_three_ordering_questions():
    roster = [
        {
            "sample_id": f"TOC-Bench:phase0:v{i}:q{i}",
            "question": {"qa_id": f"q{i}", "text": "order", "format": "ordering_3", "choices": []},
            "source_metadata": {"dim": "event_ordering"},
        }
        for i in range(3)
    ] + [
        {
            "sample_id": "TOC-Bench:phase0:v3:q3",
            "question": {"qa_id": "q3", "text": "identity", "format": "sp", "choices": ["A", "B"]},
            "source_metadata": {"dim": "reappear_identity"},
        }
    ]
    source = [
        {
            "video_id": f"v{i}",
            "qa_id": f"q{i}",
            "format": "ordering_3",
            "events": [
                {"label": "A", "event_text": "one", "chronological_index": 2},
                {"label": "B", "event_text": "two", "chronological_index": 0},
                {"label": "C", "event_text": "three", "chronological_index": 1},
            ],
            "correct_order": ["B", "C", "A"],
        }
        for i in range(3)
    ]
    amended, changes = amend_roster_prompt_fields(roster, source)
    assert [row["sample_id"] for row in amended] == [row["sample_id"] for row in roster]
    assert len(changes) == 3
    assert "query_event_descriptions" not in amended[3]["question"]
    assert "correct_order" not in str(amended)


def test_targeted_sampling_rejects_zero_length_without_explicit_single_frame():
    with pytest.raises(ValueError, match="zero-length"):
        timestamps(1.0, 1.0, 0.1)
    assert inclusive_timestamps_ms(1000, 1000, 100, allow_single_frame=True) == [1000]


def test_targeted_sampling_always_includes_exact_end_and_dense_endpoints():
    assert timestamps(0.0, 1.0, 0.3) == [0.0, 0.3, 0.6, 0.9, 1.0]
    indices = uniform_frame_indices(101, 24)
    assert len(indices) == 24
    assert indices[0] == 0 and indices[-1] == 100


def test_pts_validation_rejects_nonmonotonic_or_implausibly_scaled_decoder_values():
    assert validate_pts_observation(
        1000, 1000, previous_actual_pts_ms=900, fps=25.0
    ) == 0
    assert pts_tolerance_ms(25.0) == 80
    with pytest.raises(ValueError, match="monotonic"):
        validate_pts_observation(800, 800, previous_actual_pts_ms=900, fps=25.0)
    with pytest.raises(ValueError, match="beyond tolerance"):
        validate_pts_observation(1, 1000, previous_actual_pts_ms=0, fps=25.0)


def test_r2_gate_requires_all_three_thresholds():
    expected = []
    rows = []
    dimensions = ["event_ordering"] * 3 + ["cross_object_order"] * 2 + ["reappear_identity"] * 3 + ["reappear_or_disappear"] * 2
    accepted_indices = {0, 1, 3, 5, 8, 9}
    for index, dimension in enumerate(dimensions):
        sample_id = f"s{index}"
        expected.append({"sample_id": sample_id, "dimension": dimension})
        accepted = index in accepted_indices
        rows.append(
            {
                "sample_id": sample_id,
                "dimension": dimension,
                "cohort": "event_order_sensitive" if index < 5 else "identity_visibility_sensitive",
                "decision": "accepted" if accepted else "blocked",
                "event_presupposition_status": "observed" if accepted else "unsupported",
            }
        )
    score = validate_and_score_rows(rows, expected)
    assert score["overall"]["accepted"] == 6
    assert score["event_order_sensitive"]["accepted"] == 3
    assert score["identity_visibility_sensitive"]["accepted"] == 3
    assert score["gate_passed"] is False
