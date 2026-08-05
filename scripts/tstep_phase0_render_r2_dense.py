#!/usr/bin/env python3
"""Render the presealed R2 roster with the endpoint-inclusive 24-frame stage."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.tstep_phase0_prepare_deep10 import render_dense_sheets, write_jsonl
from tstep_v0.sampling import SAMPLER_VERSION


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "toc_phase0_r2_probed.jsonl",
    )
    parser.add_argument(
        "--preseal",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "toc_phase0_r2_preseal.json",
    )
    parser.add_argument(
        "--amendment",
        type=Path,
        default=PROJECT_ROOT
        / "data"
        / "phase0"
        / "toc_phase0_r2_preseal_amendment_001.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "toc_phase0_r2_dense.jsonl",
    )
    parser.add_argument(
        "--contact-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "contact_sheets" / "toc_r2_dense",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "toc_phase0_r2_dense_render_report.json",
    )
    parser.add_argument("--frame-count", type=int, default=24)
    return parser.parse_args()


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> int:
    args = parse_args()
    if args.frame_count != 24:
        raise ValueError("R2 contract freezes endpoint-inclusive dense review at 24 frames")
    rows = load_jsonl(args.manifest)
    preseal = json.loads(args.preseal.read_text(encoding="utf-8"))
    amendment = (
        json.loads(args.amendment.read_text(encoding="utf-8"))
        if args.amendment.exists()
        else None
    )
    if amendment is not None and amendment.get("original_roster_sha256") != preseal.get("roster_sha256"):
        raise RuntimeError("R2 prompt amendment does not chain from the locked preseal")
    expected_ids = [row["sample_id"] for row in preseal["roster"]]
    actual_ids = [row["sample_id"] for row in rows]
    if preseal.get("roster_locked") is not True or actual_ids != expected_ids:
        raise RuntimeError("dense render manifest differs from the locked R2 roster")
    if any(row.get("video", {}).get("decode_status") != "ok" for row in rows):
        raise RuntimeError("all R2 videos must pass the coarse decode stage before dense render")

    for row in rows:
        row["video"]["dense_contact_sheet_paths"] = render_dense_sheets(
            row,
            args.contact_dir,
            args.frame_count,
            12,
        )
        row["r2_dense_review"] = {
            "status": "rendered_not_reviewed",
            "sampler_version": SAMPLER_VERSION,
            "gold_accessed": False,
        }
    write_jsonl(args.output, rows)

    report = {
        "schema_version": "tstep-toc-r2-dense-render-v0.2",
        "original_preseal_roster_sha256": preseal["roster_sha256"],
        "effective_roster_sha256": (
            amendment["effective_roster_sha256"] if amendment is not None else preseal["roster_sha256"]
        ),
        "prompt_amendment_id": amendment.get("amendment_id") if amendment is not None else None,
        "sampler_version": SAMPLER_VERSION,
        "video_count": len(rows),
        "frame_count_per_video": args.frame_count,
        "total_dense_frame_count": len(rows) * args.frame_count,
        "endpoint_inclusive": True,
        "gold_accessed": False,
        "review_status": "rendered_not_reviewed",
        "gpu_or_training_started": False,
        "rows": [
            {
                "sample_id": row["sample_id"],
                "video_id": row["video"]["video_id"],
                "dimension": row["source_metadata"]["dim"],
                "frame_samples": row["video"]["dense_sampling"]["samples"],
            }
            for row in rows
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
