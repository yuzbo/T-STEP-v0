from pathlib import Path

from tstep_v0.datasets import read_jsonl
from tstep_v0.eval import evaluate_ledger_queries, evaluate_samples, normalize_answer
from tstep_v0.ledger_schema import EventOperator, LedgerQuery, StateLedger
from tstep_v0.ledger_update import apply_event_operators


def test_eval_runner_reports_query_accuracy_and_corruption_sensitivity():
    clean = apply_event_operators(
        StateLedger.from_initial_state({"cup": {"location": "table"}}),
        [
            EventOperator("e1", 1.0, 2.0, "location", "cup", "location", "table", "shelf"),
            EventOperator("e2", 3.0, 4.0, "location", "cup", "location", "shelf", "sink"),
        ],
    )
    corrupted = apply_event_operators(
        StateLedger.from_initial_state({"cup": {"location": "table"}}),
        [
            EventOperator("e1", 1.0, 2.0, "location", "cup", "location", "table", "shelf"),
            EventOperator("e2_bad", 3.0, 4.0, "location", "cup", "location", "shelf", "drawer"),
        ],
    )
    queries = [(LedgerQuery("final_state", object_id="cup", variable="location"), "sink")]

    report = evaluate_ledger_queries(clean, queries, corrupted_ledger=corrupted)

    assert report["ledger_query_accuracy"] == 1.0
    assert report["corruption_sensitivity"] == 1.0


def test_evaluate_samples_runs_unified_schema_and_drop_last_diagnostic():
    project_root = Path(__file__).resolve().parents[2]
    samples = list(
        read_jsonl(project_root / "examples" / "tstep_v0" / "toy_phase0_samples.jsonl")
    )

    report = evaluate_samples(samples, corruption_mode="drop_last")

    assert report["run_kind"] == "annotated_ledger_smoke"
    assert report["num_samples"] == 4
    assert report["ledger_query_accuracy"] == 1.0
    assert report["corruption_sensitivity"] == 1.0
    assert report["risk_coverage_auc"] == 0.0
    assert all(row["metrics"]["transition_f1"] == 1.0 for row in report["results"])
    assert all(row["diagnostics"]["corruption_drop"] == 1.0 for row in report["results"])


def test_normalize_answer_handles_articles_punctuation_booleans_and_numbers():
    assert normalize_answer("The Open-Door!") == "opendoor"
    assert normalize_answer(True) == "true"
    assert normalize_answer(2.0) == "2"
