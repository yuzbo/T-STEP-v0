#!/usr/bin/env python3
"""Render dense, answer-blind sheets for Phase 0 replacement candidates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tstep_phase0_prepare_deep10 import load_jsonl, render_dense_sheets, write_jsonl


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pool",
        type=Path,
        default=PROJECT_ROOT
        / "data"
        / "phase0"
        / "toc_deep10_replacement_pool.json",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=PROJECT_ROOT
        / "data"
        / "phase0"
        / "toc_phase0_candidates_30_screened.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT
        / "data"
        / "phase0"
        / "toc_deep10_replacement_candidates.jsonl",
    )
    parser.add_argument(
        "--contact-dir",
        type=Path,
        default=PROJECT_ROOT
        / "data"
        / "phase0"
        / "contact_sheets"
        / "toc_deep10_replacements",
    )
    parser.add_argument("--frame-count", type=int, default=24)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    pool = json.loads(args.pool.read_text(encoding="utf-8"))
    if pool.get("gold_accessed") is not False:
        raise ValueError("replacement pool must assert gold_accessed=false")
    sample_ids = pool["sample_ids"]
    if len(sample_ids) != len(set(sample_ids)):
        raise ValueError("replacement sample IDs must be unique")

    by_id = {row["sample_id"]: row for row in load_jsonl(args.manifest)}
    missing = sorted(set(sample_ids) - set(by_id))
    if missing:
        raise ValueError(f"replacement IDs missing from screened manifest: {missing}")

    selected = []
    for sample_id in sample_ids:
        row = json.loads(json.dumps(by_id[sample_id]))
        if row.get("blindness", {}).get("gold_answer_present") is not False:
            raise ValueError(f"replacement row is not answer blind: {sample_id}")
        row["replacement_review"] = {
            "candidate": True,
            "selection_stage": "dense_temporal_review_pending",
        }
        row["video"]["dense_contact_sheet_paths"] = render_dense_sheets(
            row,
            args.contact_dir,
            args.frame_count,
            12,
        )
        selected.append(row)

    write_jsonl(args.output, selected)
    print(
        json.dumps(
            {
                "schema_version": "tstep-replacement-render-v0.1",
                "gold_accessed": False,
                "replacement_count": len(selected),
                "sample_ids": sample_ids,
                "frame_count_per_video": args.frame_count,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
