"""Typed object-state transition ledger schema for T-STEP-v0.

The schema is intentionally small and deterministic. It is a Phase 0/1 harness
surface, not a model-training implementation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence, Tuple


class IdentityScope(str, Enum):
    SEMANTIC_LABEL = "semantic_label"
    TRACKER_ID = "tracker_id"
    PERSISTENT_ID = "persistent_id"


class IdentityAmbiguity(str, Enum):
    NONE = "none"
    PARTIAL = "partial"
    UNRESOLVED = "unresolved"


class RecordKind(str, Enum):
    INITIAL = "initial"
    OBSERVED = "observed"
    DERIVED = "derived"


class QueryStatus(str, Enum):
    OK = "OK"
    UNKNOWN = "UNKNOWN"
    UNDEFINED = "UNDEFINED"
    INAPPLICABLE = "INAPPLICABLE"


class EventPresuppositionStatus(str, Enum):
    OBSERVED = "observed"
    UNSUPPORTED = "unsupported"
    AMBIGUOUS = "ambiguous"
    OUTSIDE_CLIP = "outside_clip"
    NOT_REQUIRED = "not_required"


class VisibilityState(str, Enum):
    FULLY_VISIBLE = "fully_visible"
    PARTLY_HIDDEN = "partly_hidden"
    FULLY_HIDDEN = "fully_hidden"
    OUT_OF_FRAME = "out_of_frame"
    UNKNOWN = "unknown"


class IdentityEvidenceBasis(str, Enum):
    SUBJECT_LABEL = "subject_label"
    UNIQUE_APPEARANCE_REVIEW = "unique_appearance_review"
    TRACKER_CONTINUOUS = "tracker_continuous"
    MANUAL_ORACLE = "manual_oracle"


class CorrectionDirection(str, Enum):
    BOTTOM_UP_VETO = "bottom_up_veto"
    TOP_DOWN_HYPOTHESIS = "top_down_hypothesis"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    METADATA_ONLY = "metadata_only"


@dataclass(frozen=True)
class Provenance:
    source: str
    annotator_id: Optional[str] = None
    artifact_ref: Optional[str] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvidenceSpan:
    video_id: str
    start: float
    end: float
    object_ids: Tuple[str, ...] = ()
    score: float = 1.0
    span_id: Optional[str] = None


@dataclass(frozen=True)
class Uncertainty:
    confidence: float = 1.0
    source: str = "unknown"


@dataclass(frozen=True)
class ObjectState:
    object_id: str
    variables: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RelationState:
    subject_id: str
    relation: str
    object_id: str
    value: Any
    confidence: float = 1.0


@dataclass(frozen=True)
class IdentityAnchor:
    t_ms: int
    visibility: str
    bbox_xyxy: Optional[Tuple[float, float, float, float]] = None
    reference: Optional[str] = None
    anchor_id: Optional[str] = None
    role: Optional[str] = None
    evidence_refs: Tuple[str, ...] = ()
    source_basis: IdentityEvidenceBasis = IdentityEvidenceBasis.SUBJECT_LABEL
    provenance: Optional[Provenance] = None


@dataclass(frozen=True)
class CompetingInstance:
    entity_ref: str
    same_class: bool
    evidence_refs: Tuple[str, ...] = ()
    excluded_by: Optional[str] = None


@dataclass(frozen=True)
class IdentityCertificate:
    certificate_id: str
    entity_ref: str
    pre_gap_anchor_id: str
    post_gap_anchor_id: str
    competing_instances: Tuple[CompetingInstance, ...] = ()
    identity_scope: IdentityScope = IdentityScope.PERSISTENT_ID
    ambiguity: IdentityAmbiguity = IdentityAmbiguity.UNRESOLVED
    evidence_refs: Tuple[str, ...] = ()
    reviewer: str = ""
    provenance: Optional[Provenance] = None
    manual_oracle_basis: bool = False
    competitor_inventory_reviewed: bool = False


@dataclass(frozen=True)
class EntityRef:
    entity_id: str
    entity_type: str
    identity_scope: IdentityScope = IdentityScope.SEMANTIC_LABEL
    subject_label: Optional[str] = None
    identity_anchors: Tuple[IdentityAnchor, ...] = ()
    identity_ambiguity: IdentityAmbiguity = IdentityAmbiguity.UNRESOLVED
    provenance: Optional[Provenance] = None


@dataclass(frozen=True)
class StateInterval:
    """Observed state assertion on a half-open PTS interval.

    This is observational evidence. It is never an executable operator.
    """

    interval_id: str
    entity_ref: str
    state_key: str
    typed_value: Any
    start_ms: int
    end_ms: int
    observation_status: str = "observed"
    source: str = "manual"
    provenance: Optional[Provenance] = None


@dataclass(frozen=True)
class VisibilityObservation:
    """Manual discrete visibility label plus interval-valued visual evidence."""

    observation_id: str
    entity_ref: str
    start_ms: int
    end_ms: int
    visible_fraction_lo: float
    visible_fraction_hi: float
    state: VisibilityState
    occluder_ref: Optional[str] = None
    continuous_track: bool = False
    manual_identity_evidence: bool = False
    frame_boundary_crossing: bool = False
    evidence_refs: Tuple[str, ...] = ()
    provenance: Optional[Provenance] = None


@dataclass(frozen=True)
class TransitionBoundary:
    """Temporal constraint on a state change, without causal semantics."""

    boundary_id: str
    entity_ref: str
    state_key: str
    boundary_kind: str
    lo_ms: int
    hi_ms: int
    linked_interval_ids: Tuple[str, ...] = ()
    source: str = "manual"
    provenance: Optional[Provenance] = None


@dataclass(frozen=True)
class TerminalPredicate:
    """Clip-terminal assertion; never an executable EventOperator."""

    predicate_id: str
    entity_ref: str
    predicate_type: str
    holds_from_ms: int
    verified_through_ms: int
    clip_end_ms: int
    evidence_refs: Tuple[str, ...] = ()
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    provenance: Optional[Provenance] = None


@dataclass(frozen=True)
class StatePredicate:
    entity_ref: str
    state_key: str
    typed_value: Any


@dataclass(frozen=True)
class EventOperator:
    """Executable transition.

    The leading fields preserve the v0 toy constructor. ``participants``,
    ``preconditions`` and ``effects`` are the authoritative typed execution
    view; legacy object/variable/before/after fields are adapted into that view.
    """

    event_id: str
    t_start: float
    t_end: float
    op_type: str
    object_id: str
    variable: str
    before: Any = None
    after: Any = None
    target_object_id: Optional[str] = None
    confidence: float = 1.0
    evidence: Tuple[EvidenceSpan, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    participants: Mapping[str, str] = field(default_factory=dict)
    preconditions: Tuple[StatePredicate, ...] = ()
    effects: Tuple[StatePredicate, ...] = ()
    event_span_ms: Optional[Tuple[int, int]] = None
    apply_boundary_id: Optional[str] = None
    source: str = "decoder"
    provenance: Optional[Provenance] = None
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    evidence_refs: Tuple[str, ...] = ()
    conversion_certificate_id: Optional[str] = None
    identity_certificate_id: Optional[str] = None

    def __post_init__(self) -> None:
        if self.verification_status is VerificationStatus.VERIFIED:
            if not self.participants or not self.preconditions or not self.effects:
                raise ValueError(
                    "verified EventOperator requires explicit participants, preconditions, and effects"
                )
            if self.event_span_ms is None:
                raise ValueError("verified EventOperator requires an explicit PTS-ms event span")
            return
        if not self.participants:
            object.__setattr__(self, "participants", {"affected": self.object_id})
        if not self.preconditions and self.before is not None:
            object.__setattr__(
                self,
                "preconditions",
                (StatePredicate(self.object_id, self.variable, self.before),),
            )
        if not self.effects:
            object.__setattr__(
                self,
                "effects",
                (StatePredicate(self.object_id, self.variable, self.after),),
            )
        if self.event_span_ms is None:
            object.__setattr__(
                self,
                "event_span_ms",
                (round(self.t_start * 1000), round(self.t_end * 1000)),
            )


@dataclass(frozen=True)
class StateRecord:
    object_id: str
    variable: str
    value: Any
    t: float
    event_id: str
    confidence: float = 1.0
    evidence: Tuple[EvidenceSpan, ...] = ()
    record_id: Optional[str] = None
    valid_from_ms: Optional[int] = None
    valid_to_ms: Optional[int] = None
    producer: Optional[str] = None
    record_kind: RecordKind = RecordKind.DERIVED
    source: str = "executor"
    provenance: Optional[Provenance] = None

    def __post_init__(self) -> None:
        if not self.producer:
            raise ValueError("StateRecord producer must be explicit")
        producer = self.producer
        if self.record_id is None:
            object.__setattr__(
                self,
                "record_id",
                f"{producer}:{self.object_id}:{self.variable}:{self.t}",
            )
        if self.valid_from_ms is None and math.isfinite(self.t):
            object.__setattr__(self, "valid_from_ms", round(self.t * 1000))


@dataclass(frozen=True)
class ConflictRecord:
    event_id: str
    object_id: str
    variable: str
    expected: Any
    actual: Any
    message: str


@dataclass(frozen=True)
class LedgerQuery:
    query_type: str
    object_id: Optional[str] = None
    variable: Optional[str] = None
    time: Optional[float] = None
    event_ids: Tuple[str, ...] = ()
    value: Any = None
    parameters: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MetricApplicability:
    state_acc: bool = False
    transition_f1: bool = False
    ledger_query_accuracy: bool = True
    transition_drop: bool = False
    object_id_swap: bool = False


@dataclass(frozen=True)
class ProofRequirements:
    required_event_ids: Tuple[str, ...] = ()
    required_state_record_ids: Tuple[str, ...] = ()
    identity_dependent: bool = False


@dataclass(frozen=True)
class QuerySpec:
    """Answer-blind executable query package."""

    query_id: str
    query_ast: Mapping[str, Any]
    target_entity_ids: Tuple[str, ...]
    expected_answer_type: str
    event_presupposition_status: EventPresuppositionStatus
    proof_requirements: ProofRequirements = field(default_factory=ProofRequirements)
    metric_applicability: MetricApplicability = field(default_factory=MetricApplicability)
    question_text: Optional[str] = None
    presupposed_event_refs: Tuple[str, ...] = ()
    presupposition_evidence_refs: Tuple[str, ...] = ()
    reviewed_span_ms: Optional[Tuple[int, int]] = None
    presupposition_reason_code: Optional[str] = None


@dataclass(frozen=True)
class CorruptionSpec:
    corruption_id: str
    corruption_type: str
    target_ids: Tuple[str, ...]
    eligibility_reason: str
    expected_relation_to_clean: str
    expected_corrupted_answer: Any = None
    validator_version: str = "tstep-corruption-v0.2"


@dataclass(frozen=True)
class StateChangeCandidate:
    candidate_id: str
    entity_ref: str
    state_key: str
    before_value: Any
    after_value: Any
    transition_span_ms: Tuple[int, int]
    linked_interval_ids: Tuple[str, ...]
    source: str
    verification_status: VerificationStatus = VerificationStatus.METADATA_ONLY


@dataclass(frozen=True)
class ConversionCertificate:
    same_persistent_object: bool
    same_state_key: bool
    explicit_before_after: bool
    explicit_operator_type: bool
    participant_roles_verified: bool
    commit_boundary_verified: bool
    operator_type: str
    participants: Mapping[str, str]
    apply_boundary_id: str
    reviewer: str
    provenance: Provenance
    certificate_id: str
    candidate_id: Optional[str] = None
    linked_interval_ids: Tuple[str, ...] = ()
    evidence_refs: Tuple[str, ...] = ()
    identity_certificate_id: Optional[str] = None


@dataclass(frozen=True)
class CorrectionRecord:
    correction_id: str
    direction: CorrectionDirection
    before_hypothesis: Any
    proposed_hypothesis: Any
    final_hypothesis: Any
    evidence_refs: Tuple[str, ...]
    affected_layers: Tuple[str, ...]
    consistency_before: bool
    consistency_after: bool
    decision: str
    provenance: Provenance
    gold_correct_before: Optional[bool] = None
    gold_correct_after: Optional[bool] = None


@dataclass(frozen=True)
class StateLedger:
    records: Tuple[StateRecord, ...] = ()
    events: Tuple[EventOperator, ...] = ()
    rejected_events: Tuple[EventOperator, ...] = ()
    conflicts: Tuple[ConflictRecord, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
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

    @classmethod
    def from_initial_state(
        cls,
        initial_state: Mapping[str, Mapping[str, Any]],
        *,
        t: float = float("-inf"),
    ) -> "StateLedger":
        records = []
        for object_id, variables in initial_state.items():
            for variable, value in variables.items():
                records.append(
                    StateRecord(
                        object_id=object_id,
                        variable=variable,
                        value=value,
                        t=t,
                        event_id="__initial__",
                        producer="__initial__",
                        record_kind=RecordKind.INITIAL,
                        source="initial_state",
                    )
                )
        return cls(records=tuple(records))

    def with_record(self, record: StateRecord, event: EventOperator) -> "StateLedger":
        return replace(
            self,
            records=self.records + (record,),
            events=self.events + (event,),
        )

    def with_records(
        self,
        records: Sequence[StateRecord],
        event: EventOperator,
    ) -> "StateLedger":
        return replace(
            self,
            records=self.records + tuple(records),
            events=self.events + (event,),
        )

    def with_conflict(self, conflict: ConflictRecord, event: EventOperator) -> "StateLedger":
        return replace(
            self,
            rejected_events=self.rejected_events + (event,),
            conflicts=self.conflicts + (conflict,),
        )

    def with_conflicts(
        self,
        conflicts: Sequence[ConflictRecord],
        event: EventOperator,
    ) -> "StateLedger":
        return replace(
            self,
            rejected_events=self.rejected_events + (event,),
            conflicts=self.conflicts + tuple(conflicts),
        )

    @property
    def applied_events(self) -> Tuple[EventOperator, ...]:
        """Explicit v0.2 name; ``events`` remains the compatibility alias."""

        return self.events

    def history(self, object_id: str, variable: str) -> Tuple[StateRecord, ...]:
        rows = [
            record
            for record in self.records
            if record.object_id == object_id and record.variable == variable
        ]
        return tuple(sorted(rows, key=lambda record: record.t))

    def get_state(
        self,
        object_id: str,
        variable: str,
        *,
        time: Optional[float] = None,
        default: Any = None,
    ) -> Any:
        candidates = self.history(object_id, variable)
        if time is not None:
            candidates = tuple(record for record in candidates if record.t <= time)
        if not candidates:
            return default
        return candidates[-1].value

    def record_at(
        self,
        object_id: str,
        variable: str,
        *,
        time: Optional[float] = None,
    ) -> Optional[StateRecord]:
        candidates = self.history(object_id, variable)
        if time is not None:
            candidates = tuple(record for record in candidates if record.t <= time)
        return candidates[-1] if candidates else None

    def event(self, event_id: str) -> Optional[EventOperator]:
        for event in self.events:
            if event.event_id == event_id:
                return event
        return None

    def rejected_event(self, event_id: str) -> Optional[EventOperator]:
        for event in self.rejected_events:
            if event.event_id == event_id:
                return event
        return None

    def object_ids(self) -> Tuple[str, ...]:
        return tuple(sorted({record.object_id for record in self.records}))

    def variables_for(self, object_id: str) -> Tuple[str, ...]:
        return tuple(
            sorted(
                {
                    record.variable
                    for record in self.records
                    if record.object_id == object_id
                }
            )
        )


def make_ledger(initial_state: Mapping[str, Mapping[str, Any]]) -> StateLedger:
    return StateLedger.from_initial_state(initial_state)


def ensure_events(events: Iterable[EventOperator]) -> Tuple[EventOperator, ...]:
    return tuple(events)
