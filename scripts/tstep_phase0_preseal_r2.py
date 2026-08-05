#!/usr/bin/env python3
"""Preseal an all-new, answer-blind TOC-Bench R2 roster before video review."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.tstep_phase0_select_toc_candidates import candidate_row, gold_row
from tstep_v0.validators import validate_no_answer_access


R2_SEED = 20260806
R2_QUOTAS = {
    "event_ordering": 3,
    "cross_object_order": 2,
    "reappear_identity": 3,
    "reappear_or_disappear": 2,
}
PRESEAL_SCHEMA_VERSION = "tstep-toc-r2-preseal-v0.2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "source" / "toc_answer_final.json",
    )
    parser.add_argument(
        "--prior-manifest",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "toc_phase0_candidates_30.jsonl",
    )
    parser.add_argument(
        "--candidate-pool-output",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "toc_phase0_r2_candidate_pool.jsonl",
    )
    parser.add_argument(
        "--roster-output",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "toc_phase0_r2_roster.jsonl",
    )
    parser.add_argument(
        "--gold-output",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "evaluator_only" / "toc_r2_gold.jsonl",
    )
    parser.add_argument(
        "--preseal-output",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "toc_phase0_r2_preseal.json",
    )
    parser.add_argument("--seed", type=int, default=R2_SEED)
    parser.add_argument("--created-at", default="2026-08-06T00:00:00+08:00")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Explicitly allow replacing an existing preseal (never use after review starts).",
    )
    return parser.parse_args()


def eligible_blind_pool(
    items: Sequence[Mapping[str, Any]],
    *,
    excluded_video_ids: set[str],
) -> List[Dict[str, Any]]:
    rows = []
    seen_videos = set()
    for item in items:
        metadata = item.get("metadata", {})
        dim = metadata.get("dim")
        video_id = item.get("video_id")
        if dim not in R2_QUOTAS or not item.get("qa_id") or not video_id:
            continue
        if video_id in excluded_video_ids or video_id in seen_videos:
            continue
        if not metadata.get("subject_label"):
            continue
        if metadata.get("has_hallucination_distractor", False):
            continue
        row = candidate_row(item)
        row["r2_pool"] = {
            "eligible": True,
            "selection_features": ["dimension", "video_id", "qa_id", "seeded_hash"],
            "gold_used": False,
        }
        validate_no_answer_access(row)
        rows.append(row)
        seen_videos.add(str(video_id))
    return sorted(rows, key=lambda row: row["sample_id"])


def select_r2_roster(
    pool: Sequence[Mapping[str, Any]],
    *,
    seed: int,
) -> List[Dict[str, Any]]:
    by_dim: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in pool:
        by_dim[str(row["source_metadata"]["dim"])].append(row)

    selected = []
    selected_videos = set()
    for dim, quota in R2_QUOTAS.items():
        ranked = sorted(
            by_dim[dim],
            key=lambda row: hashlib.sha256(
                f"{seed}:{row['sample_id']}".encode("utf-8")
            ).hexdigest(),
        )
        picked = []
        for row in ranked:
            video_id = str(row["video"]["video_id"])
            if video_id in selected_videos:
                continue
            copied = json.loads(json.dumps(row))
            copied["r2_selection"] = {
                "selected": True,
                "dimension_quota": quota,
                "seed": seed,
                "preseal_required_before_video_access": True,
                "replacement_allowed": False,
            }
            picked.append(copied)
            selected_videos.add(video_id)
            if len(picked) == quota:
                break
        if len(picked) != quota:
            raise RuntimeError(
                f"R2 pool shortfall for {dim}: need {quota}, have {len(picked)}; "
                "contract requires DEFER rather than replacement"
            )
        selected.extend(picked)

    if len(selected) != 10 or len(selected_videos) != 10:
        raise AssertionError("R2 roster must contain ten unique videos")
    return selected


def canonical_rows_sha256(rows: Sequence[Mapping[str, Any]]) -> str:
    payload = "\n".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for row in rows
    )
    return hashlib.sha256((payload + "\n").encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    args = parse_args()
    if args.preseal_output.exists() and not args.force:
        raise FileExistsError(
            f"refusing to overwrite immutable R2 preseal: {args.preseal_output}; "
            "use a versioned amendment instead"
        )
    source_items = json.loads(args.source.read_text(encoding="utf-8"))["items"]
    prior_rows = read_jsonl(args.prior_manifest)
    excluded_video_ids = {str(row["video"]["video_id"]) for row in prior_rows}

    pool = eligible_blind_pool(source_items, excluded_video_ids=excluded_video_ids)
    roster = select_r2_roster(pool, seed=args.seed)
    selected_ids = {row["sample_id"] for row in roster}
    source_by_sample_id = {
        f"TOC-Bench:phase0:{item['video_id']}:{item['qa_id']}": item
        for item in source_items
        if item.get("video_id") and item.get("qa_id")
    }
    gold_rows = [gold_row(source_by_sample_id[sample_id]) for sample_id in selected_ids]
    gold_rows.sort(key=lambda row: row["sample_id"])

    write_jsonl(args.candidate_pool_output, pool)
    write_jsonl(args.roster_output, roster)
    write_jsonl(args.gold_output, gold_rows)

    report = {
        "schema_version": PRESEAL_SCHEMA_VERSION,
        "created_at": args.created_at,
        "decision": "R2_PRESEALED",
        "roster_locked": True,
        "replacement_allowed": False,
        "gold_accessed_for_selection": False,
        "prior_candidate_video_count_excluded": len(excluded_video_ids),
        "all_video_ids_new_vs_r1_candidate_30": all(
            row["video"]["video_id"] not in excluded_video_ids for row in roster
        ),
        "seed": args.seed,
        "quotas": R2_QUOTAS,
        "candidate_pool_count": len(pool),
        "candidate_pool_by_dim": dict(Counter(row["source_metadata"]["dim"] for row in pool)),
        "candidate_pool_sha256": canonical_rows_sha256(pool),
        "prior_candidate_manifest_sha256": file_sha256(args.prior_manifest),
        "roster_sha256": canonical_rows_sha256(roster),
        "evaluator_gold_sha256": file_sha256(args.gold_output),
        "roster": [
            {
                "sample_id": row["sample_id"],
                "video_id": row["video"]["video_id"],
                "dimension": row["source_metadata"]["dim"],
                "asset_status": "download_pending",
                "deep_review_status": "not_started",
            }
            for row in roster
        ],
        "pass_gate": {
            "overall": "accepted >= 8/10",
            "event_order_sensitive": "accepted >= 4/5",
            "identity_visibility_sensitive": "accepted >= 4/5",
        },
        "gpu_locked": True,
    }
    args.preseal_output.parent.mkdir(parents=True, exist_ok=True)
    args.preseal_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
