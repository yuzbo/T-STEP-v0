from tstep_v0.ledger_schema import EventOperator, LedgerQuery, StateLedger
from tstep_v0.ledger_update import apply_event_operators
from tstep_v0.query_executor import execute_query


def _toy_ledger():
    ledger = StateLedger.from_initial_state({"cup": {"location": "table"}})
    return apply_event_operators(
        ledger,
        [
            EventOperator("e1", 1.0, 2.0, "location", "cup", "location", "table", "shelf"),
            EventOperator("e2", 3.0, 4.0, "location", "cup", "location", "shelf", "sink"),
        ],
        allow_unverified_toy=True,
    )


def test_final_state_query_returns_answer_and_trace_from_ledger():
    result = execute_query(
        _toy_ledger(),
        LedgerQuery("final_state", object_id="cup", variable="location"),
    )

    assert result.answer == "sink"
    assert result.trace[-1].event_id == "e2"


def test_state_at_query_uses_time_index():
    result = execute_query(
        _toy_ledger(),
        LedgerQuery("state_at", object_id="cup", variable="location", time=2.5),
    )

    assert result.answer == "shelf"


def test_event_order_query_compares_event_times():
    result = execute_query(
        _toy_ledger(),
        LedgerQuery("event_order", event_ids=("e1", "e2")),
    )

    assert result.answer is True
