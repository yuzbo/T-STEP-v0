#!/usr/bin/env python3
"""Fetch only the ten presealed R2 videos from the public TOC-Bench snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

from huggingface_hub import hf_hub_download


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.tstep_phase0_preseal_r2 import canonical_rows_sha256


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--roster",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "toc_phase0_r2_roster.jsonl",
    )
    parser.add_argument(
        "--preseal",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "toc_phase0_r2_preseal.json",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "videos" / "toc_r2",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "toc_phase0_r2_asset_report.json",
    )
    parser.add_argument("--repo-id", default="anonymous-video-benchmark/toc_bench")
    return parser.parse_args()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> int:
    args = parse_args()
    preseal = json.loads(args.preseal.read_text(encoding="utf-8"))
    roster = load_jsonl(args.roster)
    if preseal.get("roster_locked") is not True:
        raise RuntimeError("R2 assets cannot be fetched before roster preseal")
    if canonical_rows_sha256(roster) != preseal.get("roster_sha256"):
        raise RuntimeError("R2 roster hash differs from the presealed hash")
    if len(roster) != 10 or len({row["video"]["video_id"] for row in roster}) != 10:
        raise RuntimeError("R2 roster must contain ten unique videos")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for row in roster:
        video_id = str(row["video"]["video_id"])
        destination = args.output_dir / f"{video_id}.mp4"
        if not destination.exists() or destination.stat().st_size == 0:
            cached = Path(
                hf_hub_download(
                    repo_id=args.repo_id,
                    repo_type="dataset",
                    filename=f"videos/{video_id}.mp4",
                )
            )
            shutil.copy2(cached, destination)
        rows.append(
            {
                "sample_id": row["sample_id"],
                "video_id": video_id,
                "status": "materialized",
                "file_size_bytes": destination.stat().st_size,
                "sha256": file_sha256(destination),
            }
        )

    report = {
        "schema_version": "tstep-toc-r2-assets-v0.2",
        "preseal_roster_sha256": preseal["roster_sha256"],
        "repo_id": args.repo_id,
        "requested_count": len(roster),
        "materialized_count": sum(row["status"] == "materialized" for row in rows),
        "all_nonempty": all(row["file_size_bytes"] > 0 for row in rows),
        "gpu_or_training_started": False,
        "rows": rows,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
