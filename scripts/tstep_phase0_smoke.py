#!/usr/bin/env python3
"""Run the annotated-ledger Phase 0 smoke loop on unified JSONL samples."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tstep_v0.datasets import read_jsonl, write_jsonl
from tstep_v0.eval import evaluate_samples


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "examples" / "tstep_v0" / "toy_phase0_samples.jsonl",
        help="Unified-sample JSONL input.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "smoke_results.jsonl",
        help="Per-sample result JSONL output.",
    )
    parser.add_argument(
        "--summary",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "smoke_summary.json",
        help="Aggregate summary JSON output.",
    )
    parser.add_argument("--run-id", default="phase0_toy_smoke")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    samples = list(read_jsonl(args.input))
    report = evaluate_samples(samples, run_id=args.run_id)
    write_jsonl(args.output, report["results"])

    summary = {key: value for key, value in report.items() if key != "results"}
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
