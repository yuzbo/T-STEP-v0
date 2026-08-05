"""Contract-validated Phase 0 corruptions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping, Tuple

from .ledger_schema import CorruptionSpec, QuerySpec, RecordKind, StateLedger
from .ledger_update import apply_event_operators
from .validators import validate_corruption_package


@dataclass(frozen=True)
class CorruptionResult:
    ledger: StateLedger
    query: QuerySpec
    identity_bindings: Mapping[str, str]
    removed_event_ids: Tuple[str, ...] = ()


def apply_corruption(
    ledger: StateLedger,
    query: QuerySpec,
    spec: CorruptionSpec,
) -> CorruptionResult:
    """Apply only a corruption that passed full query/package eligibility checks."""

    validate_corruption_package(spec, query, ledger)
    if spec.corruption_type == "transition_drop":
        removed = set(spec.target_ids)
        base_records = tuple(
            record
            for record in ledger.records
            if record.record_kind in {RecordKind.INITIAL, RecordKind.OBSERVED}
        )
        base = replace(
            ledger,
            records=base_records,
            events=(),
            rejected_events=(),
            conflicts=(),
        )
        retained = [event for event in ledger.events if event.event_id not in removed]
        corrupted = apply_event_operators(base, retained)
        return CorruptionResult(
            ledger=corrupted,
            query=query,
            identity_bindings={},
            removed_event_ids=tuple(spec.target_ids),
        )

    first, second = spec.target_ids
    bindings = {first: second, second: first}
    corrupted_query = replace(
        query,
        target_entity_ids=tuple(bindings.get(value, value) for value in query.target_entity_ids),
        query_ast=_swap_ids(query.query_ast, bindings),
    )
    return CorruptionResult(
        ledger=ledger,
        query=corrupted_query,
        identity_bindings=bindings,
    )


def _swap_ids(value: Any, bindings: Mapping[str, str]) -> Any:
    if isinstance(value, str):
        return bindings.get(value, value)
    if isinstance(value, Mapping):
        return {key: _swap_ids(item, bindings) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_swap_ids(item, bindings) for item in value)
    if isinstance(value, list):
        return [_swap_ids(item, bindings) for item in value]
    return value
