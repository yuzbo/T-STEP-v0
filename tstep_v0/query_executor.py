"""Symbolic query executor over a T-STEP-v0 state ledger."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Tuple

from .ledger_schema import (
    EvidenceSpan,
    LedgerQuery,
    QueryStatus,
    StateLedger,
    StateRecord,
)


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
    identity_bindings: Mapping[str, str] = field(default_factory=dict)


def execute_query(ledger: StateLedger, query: LedgerQuery) -> QueryResult:
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
    raise ValueError(f"unsupported query_type: {query.query_type}")


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
    if first is None or second is None:
        return QueryResult(
            answer=None,
            status=QueryStatus.UNKNOWN,
            metadata={"missing_event": True},
        )
    return QueryResult(
        answer=first.t_start < second.t_start,
        normalized_answer=first.t_start < second.t_start,
        applied_event_ids=(first.event_id, second.event_id),
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
