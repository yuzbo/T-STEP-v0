#!/usr/bin/env python3
"""Validate the frozen blind R2 review and compute the immutable gate result."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.tstep_phase0_preseal_r2 import canonical_rows_sha256
from tstep_v0.validators import validate_no_answer_access


EVENT_DIMS = {"event_ordering", "cross_object_order"}
IDENTITY_DIMS = {"reappear_identity", "reappear_or_disappear"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    phase0 = PROJECT_ROOT / "data" / "phase0"
    parser.add_argument("--review", type=Path, default=phase0 / "toc_phase0_r2_manual_review.json")
    parser.add_argument("--preseal", type=Path, default=phase0 / "toc_phase0_r2_preseal.json")
    parser.add_argument(
        "--amendment", type=Path, default=phase0 / "toc_phase0_r2_preseal_amendment_001.json"
    )
    parser.add_argument("--roster", type=Path, default=phase0 / "toc_phase0_r2_roster.jsonl")
    parser.add_argument("--asset-report", type=Path, default=phase0 / "toc_phase0_r2_asset_report.json")
    parser.add_argument("--probe-report", type=Path, default=phase0 / "toc_phase0_r2_probe_report.json")
    parser.add_argument(
        "--dense-report", type=Path, default=phase0 / "toc_phase0_r2_dense_render_report.json"
    )
    parser.add_argument(
        "--targeted-report", type=Path, default=phase0 / "toc_phase0_r2_targeted_render_report.json"
    )
    parser.add_argument(
        "--targeted-spec", type=Path, default=phase0 / "toc_phase0_r2_targeted_windows.json"
    )
    parser.add_argument("--output", type=Path, default=phase0 / "toc_phase0_r2_gate_result.json")
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def validate_and_score_rows(
    rows: Sequence[Mapping[str, Any]],
    expected_roster: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    expected_ids = [str(row["sample_id"]) for row in expected_roster]
    actual_ids = [str(row.get("sample_id")) for row in rows]
    if actual_ids != expected_ids:
        raise ValueError("review rows must exactly preserve the presealed sample IDs and order")
    if len(set(actual_ids)) != len(actual_ids):
        raise ValueError("review sample IDs must be unique")

    expected_dims = {str(row["sample_id"]): str(row["dimension"]) for row in expected_roster}
    for row in rows:
        sample_id = str(row["sample_id"])
        dimension = str(row.get("dimension"))
        if dimension != expected_dims[sample_id]:
            raise ValueError(f"review dimension changed for {sample_id}")
        decision = row.get("decision")
        status = row.get("event_presupposition_status")
        if decision not in {"accepted", "blocked"}:
            raise ValueError(f"invalid review decision for {sample_id}: {decision}")
        if status not in {"observed", "unsupported", "ambiguous", "outside_clip", "not_required"}:
            raise ValueError(f"invalid event presupposition status for {sample_id}: {status}")
        if decision == "accepted" and status != "observed":
            raise ValueError(f"accepted event-dependent row must be observed: {sample_id}")
        expected_cohort = (
            "event_order_sensitive" if dimension in EVENT_DIMS else "identity_visibility_sensitive"
        )
        if row.get("cohort") != expected_cohort:
            raise ValueError(f"cohort mismatch for {sample_id}")

    accepted = [row for row in rows if row["decision"] == "accepted"]
    event_rows = [row for row in rows if row["dimension"] in EVENT_DIMS]
    identity_rows = [row for row in rows if row["dimension"] in IDENTITY_DIMS]
    if len(rows) != 10 or len(event_rows) != 5 or len(identity_rows) != 5:
        raise ValueError("R2 must contain 10 rows split into fixed 5/5 cohorts")

    overall_count = len(accepted)
    event_count = sum(row["decision"] == "accepted" for row in event_rows)
    identity_count = sum(row["decision"] == "accepted" for row in identity_rows)
    checks = {
        "overall_accepted_at_least_8_of_10": overall_count >= 8,
        "event_order_accepted_at_least_4_of_5": event_count >= 4,
        "identity_visibility_accepted_at_least_4_of_5": identity_count >= 4,
    }
    return {
        "overall": {"accepted": overall_count, "total": 10, "passed": checks["overall_accepted_at_least_8_of_10"]},
        "event_order_sensitive": {"accepted": event_count, "total": 5, "passed": checks["event_order_accepted_at_least_4_of_5"]},
        "identity_visibility_sensitive": {"accepted": identity_count, "total": 5, "passed": checks["identity_visibility_accepted_at_least_4_of_5"]},
        "checks": checks,
        "gate_passed": all(checks.values()),
    }


def main() -> int:
    args = parse_args()
    review = json.loads(args.review.read_text(encoding="utf-8"))
    validate_no_answer_access(review)
    preseal = json.loads(args.preseal.read_text(encoding="utf-8"))
    amendment = json.loads(args.amendment.read_text(encoding="utf-8"))
    roster = read_jsonl(args.roster)

    if canonical_rows_sha256(roster) != amendment["effective_roster_sha256"]:
        raise ValueError("effective R2 roster hash does not match the immutable amendment")
    if review["original_preseal_roster_sha256"] != preseal["roster_sha256"]:
        raise ValueError("review does not chain from the immutable R2 preseal")
    if review["effective_roster_sha256"] != amendment["effective_roster_sha256"]:
        raise ValueError("review does not chain from the effective R2 roster")
    if review["sampler_version"] != "tstep-four-stage-sampler-v0.2.2":
        raise ValueError("R2 review must use the PTS-validated v0.2.2 sampler")
    protocol = review["review_protocol"]
    if protocol.get("evaluator_artifact_accessed") is not False:
        raise ValueError("R2 review must remain evaluator-artifact blind")
    if protocol.get("training_or_gpu_started") is not False:
        raise ValueError("GPU/training must remain locked during R2")
    if protocol.get("replacement_performed") is not False:
        raise ValueError("R2 replacement is forbidden")

    score = validate_and_score_rows(review["rows"], preseal["roster"])
    blocked = [row for row in review["rows"] if row["decision"] == "blocked"]
    result = {
        "schema_version": "tstep-toc-r2-gate-result-v0.2",
        "created_at": "2026-08-06T18:30:00+08:00",
        "decision": "R2_GATE_PASSED" if score["gate_passed"] else "R2_GATE_FAILED",
        "immutable_roster": True,
        "replacement_performed": False,
        "evaluator_artifact_accessed": False,
        "training_or_gpu_started": False,
        "score": score,
        "blocked_reason_counts": dict(Counter(str(row["reason_code"]) for row in blocked)),
        "row_decisions": [
            {
                "sample_id": row["sample_id"],
                "video_id": row["video_id"],
                "dimension": row["dimension"],
                "decision": row["decision"],
                "event_presupposition_status": row["event_presupposition_status"],
                "reason_code": row["reason_code"],
            }
            for row in review["rows"]
        ],
        "artifact_sha256": {
            "manual_review": file_sha256(args.review),
            "effective_roster_file": file_sha256(args.roster),
            "asset_report": file_sha256(args.asset_report),
            "probe_report": file_sha256(args.probe_report),
            "dense_render_report": file_sha256(args.dense_report),
            "targeted_window_spec": file_sha256(args.targeted_spec),
            "targeted_render_report": file_sha256(args.targeted_report),
        },
        "route_effect": (
            "DEFER_GPU_AND_DO_NOT_RESAMPLE_R2; retain ledger-core code, reject TOC-Bench "
            "automatic event labels as sole local-core supervision, and redesign the real-asset "
            "source/annotation contract before any model experiment."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if score["gate_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
