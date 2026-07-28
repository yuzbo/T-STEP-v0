"""ECTok v0: budgeted event-complete token selection helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Sequence, Tuple


@dataclass(frozen=True)
class EventToken:
    token_id: str
    start: float
    end: float
    score: float
    object_ids: Tuple[str, ...] = ()
    features: Mapping[str, float] = field(default_factory=dict)


class EventCompleteTokenizer:
    """Select top-scoring candidate event spans under a fixed budget."""

    def select(
        self,
        candidates: Sequence[EventToken],
        *,
        budget: int,
    ) -> Tuple[EventToken, ...]:
        if budget < 0:
            raise ValueError("budget must be non-negative")
        ranked = sorted(candidates, key=lambda token: (-token.score, token.start, token.token_id))
        selected = ranked[:budget]
        return tuple(sorted(selected, key=lambda token: (token.start, token.end, token.token_id)))


def oracle_event_selector(
    candidates: Sequence[EventToken],
    gold_token_ids: Sequence[str],
    *,
    budget: int,
) -> Tuple[EventToken, ...]:
    gold = set(gold_token_ids)
    ranked = sorted(
        candidates,
        key=lambda token: (token.token_id not in gold, -token.score, token.start, token.token_id),
    )
    return tuple(sorted(ranked[:budget], key=lambda token: (token.start, token.end, token.token_id)))
