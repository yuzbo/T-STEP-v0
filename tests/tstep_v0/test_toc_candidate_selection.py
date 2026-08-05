import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

from tstep_v0.datasets import read_jsonl
from tstep_v0.validators import validate_no_answer_access
from scripts.tstep_phase0_select_toc_candidates import candidate_row
from scripts.tstep_phase0_preseal_r2 import (
    R2_QUOTAS,
    canonical_rows_sha256,
    eligible_blind_pool,
    select_r2_roster,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_candidate_row_uses_configurable_portable_video_root():
    item = {
        "qa_id": "synthetic_q1",
        "video_id": "synthetic_video",
        "question": "Synthetic conditional-state question?",
        "format": "mcq_4",
        "allowed_answers": ["a", "b", "c", "d"],
        "metadata": {
            "dim": "conditional_state",
            "tier": "tier3",
            "subject_label": "synthetic object",
            "hallucination": None,
            "has_hallucination_distractor": False,
        },
    }

    row = candidate_row(item, video_root="s3://example-bucket/videos")

    assert (
        row["video"]["path_or_uri"]
        == "s3://example-bucket/videos/synthetic_video.mp4"
    )


def test_toc_candidate_selection_is_stratified_and_answer_blind(tmp_path):
    source = PROJECT_ROOT / "data" / "phase0" / "source" / "toc_answer_final.json"
    if not source.exists():
        return
    output = tmp_path / "candidates.jsonl"
    gold = tmp_path / "gold.jsonl"
    summary = tmp_path / "summary.json"
    video_ids = tmp_path / "video_ids.txt"
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            str(PROJECT_ROOT / "scripts" / "tstep_phase0_select_toc_candidates.py"),
            "--input",
            str(source),
            "--output",
            str(output),
            "--gold-output",
            str(gold),
            "--summary",
            str(summary),
            "--video-id-output",
            str(video_ids),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    candidates = list(read_jsonl(output))
    assert len(candidates) == 30
    assert len({row["video"]["video_id"] for row in candidates}) == 30
    assert Counter(row["source_metadata"]["dim"] for row in candidates) == {
        "conditional_state": 6,
        "relative_spatial_change": 5,
        "reappear_or_disappear": 5,
        "reappear_identity": 5,
        "event_ordering": 5,
        "cross_object_order": 4,
    }
    for row in candidates:
        validate_no_answer_access(row)
        assert row["blindness"]["gold_answer_present"] is False
    assert len(list(read_jsonl(gold))) == 30
    assert len(video_ids.read_text(encoding="utf-8").splitlines()) == 30
    assert json.loads(summary.read_text(encoding="utf-8"))["selected_count"] == 30


def test_r2_preseal_is_all_new_quota_exact_and_deterministic():
    items = []
    for dim, quota in R2_QUOTAS.items():
        for index in range(quota + 1):
            items.append(
                {
                    "qa_id": f"{dim}-{index}",
                    "video_id": f"{dim}-video-{index}",
                    "question": f"Question for {dim} {index}?",
                    "format": "sp",
                    "allowed_answers": ["A", "B"],
                    "correct_answer": "A",
                    "events": [{"answer_derived": True}],
                    "metadata": {
                        "dim": dim,
                        "tier": "tier1",
                        "subject_label": "object",
                        "has_hallucination_distractor": False,
                    },
                }
            )
    excluded = {"event_ordering-video-0"}
    pool = eligible_blind_pool(items, excluded_video_ids=excluded)
    first = select_r2_roster(pool, seed=17)
    second = select_r2_roster(pool, seed=17)

    assert first == second
    assert len(first) == 10
    assert len({row["video"]["video_id"] for row in first}) == 10
    assert not ({row["video"]["video_id"] for row in first} & excluded)
    assert Counter(row["source_metadata"]["dim"] for row in first) == R2_QUOTAS
    assert all("events" not in row["question"] for row in first)
    assert canonical_rows_sha256(first) == canonical_rows_sha256(second)
