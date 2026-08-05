"""Symbolic query executor over a T-STEP-v0 state ledger."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple, Union

from .ledger_schema import (
    EvidenceSpan,
    EventPresuppositionStatus,
    LedgerQuery,
    QuerySpec,
    QueryStatus,
    StateLedger,
    StateRecord,
)
from .validators import ValidationError, validate_query_applicability, validate_query_package


@dataclass(frozen=True)
class QueryResult:
    answer: Any
    trace: Tuple[StateRecord, ...] = ()
    evidence: Tuple[EvidenceSpan, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    normalized_answer: Any = None
    status: QueryStatus = QueryStatus.OK
    read_state_record_ids: Tuple[str, ...] = ()
    applied_event_ids: Tuple[str, ...] = ()
    rejected_event_ids: Tuple[str, ...] = ()
    identity_bindings: Mapping[str, str] = field(default_factory=dict)
    event_presupposition_status: EventPresuppositionStatus | None = None


def execute_query(
    ledger: StateLedger,
    query: Union[LedgerQuery, QuerySpec],
) -> QueryResult:
    if isinstance(query, QuerySpec):
        return execute_query_spec(ledger, query)
    if query.query_type == "final_state":
        return _state_query(ledger, query, time=None)
    if query.query_type == "state_at":
        return _state_query(ledger, query, time=query.time)
    if query.query_type == "count_transitions":
        return _count_transitions(ledger, query)
    if query.query_type == "event_order":
        return _event_order(ledger, query)
    if query.query_type == "changed_to":
        return _changed_to(ledger, query)
    if query.query_type == "event_exists":
        return _event_exists(ledger, query)
    raise ValueError(f"unsupported query_type: {query.query_type}")


def execute_query_spec(ledger: StateLedger, query: QuerySpec) -> QueryResult:
    """Execute an answer-blind QuerySpec through the unified presupposition gate."""

    validate_query_applicability(query)
    status = EventPresuppositionStatus(query.event_presupposition_status)
    if status in {
        EventPresuppositionStatus.UNSUPPORTED,
        EventPresuppositionStatus.OUTSIDE_CLIP,
    }:
        return QueryResult(
            answer=None,
            status=QueryStatus.INAPPLICABLE,
            event_presupposition_status=status,
            metadata={"reason_code": query.presupposition_reason_code},
        )
    if status is EventPresuppositionStatus.AMBIGUOUS:
        return QueryResult(
            answer=None,
            status=QueryStatus.UNKNOWN,
            event_presupposition_status=status,
            metadata={"reason_code": query.presupposition_reason_code},
        )
    try:
        validate_query_package(query, ledger)
    except ValidationError as error:
        if "missing applied events" not in str(error):
            raise
        return QueryResult(
            answer=None,
            status=QueryStatus.UNKNOWN,
            event_presupposition_status=status,
            metadata={"reason_code": "required_event_not_applied", "validation_error": str(error)},
        )

    result = execute_query(ledger, _query_spec_to_ledger_query(query))
    return QueryResult(
        **{
            **result.__dict__,
            "event_presupposition_status": status,
        }
    )


def _state_query(ledger: StateLedger, query: LedgerQuery, *, time: float | None) -> QueryResult:
    if query.object_id is None or query.variable is None:
        raise ValueError("state queries require object_id and variable")
    trace = ledger.history(query.object_id, query.variable)
    if time is not None:
        trace = tuple(record for record in trace if record.t <= time)
    if not trace:
        return QueryResult(answer=None, status=QueryStatus.UNKNOWN)
    answer = trace[-1].value
    evidence = tuple(span for record in trace for span in record.evidence)
    return _traced_result(answer, trace, evidence)


def _count_transitions(ledger: StateLedger, query: LedgerQuery) -> QueryResult:
    records = ledger.history(query.object_id or "", query.variable or "")
    if not records:
        return QueryResult(answer=None, status=QueryStatus.UNKNOWN)
    transitions = tuple(record for record in records if record.event_id != "__initial__")
    return _traced_result(len(transitions), transitions)


def _event_order(ledger: StateLedger, query: LedgerQuery) -> QueryResult:
    if len(query.event_ids) != 2:
        raise ValueError("event_order requires exactly two event_ids")
    first = ledger.event(query.event_ids[0])
    second = ledger.event(query.event_ids[1])
    terminal_ids = {predicate.predicate_id for predicate in ledger.terminal_predicates}
    if any(event_id in terminal_ids for event_id in query.event_ids):
        return QueryResult(
            answer=None,
            status=QueryStatus.INAPPLICABLE,
            metadata={"terminal_predicate_order": True},
        )
    if first is None or second is None:
        return QueryResult(
            answer=None,
            status=QueryStatus.UNKNOWN,
            metadata={"missing_event": True},
        )
    first_completion = _completion_interval_ms(ledger, first.event_id)
    second_completion = _completion_interval_ms(ledger, second.event_id)
    if first_completion[1] < second_completion[0]:
        answer = True
    elif second_completion[1] < first_completion[0]:
        answer = False
    else:
        return QueryResult(
            answer=None,
            status=QueryStatus.UNKNOWN,
            applied_event_ids=(first.event_id, second.event_id),
            metadata={
                "completion_intervals_overlap": True,
                "first_completion_ms": first_completion,
                "second_completion_ms": second_completion,
            },
        )
    return QueryResult(
        answer=answer,
        normalized_answer=answer,
        applied_event_ids=(first.event_id, second.event_id),
        metadata={
            "first_completion_ms": first_completion,
            "second_completion_ms": second_completion,
        },
    )


def _changed_to(ledger: StateLedger, query: LedgerQuery) -> QueryResult:
    if query.object_id is None or query.variable is None:
        raise ValueError("changed_to requires object_id and variable")
    trace = tuple(
        record
        for record in ledger.history(query.object_id, query.variable)
        if record.event_id != "__initial__"
    )
    if not trace:
        return QueryResult(answer=None, status=QueryStatus.UNKNOWN)
    return _traced_result(any(record.value == query.value for record in trace), trace)


def _event_exists(ledger: StateLedger, query: LedgerQuery) -> QueryResult:
    if len(query.event_ids) != 1:
        raise ValueError("event_exists requires exactly one event_id")
    event_id = query.event_ids[0]
    exists = ledger.event(event_id) is not None
    return QueryResult(
        answer=exists,
        normalized_answer=exists,
        applied_event_ids=(event_id,) if exists else (),
        rejected_event_ids=(event_id,) if ledger.rejected_event(event_id) is not None else (),
    )


def _completion_interval_ms(ledger: StateLedger, event_id: str) -> Tuple[int, int]:
    event = ledger.event(event_id)
    if event is None:
        raise ValueError(f"unknown applied event: {event_id}")
    if event.apply_boundary_id:
        for boundary in ledger.boundaries:
            if boundary.boundary_id == event.apply_boundary_id:
                return (boundary.lo_ms, boundary.hi_ms)
    end_ms = event.event_span_ms[1] if event.event_span_ms is not None else round(event.t_end * 1000)
    return (end_ms, end_ms)


def _query_spec_to_ledger_query(query: QuerySpec) -> LedgerQuery:
    ast = query.query_ast
    query_type = str(ast.get("operator") or ast.get("query_type") or "")
    if not query_type:
        raise ValueError(f"QuerySpec {query.query_id} lacks query operator")
    raw_event_ids = ast.get("event_ids") or ast.get("target_event_ids") or ()
    if isinstance(raw_event_ids, str):
        raw_event_ids = (raw_event_ids,)
    return LedgerQuery(
        query_type=query_type,
        object_id=(
            str(ast["object_id"])
            if ast.get("object_id") is not None
            else (query.target_entity_ids[0] if query.target_entity_ids else None)
        ),
        variable=str(ast["state_key"]) if ast.get("state_key") is not None else ast.get("variable"),
        time=float(ast["time_sec"]) if ast.get("time_sec") is not None else None,
        event_ids=tuple(str(event_id) for event_id in raw_event_ids),
        value=ast.get("value"),
        parameters=dict(ast.get("parameters") or {}),
    )


def _traced_result(
    answer: Any,
    trace: Tuple[StateRecord, ...],
    evidence: Tuple[EvidenceSpan, ...] = (),
) -> QueryResult:
    applied_event_ids = tuple(
        dict.fromkeys(
            record.event_id
            for record in trace
            if record.event_id != "__initial__"
        )
    )
    return QueryResult(
        answer=answer,
        normalized_answer=answer,
        trace=trace,
        evidence=evidence,
        read_state_record_ids=tuple(
            record.record_id for record in trace if record.record_id is not None
        ),
        applied_event_ids=applied_event_ids,
    )


def parse_question_to_query(question: str) -> LedgerQuery:
    """Placeholder parser for future natural-language routing.

    Phase 0 tests should pass explicit ``LedgerQuery`` objects. The parser is
    intentionally not guessed from free text yet.
    """

    raise NotImplementedError("natural-language query parsing is out of scope for v0 skeleton")
