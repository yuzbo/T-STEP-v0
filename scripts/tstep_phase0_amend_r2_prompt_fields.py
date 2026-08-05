#!/usr/bin/env python3
"""Apply a versioned, answer-blind prompt-completeness amendment to R2.

The R2 roster was sealed before we established upstream provenance for the
TOC-Bench ``events`` field.  Upstream construction/evaluation code proves that
``label`` and ``event_text`` are shuffled prompt options, while
``correct_order`` is stored separately as evaluator gold.  This script keeps
the selected samples and their order fixed and adds only those two prompt
fields to ordering questions.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.tstep_phase0_preseal_r2 import canonical_rows_sha256
from scripts.tstep_phase0_select_toc_candidates import query_event_descriptions_for
from tstep_v0.validators import validate_no_answer_access


AMENDMENT_ID = "R2_PRESEAL_AMENDMENT_001"
UPSTREAM_REPOSITORY = "https://github.com/cjzcjz666/toc_bench"
UPSTREAM_COMMIT = "e4a10bc1fd31ec1af9482bcfc827e41f2fac769a"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "source" / "toc_answer_final.json",
    )
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
        "--amendment-output",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "toc_phase0_r2_preseal_amendment_001.json",
    )
    parser.add_argument("--created-at", default="2026-08-06T12:00:00+08:00")
    return parser.parse_args()


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def source_sample_id(item: Mapping[str, Any]) -> str:
    return f"TOC-Bench:phase0:{item['video_id']}:{item['qa_id']}"


def amend_roster_prompt_fields(
    roster: Sequence[Mapping[str, Any]],
    source_items: Sequence[Mapping[str, Any]],
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    source_by_id = {
        source_sample_id(item): item
        for item in source_items
        if item.get("video_id") and item.get("qa_id")
    }
    amended: List[Dict[str, Any]] = []
    changes: List[Dict[str, Any]] = []
    for original in roster:
        row = json.loads(json.dumps(original))
        if row.get("source_metadata", {}).get("dim") == "event_ordering":
            item = source_by_id.get(str(row["sample_id"]))
            if item is None:
                raise KeyError(f"source item missing for {row['sample_id']}")
            projected = query_event_descriptions_for(item)
            if not projected:
                raise ValueError(f"ordering prompt options missing for {row['sample_id']}")
            question = row.setdefault("question", {})
            if "query_event_descriptions" in question:
                raise ValueError(f"roster is already amended for {row['sample_id']}")
            question["query_event_descriptions"] = projected
            changes.append(
                {
                    "sample_id": row["sample_id"],
                    "added_field": "question.query_event_descriptions",
                    "event_count": len(projected),
                }
            )
        validate_no_answer_access(row)
        amended.append(row)

    if len(changes) != 3:
        raise AssertionError(f"R2 amendment expected three event-order rows, got {len(changes)}")
    if [row["sample_id"] for row in amended] != [row["sample_id"] for row in roster]:
        raise AssertionError("R2 amendment must not change sample IDs or roster order")
    return amended, changes


def main() -> int:
    args = parse_args()
    if args.amendment_output.exists():
        raise FileExistsError(f"refusing to overwrite immutable amendment: {args.amendment_output}")

    preseal = json.loads(args.preseal.read_text(encoding="utf-8"))
    roster = read_jsonl(args.roster)
    before_sha = canonical_rows_sha256(roster)
    if before_sha != preseal["roster_sha256"]:
        raise RuntimeError(
            "R2 roster no longer matches the immutable preseal; refusing amendment "
            f"({before_sha} != {preseal['roster_sha256']})"
        )

    # Deliberately project only the released prompt fields.  No correct-answer
    # key is read or propagated by amend_roster_prompt_fields().
    source_items = json.loads(args.source.read_text(encoding="utf-8"))["items"]
    amended, changes = amend_roster_prompt_fields(roster, source_items)
    after_sha = canonical_rows_sha256(amended)
    write_jsonl(args.roster, amended)

    report = {
        "schema_version": "tstep-toc-r2-preseal-amendment-v0.2",
        "amendment_id": AMENDMENT_ID,
        "created_at": args.created_at,
        "decision": "PROMPT_COMPLETENESS_FIX_ONLY",
        "selection_changed": False,
        "sample_ids_or_order_changed": False,
        "replacement_allowed": False,
        "gold_fields_accessed_or_propagated": False,
        "original_preseal": str(args.preseal.relative_to(PROJECT_ROOT)).replace("\\", "/"),
        "original_roster_sha256": before_sha,
        "effective_roster_sha256": after_sha,
        "changed_rows": changes,
        "allowed_projection": ["events[].label", "events[].event_text"],
        "forbidden_projection": [
            "correct_order",
            "chronological_index",
            "event_id",
            "event_type",
            "correct_answer",
        ],
        "upstream_provenance": {
            "repository": UPSTREAM_REPOSITORY,
            "commit": UPSTREAM_COMMIT,
            "construction": (
                f"{UPSTREAM_REPOSITORY}/blob/{UPSTREAM_COMMIT}/"
                "scripts/step3b_build_skeletons.py#L509-L545"
            ),
            "release_projection": (
                f"{UPSTREAM_REPOSITORY}/blob/{UPSTREAM_COMMIT}/"
                "scripts/step5a_export_for_humans.py#L65-L80"
            ),
            "evaluation_prompt": (
                f"{UPSTREAM_REPOSITORY}/blob/{UPSTREAM_COMMIT}/eval_runner.py#L562-L570"
            ),
            "interpretation": (
                "events[].label and events[].event_text are shuffled prompt options; "
                "correct_order is the separately stored evaluator answer"
            ),
        },
    }
    args.amendment_output.parent.mkdir(parents=True, exist_ok=True)
    args.amendment_output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
