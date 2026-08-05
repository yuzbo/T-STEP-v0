import subprocess
import sys
from pathlib import Path

from tstep_v0.datasets import read_jsonl, validate_unified_sample


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_phase0_mapping_is_reproducible_from_public_fixture(tmp_path):
    output = tmp_path / "mapped.jsonl"
    coverage = tmp_path / "coverage.csv"

    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            str(PROJECT_ROOT / "scripts" / "tstep_phase0_map_first_samples.py"),
            "--input",
            str(
                PROJECT_ROOT
                / "examples"
                / "tstep_v0"
                / "phase0_mapping_fixture.jsonl"
            ),
            "--output",
            str(output),
            "--coverage-output",
            str(coverage),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    samples = list(read_jsonl(output))
    assert len(samples) == 4
    assert {sample["dataset"] for sample in samples} == {
        "VSTAT",
        "TOC-Bench",
        "VidOSC",
        "Moment-Video",
    }
    assert sum(sample["coverage"]["has_video"] for sample in samples) == 1
    assert sum(
        sample["coverage"]["can_define_stable_state_variable"] for sample in samples
    ) == 2
    for sample in samples:
        validate_unified_sample(sample)
    assert coverage.read_text(encoding="utf-8").count("\n") == 5
