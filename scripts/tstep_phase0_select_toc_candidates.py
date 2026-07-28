#!/usr/bin/env python3
"""Select an answer-blind, stratified TOC-Bench Phase 0 candidate set."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VIDEO_ROOT = "datasets/toc_bench_full/videos"
SEED = 20260728
DIM_TIER_QUOTAS: Mapping[str, Mapping[str, int]] = {
    "conditional_state": {"tier1": 2, "tier2": 2, "tier3": 2},
    "relative_spatial_change": {"tier1": 2, "tier2": 2, "tier3": 1},
    "reappear_or_disappear": {"tier1": 2, "tier2": 2, "tier3": 1},
    "reappear_identity": {"tier1": 1, "tier2": 2, "tier3": 2},
    "event_ordering": {"tier1": 1, "tier2": 2, "tier3": 2},
    "cross_object_order": {"tier1": 2, "tier2": 1, "tier3": 1},
}
QUERY_TYPE_BY_DIM = {
    "conditional_state": "conditional_state",
    "relative_spatial_change": "relation_change",
    "reappear_or_disappear": "visibility",
    "reappear_identity": "object_identity",
    "event_ordering": "event_order",
    "cross_object_order": "event_order",
}
LEDGER_ROLE_BY_DIM = {
    "conditional_state": "state_transition",
    "relative_spatial_change": "relation_change",
    "reappear_or_disappear": "identity_persistence",
    "reappear_identity": "identity_persistence",
    "event_ordering": "temporal_order",
    "cross_object_order": "identity_and_order",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "source" / "toc_answer_final.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "toc_phase0_candidates_30.jsonl",
    )
    parser.add_argument(
        "--gold-output",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "evaluator_only" / "toc_gold_30.jsonl",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "toc_candidates_30_summary.json",
    )
    parser.add_argument(
        "--video-id-output",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "toc_candidate_video_ids.txt",
    )
    parser.add_argument(
        "--video-root",
        default=DEFAULT_VIDEO_ROOT,
        help="Portable path or URI prefix used in the answer-blind manifest.",
    )
    parser.add_argument("--seed", type=int, default=SEED)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    items = payload["items"]
    selected, shortfalls = select_candidates(items, seed=args.seed)
    candidates = [
        candidate_row(item, video_root=args.video_root) for item in selected
    ]
    gold_rows = [gold_row(item) for item in selected]

    write_jsonl(args.output, candidates)
    write_jsonl(args.gold_output, gold_rows)
    args.video_id_output.parent.mkdir(parents=True, exist_ok=True)
    args.video_id_output.write_text(
        "".join(f"{item['video_id']}\n" for item in selected),
        encoding="utf-8",
    )
    summary = build_summary(items, selected, shortfalls, args)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def select_candidates(
    items: Sequence[Mapping[str, Any]],
    *,
    seed: int,
) -> Tuple[List[Mapping[str, Any]], List[Mapping[str, Any]]]:
    pools: Dict[Tuple[str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for item in items:
        metadata = item.get("metadata", {})
        dim = metadata.get("dim")
        tier = metadata.get("tier")
        if dim not in DIM_TIER_QUOTAS or tier not in {"tier1", "tier2", "tier3"}:
            continue
        if not item.get("qa_id") or not item.get("video_id"):
            continue
        if not metadata.get("subject_label"):
            continue
        if metadata.get("has_hallucination_distractor", False):
            continue
        pools[(dim, tier)].append(item)

    for key, rows in pools.items():
        rows.sort(key=lambda item: deterministic_key(seed, item["qa_id"]))

    selected: List[Mapping[str, Any]] = []
    selected_ids = set()
    selected_videos = set()
    shortfalls: List[Mapping[str, Any]] = []
    for dim, tier_quotas in DIM_TIER_QUOTAS.items():
        dim_target = sum(tier_quotas.values())
        dim_selected: List[Mapping[str, Any]] = []
        for tier, target in tier_quotas.items():
            picked = take_unique(
                pools[(dim, tier)],
                target,
                selected_ids,
                selected_videos,
            )
            dim_selected.extend(picked)
            if len(picked) < target:
                shortfalls.append(
                    {
                        "dim": dim,
                        "tier": tier,
                        "target": target,
                        "selected": len(picked),
                        "reason": "pool_or_unique_video_shortfall",
                    }
                )

        if len(dim_selected) < dim_target:
            fallback = sorted(
                (
                    item
                    for tier in ("tier1", "tier2", "tier3")
                    for item in pools[(dim, tier)]
                ),
                key=lambda item: deterministic_key(seed + 1, item["qa_id"]),
            )
            dim_selected.extend(
                take_unique(
                    fallback,
                    dim_target - len(dim_selected),
                    selected_ids,
                    selected_videos,
                )
            )
        selected.extend(dim_selected)

    expected = sum(
        sum(tier_quotas.values()) for tier_quotas in DIM_TIER_QUOTAS.values()
    )
    if len(selected) != expected:
        raise RuntimeError(f"selected {len(selected)} candidates; expected {expected}")
    return selected, shortfalls


def take_unique(
    pool: Iterable[Mapping[str, Any]],
    count: int,
    selected_ids: set[str],
    selected_videos: set[str],
) -> List[Mapping[str, Any]]:
    picked = []
    for item in pool:
        if len(picked) >= count:
            break
        if item["qa_id"] in selected_ids or item["video_id"] in selected_videos:
            continue
        selected_ids.add(item["qa_id"])
        selected_videos.add(item["video_id"])
        picked.append(item)
    return picked


def candidate_row(
    item: Mapping[str, Any],
    *,
    video_root: str = DEFAULT_VIDEO_ROOT,
) -> Dict[str, Any]:
    metadata = item["metadata"]
    dim = metadata["dim"]
    choices = choices_for(item)
    return {
        "schema_version": "tstep-toc-candidate-v0.1",
        "sample_id": f"TOC-Bench:phase0:{item['video_id']}:{item['qa_id']}",
        "video": {
            "video_id": item["video_id"],
            "path_or_uri": f"{video_root.rstrip('/')}/{item['video_id']}.mp4",
            "decode_status": "pending_remote_probe",
            "duration_ms": None,
            "fps": None,
            "frame_count": None,
        },
        "question": {
            "qa_id": item["qa_id"],
            "text": item["question"],
            "format": item["format"],
            "choices": choices,
            "events": item.get("events", []),
        },
        "source_metadata": {
            "dim": dim,
            "tier": metadata["tier"],
            "subject_label": metadata["subject_label"],
            "hallucination": metadata.get("hallucination"),
            "has_hallucination_distractor": metadata.get(
                "has_hallucination_distractor",
                False,
            ),
        },
        "screening": {
            "proposed_query_type": QUERY_TYPE_BY_DIM[dim],
            "ledger_role": LEDGER_ROLE_BY_DIM[dim],
            "ledger_critical_status": "requires_video_review",
            "subject_visible": None,
            "state_or_relation_change_visible": None,
            "static_frame_sufficient": None,
            "multi_instance_interference": None,
            "persistent_identity_required": dim
            in {"reappear_identity", "cross_object_order"},
            "transition_dependent": None,
            "deep_annotation_eligible": None,
            "exclusion_reason": None,
            "reviewer": None,
            "review_confidence": None,
        },
        "coverage": {
            "has_video": True,
            "has_question": True,
            "has_answer_evaluator_only": True,
            "has_temporal_evidence": False,
            "has_bbox_or_track": False,
            "has_persistent_object_id": False,
            "has_state_label": False,
            "has_transition_boundary": False,
        },
        "blindness": {
            "gold_answer_present": False,
            "gold_artifact": "data/phase0/evaluator_only/toc_gold_30.jsonl",
        },
    }


def gold_row(item: Mapping[str, Any]) -> Dict[str, Any]:
    gold_value = (
        item["correct_answer"]
        if "correct_answer" in item
        else item.get("correct_order")
    )
    return {
        "sample_id": f"TOC-Bench:phase0:{item['video_id']}:{item['qa_id']}",
        "qa_id": item["qa_id"],
        "correct_answer": gold_value,
        "allowed_answers": item.get("allowed_answers"),
        "statement_A": item.get("statement_A"),
        "statement_B": item.get("statement_B"),
        "access_scope": "evaluator_only",
    }


def build_summary(
    items: Sequence[Mapping[str, Any]],
    selected: Sequence[Mapping[str, Any]],
    shortfalls: Sequence[Mapping[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    target_dims = set(DIM_TIER_QUOTAS)
    available = Counter(
        (item.get("metadata", {}).get("dim"), item.get("metadata", {}).get("tier"))
        for item in items
        if item.get("metadata", {}).get("dim") in target_dims
    )
    return {
        "schema_version": "tstep-toc-selection-summary-v0.1",
        "seed": args.seed,
        "selected_count": len(selected),
        "unique_video_count": len({item["video_id"] for item in selected}),
        "selected_by_dim": dict(
            Counter(item["metadata"]["dim"] for item in selected)
        ),
        "selected_by_tier": dict(
            Counter(item["metadata"]["tier"] for item in selected)
        ),
        "available_by_dim_tier": {
            f"{dim}/{tier}": count
            for (dim, tier), count in sorted(available.items())
        },
        "quota_shortfalls": list(shortfalls),
        "answer_blind_manifest": str(args.output),
        "evaluator_only_gold": str(args.gold_output),
        "video_id_list": str(args.video_id_output),
        "warning": (
            "This is a deterministic candidate manifest, not a TOC-Bench "
            "feasibility estimate. Video review is still pending."
        ),
    }


def choices_for(item: Mapping[str, Any]) -> List[str]:
    if item.get("allowed_answers"):
        return list(item["allowed_answers"])
    choices = []
    for suffix in ("A", "B", "C", "D"):
        value = item.get(f"statement_{suffix}", item.get(f"option_{suffix}"))
        if value is not None:
            choices.append(value)
    return choices


def deterministic_key(seed: int, qa_id: str) -> str:
    return hashlib.sha256(f"{seed}:{qa_id}".encode("utf-8")).hexdigest()


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
