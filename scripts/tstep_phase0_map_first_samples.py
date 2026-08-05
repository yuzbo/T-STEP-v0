#!/usr/bin/env python3
"""Map the first remote Phase 0 records into the unified audit schema."""

from __future__ import annotations

import argparse
import ast
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tstep_v0.datasets import SCHEMA_VERSION, read_jsonl, validate_unified_sample, write_jsonl


COVERAGE_FIELDS = (
    "has_video",
    "has_question",
    "has_answer",
    "has_temporal_evidence",
    "has_bbox_or_track",
    "has_object_identity",
    "has_state_label",
    "has_transition_boundary",
    "has_relation_label",
    "has_counterfactual_label",
    "can_define_stable_state_variable",
    "requires_manual_state_annotation",
)
TOC_VIDEO_ROOT = "datasets/toc_bench_full/videos"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "first_real_samples_raw.jsonl",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "first_real_samples_unified.jsonl",
    )
    parser.add_argument(
        "--coverage-output",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "annotation_coverage_pilot.csv",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mapped = [map_record(record) for record in read_jsonl(args.input)]
    for sample in mapped:
        validate_unified_sample(sample)
    write_jsonl(args.output, mapped)
    write_coverage(args.coverage_output, mapped)
    print(
        json.dumps(
            {
                "sample_count": len(mapped),
                "dataset_counts": _counts(sample["dataset"] for sample in mapped),
                "mapping_status_counts": _counts(
                    sample["audit"]["mapping_status"] for sample in mapped
                ),
                "output": str(args.output),
                "coverage_output": str(args.coverage_output),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def map_record(record: Mapping[str, Any]) -> Dict[str, Any]:
    dataset = record["source_dataset"]
    if dataset == "VSTAT":
        return map_vstat(record)
    if dataset == "TOC-Bench":
        return map_toc(record)
    if dataset == "VidOSC":
        return map_vidosc(record)
    if dataset == "Moment-Video":
        return map_moment(record)
    raise ValueError(f"unsupported source_dataset: {dataset!r}")


def map_vstat(record: Mapping[str, Any]) -> Dict[str, Any]:
    raw = record["raw"]
    underlying_video_id = Path(raw["video_path"]).stem
    variable = (
        "possession_actor_count"
        if "possession" in raw["question"].lower()
        else "distinct_actor_count"
    )
    return base_sample(
        record,
        sample_id=f"VSTAT:audit:{raw['video_id']}",
        dataset="VSTAT",
        video={
            "video_id": underlying_video_id,
            "path_or_uri": raw["video_path"],
            "duration_sec": float(raw["end_sec"]) - float(raw["start_sec"]),
            "fps": 0.0,
            "frame_count": 0,
        },
        question={
            "question_id": raw["video_id"],
            "text": raw["question"],
            "type": "count",
            "answer_type": "number",
            "choices": raw["choices"],
            "gt_answer": raw["answer"],
            "gt_answer_normalized": str(raw["answer"]),
        },
        ledger_query={
            "query_type": "count",
            "target_time_sec": None,
            "target_event_id": None,
            "object_refs": ["foreground_players"],
            "variables": [variable],
            "relation_refs": [],
            "intervention": None,
        },
        coverage=coverage(
            has_video=False,
            has_question=True,
            has_answer=True,
            has_temporal_evidence=False,
            can_define_stable_state_variable=False,
            requires_manual_state_annotation=True,
        ),
        audit={
            "mapping_status": "blocked_semantic_mismatch",
            "blockers": [
                "referenced_video_absent",
                "no_object_tracks_or_persistent_ids",
                "distinct_actor_count_is_not_a_typed_state_transition",
            ],
            "video_source": raw["video_source"],
            "source_task": raw["source_task"],
            "state_structure": raw["state_structure"],
            "state_element_type": raw["state_element_type"],
        },
    )


def map_toc(record: Mapping[str, Any]) -> Dict[str, Any]:
    raw = record["raw"]
    metadata = raw["metadata"]
    is_count = raw["format"] == "numerical"
    if is_count:
        normalized_answer = str(raw["correct_answer"])
        answer_type = "number"
        query_type = "count"
        query_value = None
    else:
        normalized_answer = "true"
        answer_type = "boolean"
        query_type = "changed_to"
        query_value = "visible" if "enter the frame" in raw["question"] else "hidden"

    ledger_query = {
        "query_type": query_type,
        "target_time_sec": None,
        "target_event_id": None,
        "object_refs": [metadata["subject_label"]],
        "variables": ["visibility"],
        "relation_refs": [],
        "intervention": None,
    }
    if query_value is not None:
        ledger_query["value"] = query_value

    choices = raw.get("allowed_answers", [])
    if not choices and raw["format"] == "sp":
        choices = [raw["statement_A"], raw["statement_B"]]
    return base_sample(
        record,
        sample_id=f"TOC-Bench:audit:{raw['video_id']}:{raw['qa_id']}",
        dataset="TOC-Bench",
        video={
            "video_id": raw["video_id"],
            "path_or_uri": f"{TOC_VIDEO_ROOT}/{raw['video_id']}.mp4",
            "duration_sec": 0.0,
            "fps": 0.0,
            "frame_count": 0,
        },
        question={
            "question_id": raw["qa_id"],
            "text": raw["question"],
            "type": "count" if is_count else "evidence_control",
            "answer_type": answer_type,
            "choices": choices,
            "gt_answer": raw["correct_answer"],
            "gt_answer_normalized": normalized_answer,
        },
        ledger_query=ledger_query,
        objects=[
            {
                "object_id": metadata["subject_label"],
                "canonical_name": metadata["subject_label"],
                "aliases": [],
                "category": "unknown",
                "track_id": None,
                "first_visible_sec": None,
                "last_visible_sec": None,
                "track_quality": "missing",
                "attributes_static": {},
            }
        ],
        coverage=coverage(
            has_video=True,
            has_question=True,
            has_answer=True,
            has_object_identity=False,
            can_define_stable_state_variable=True,
            requires_manual_state_annotation=True,
        ),
        audit={
            "mapping_status": "needs_manual_transition_annotation",
            "blockers": [
                "no_temporal_evidence",
                "no_tracks_or_bboxes",
                "no_persistent_object_id",
                "no_state_or_transition_labels",
            ],
            "toc_dimension": metadata["dim"],
            "toc_tier": metadata["tier"],
            "raw_answer_encoding": raw["correct_answer"],
        },
    )


def map_vidosc(record: Mapping[str, Any]) -> Dict[str, Any]:
    raw = record["raw"]
    phase_intervals = {
        "initial": parse_intervals(raw["initial_state"]),
        "transitioning": parse_intervals(raw["transitioning_state"]),
        "end": parse_intervals(raw["end_state"]),
    }
    query_interval = phase_intervals["transitioning"][0]
    target_time = (query_interval[0] + query_interval[1]) / 2
    object_name = raw["osc"].split("_", maxsplit=1)[-1]
    states = []
    evidence = []
    for phase, intervals in phase_intervals.items():
        for index, (start, end) in enumerate(intervals):
            states.append(
                {
                    "object_id": object_name,
                    "variable": "osc_phase",
                    "value": phase,
                    "time_sec": start,
                    "start_sec": start,
                    "end_sec": end,
                    "confidence": 1.0,
                    "source": "gt_interval",
                    "source_event_id": f"{phase}_{index}",
                    "is_initial": False,
                }
            )
            evidence.append(
                {
                    "evidence_span_id": f"{phase}_{index}",
                    "start_sec": start,
                    "end_sec": end,
                    "object_ids": [object_name],
                    "score": 1.0,
                    "transition_critical": phase == "transitioning",
                }
            )

    return base_sample(
        record,
        sample_id=f"VidOSC:audit:{raw['video_name']}:phase",
        dataset="VidOSC",
        video={
            "video_id": raw["video_name"],
            "path_or_uri": "",
            "duration_sec": float(raw["duration"]),
            "fps": 0.0,
            "frame_count": 0,
        },
        question={
            "question_id": f"{raw['video_name']}:phase",
            "text": (
                f"What is the annotated OSC phase of {object_name} "
                f"at {target_time:.5f} seconds?"
            ),
            "type": "intermediate_state",
            "answer_type": "short_text",
            "choices": ["initial", "transitioning", "end"],
            "gt_answer": "transitioning",
            "gt_answer_normalized": "transitioning",
        },
        ledger_query={
            "query_type": "intermediate_state",
            "target_time_sec": target_time,
            "target_event_id": None,
            "object_refs": [object_name],
            "variables": ["osc_phase"],
            "relation_refs": [],
            "intervention": None,
        },
        objects=[
            {
                "object_id": object_name,
                "canonical_name": object_name,
                "aliases": [],
                "category": "state_change_object",
                "track_id": None,
                "first_visible_sec": None,
                "last_visible_sec": None,
                "track_quality": "missing",
                "attributes_static": {"osc": raw["osc"]},
            }
        ],
        states=states,
        evidence=evidence,
        coverage=coverage(
            has_video=False,
            has_question=True,
            has_answer=True,
            has_temporal_evidence=True,
            has_state_label=True,
            has_transition_boundary=True,
            can_define_stable_state_variable=True,
            requires_manual_state_annotation=False,
        ),
        audit={
            "mapping_status": "schema_ready_video_missing",
            "blockers": [
                "source_video_absent",
                "feature_tensors_absent",
                "interval_labels_are_states_not_typed_operators",
            ],
            "source_clip_start_sec": float(raw["start_time"]),
            "osc": raw["osc"],
            "is_novel_osc": raw["is_novel_osc"] == "True",
        },
    )


def map_moment(record: Mapping[str, Any]) -> Dict[str, Any]:
    raw = record["raw"]
    return base_sample(
        record,
        sample_id=f"Moment-Video:audit:{raw['Index']}",
        dataset="Moment-Video",
        video={
            "video_id": raw["Index"],
            "path_or_uri": "",
            "duration_sec": 0.0,
            "fps": 0.0,
            "frame_count": 0,
        },
        question={
            "question_id": raw["Index"],
            "text": raw["Question"],
            "type": "causal_dependency",
            "answer_type": "short_text",
            "choices": [],
            "gt_answer": raw["Answer"],
            "gt_answer_normalized": raw["Answer"].lower(),
        },
        ledger_query={
            "query_type": "final_state",
            "target_time_sec": None,
            "target_event_id": None,
            "object_refs": ["scene"],
            "variables": ["physical_consistency"],
            "relation_refs": [],
            "intervention": None,
        },
        coverage=coverage(
            has_video=False,
            has_question=True,
            has_answer=True,
            can_define_stable_state_variable=False,
            requires_manual_state_annotation=True,
        ),
        audit={
            "mapping_status": "blocked_open_ended_qa",
            "blockers": [
                "source_video_absent",
                "no_temporal_evidence",
                "no_object_or_state_labels",
                "open_ended_answer_not_directly_executable",
            ],
            "category": raw["Category"],
            "subclass": raw["Subclass"],
            "question_type": raw["QuestionType"],
        },
    )


def base_sample(
    source: Mapping[str, Any],
    *,
    sample_id: str,
    dataset: str,
    video: Mapping[str, Any],
    question: Mapping[str, Any],
    ledger_query: Mapping[str, Any],
    coverage: Mapping[str, bool],
    audit: Mapping[str, Any],
    objects: Sequence[Mapping[str, Any]] = (),
    states: Sequence[Mapping[str, Any]] = (),
    evidence: Sequence[Mapping[str, Any]] = (),
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "sample_id": sample_id,
        "dataset": dataset,
        "split": "phase0-first-sample-audit",
        "video": dict(video),
        "question": dict(question),
        "ledger_query": dict(ledger_query),
        "objects": list(objects),
        "events": [],
        "states": list(states),
        "relations": [],
        "evidence": list(evidence),
        "coverage": dict(coverage),
        "audit": {
            **dict(audit),
            "remote_source": source["remote_source"],
            "raw_source_dataset": source["source_dataset"],
            "audit_status": "pilot_not_manual_audit_50",
        },
    }


def coverage(**overrides: bool) -> Dict[str, bool]:
    flags = {field: False for field in COVERAGE_FIELDS}
    flags.update(overrides)
    return flags


def parse_intervals(value: str) -> List[List[float]]:
    rows = ast.literal_eval(value)
    return [[float(start), float(end)] for start, end in rows]


def write_coverage(path: Path, samples: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "sample_id",
        "dataset",
        *COVERAGE_FIELDS,
        "mapping_status",
        "blockers",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for sample in samples:
            writer.writerow(
                {
                    "sample_id": sample["sample_id"],
                    "dataset": sample["dataset"],
                    **sample["coverage"],
                    "mapping_status": sample["audit"]["mapping_status"],
                    "blockers": ";".join(sample["audit"]["blockers"]),
                }
            )


def _counts(values: Iterable[str]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


if __name__ == "__main__":
    raise SystemExit(main())
