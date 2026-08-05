from pathlib import Path

import pytest

from tstep_v0.datasets import (
    read_jsonl,
    synthetic_toy_sample_to_ledger,
    synthetic_toy_sample_to_query,
    validate_unified_sample,
)
from tstep_v0.query_executor import execute_query


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TOY_SAMPLES = PROJECT_ROOT / "examples" / "tstep_v0" / "toy_phase0_samples.jsonl"


def test_toy_samples_validate_and_execute_against_normalized_targets():
    samples = list(read_jsonl(TOY_SAMPLES))

    assert len(samples) == 4
    for sample in samples:
        validate_unified_sample(sample)
        result = execute_query(
            synthetic_toy_sample_to_ledger(sample),
            synthetic_toy_sample_to_query(sample),
        )
        assert str(result.answer).lower() == str(
            sample["question"]["gt_answer_normalized"]
        ).lower()


def test_validation_rejects_missing_coverage_flags():
    sample = next(read_jsonl(TOY_SAMPLES))
    del sample["coverage"]["has_state_label"]

    with pytest.raises(ValueError, match="coverage is missing flags"):
        validate_unified_sample(sample)
