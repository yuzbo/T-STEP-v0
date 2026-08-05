from tstep_v0.ledger_schema import EventOperator, StateLedger
from tstep_v0.ledger_update import apply_event_operator, apply_event_operators


def test_apply_event_operator_updates_state_and_keeps_history():
    ledger = StateLedger.from_initial_state({"cup": {"location": "table"}})
    op = EventOperator(
        event_id="e1",
        t_start=1.0,
        t_end=2.0,
        op_type="location",
        object_id="cup",
        variable="location",
        before="table",
        after="shelf",
    )

    updated = apply_event_operator(ledger, op, allow_unverified_toy=True)

    assert updated.get_state("cup", "location") == "shelf"
    assert ledger.get_state("cup", "location") == "table"
    assert [record.value for record in updated.history("cup", "location")] == [
        "table",
        "shelf",
    ]


def test_precondition_mismatch_records_conflict_without_state_change():
    ledger = StateLedger.from_initial_state({"cup": {"location": "table"}})
    op = EventOperator(
        event_id="e_bad",
        t_start=1.0,
        t_end=2.0,
        op_type="location",
        object_id="cup",
        variable="location",
        before="drawer",
        after="shelf",
    )

    updated = apply_event_operator(ledger, op, allow_unverified_toy=True)

    assert updated.get_state("cup", "location") == "table"
    assert len(updated.conflicts) == 1
    assert updated.conflicts[0].event_id == "e_bad"
    assert updated.events == ()
    assert [event.event_id for event in updated.rejected_events] == ["e_bad"]


def test_apply_event_operators_replays_in_time_order():
    ledger = StateLedger.from_initial_state({"cup": {"location": "table"}})
    later = EventOperator("e2", 3.0, 4.0, "location", "cup", "location", "shelf", "sink")
    earlier = EventOperator("e1", 1.0, 2.0, "location", "cup", "location", "table", "shelf")

    updated = apply_event_operators(ledger, [later, earlier], allow_unverified_toy=True)

    assert updated.get_state("cup", "location") == "sink"
    assert [record.event_id for record in updated.history("cup", "location")] == [
        "__initial__",
        "e1",
        "e2",
    ]
