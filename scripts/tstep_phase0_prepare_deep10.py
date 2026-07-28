#!/usr/bin/env python3
"""Merge blind screening, select a stratified deep-10, and render dense sheets."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SELECTION_QUOTAS = {
    "conditional_state": 2,
    "relative_spatial_change": 1,
    "reappear_or_disappear": 1,
    "reappear_identity": 2,
    "event_ordering": 2,
    "cross_object_order": 2,
}
ALLOWED_SCREENING_VALUES = {"yes", "no", "unclear"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=PROJECT_ROOT
        / "data"
        / "phase0"
        / "toc_phase0_candidates_30_probed.jsonl",
    )
    parser.add_argument(
        "--screening",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "toc_video_screening_30.json",
    )
    parser.add_argument(
        "--screened-output",
        type=Path,
        default=PROJECT_ROOT
        / "data"
        / "phase0"
        / "toc_phase0_candidates_30_screened.jsonl",
    )
    parser.add_argument(
        "--deep10-output",
        type=Path,
        default=PROJECT_ROOT
        / "data"
        / "phase0"
        / "toc_phase0_deep10_candidates.jsonl",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "toc_deep10_selection_report.json",
    )
    parser.add_argument(
        "--dense-contact-dir",
        type=Path,
        default=PROJECT_ROOT
        / "data"
        / "phase0"
        / "contact_sheets"
        / "toc_deep10_dense",
    )
    parser.add_argument("--frame-count", type=int, default=24)
    parser.add_argument("--frames-per-sheet", type=int, default=12)
    return parser.parse_args()


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def validate_inputs(
    candidates: Sequence[Mapping[str, Any]],
    screening_document: Mapping[str, Any],
) -> Dict[str, Mapping[str, Any]]:
    screening_rows = screening_document.get("rows", [])
    if screening_document.get("gold_accessed") is not False:
        raise ValueError("screening document must explicitly assert gold_accessed=false")
    if len(candidates) != 30 or len(screening_rows) != 30:
        raise ValueError("Phase 0 coarse screen requires exactly 30 candidate/result rows")

    candidate_ids = [row["sample_id"] for row in candidates]
    screening_ids = [row["sample_id"] for row in screening_rows]
    if len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError("candidate sample IDs must be unique")
    if len(set(screening_ids)) != len(screening_ids):
        raise ValueError("screening sample IDs must be unique")
    if set(candidate_ids) != set(screening_ids):
        missing = sorted(set(candidate_ids) - set(screening_ids))
        extra = sorted(set(screening_ids) - set(candidate_ids))
        raise ValueError(f"screening mismatch: missing={missing}, extra={extra}")

    for candidate in candidates:
        blindness = candidate.get("blindness", {})
        if blindness.get("gold_answer_present") is not False:
            raise ValueError(f"candidate is not answer blind: {candidate['sample_id']}")
    for row in screening_rows:
        for field in (
            "subject_visible",
            "state_or_relation_change_visible",
            "static_frame_sufficient",
            "multi_instance_interference",
            "transition_dependent",
        ):
            if row.get(field) not in ALLOWED_SCREENING_VALUES:
                raise ValueError(
                    f"invalid {field}={row.get(field)!r} for {row['sample_id']}"
                )
        if row.get("ledger_critical_status") not in {
            "likely",
            "uncertain",
            "unsuitable",
        }:
            raise ValueError(f"invalid ledger status for {row['sample_id']}")
        if row.get("deep_annotation_eligible") not in ALLOWED_SCREENING_VALUES:
            raise ValueError(f"invalid eligibility for {row['sample_id']}")
        confidence = row.get("review_confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            raise ValueError(f"invalid confidence for {row['sample_id']}")
    return {row["sample_id"]: row for row in screening_rows}


def merge_screening(
    candidates: Sequence[Mapping[str, Any]],
    screening_by_id: Mapping[str, Mapping[str, Any]],
    stage: str,
) -> List[Dict[str, Any]]:
    merged = []
    for candidate in candidates:
        row = json.loads(json.dumps(candidate))
        result = screening_by_id[row["sample_id"]]
        row["screening"] = {
            **row.get("screening", {}),
            **{
                key: value
                for key, value in result.items()
                if key not in {"sample_id"}
            },
            "screening_stage": stage,
            "gold_accessed": False,
        }
        merged.append(row)
    return merged


def rank_key(row: Mapping[str, Any]) -> tuple:
    screening = row["screening"]
    return (
        -float(screening["review_confidence"]),
        screening["multi_instance_interference"] != "no",
        row["sample_id"],
    )


def select_deep10(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    for dimension, target in SELECTION_QUOTAS.items():
        pool = [
            row
            for row in rows
            if row["source_metadata"]["dim"] == dimension
            and row["screening"]["ledger_critical_status"] == "likely"
            and row["screening"]["deep_annotation_eligible"] == "yes"
            and row["screening"]["static_frame_sufficient"] == "no"
            and row["screening"]["transition_dependent"] == "yes"
        ]
        ranked = sorted(pool, key=rank_key)
        if len(ranked) < target:
            raise ValueError(
                f"deep-10 quota not met for {dimension}: need {target}, have {len(ranked)}"
            )
        for row in ranked[:target]:
            copied = json.loads(json.dumps(row))
            copied["deep10_selection"] = {
                "selected": True,
                "selection_stage": "dense_temporal_review_pending",
                "dimension_quota": target,
                "rank_basis": [
                    "ledger_critical_status=likely",
                    "deep_annotation_eligible=yes",
                    "static_frame_sufficient=no",
                    "transition_dependent=yes",
                    "review_confidence_desc",
                    "prefer_no_multi_instance_interference",
                ],
            }
            selected.append(copied)
    if len(selected) != 10:
        raise AssertionError(f"expected 10 selected rows, got {len(selected)}")
    if len({row["video"]["video_id"] for row in selected}) != 10:
        raise AssertionError("deep-10 must contain ten unique videos")
    return selected


def sample_dense_frames(
    video_path: Path,
    frame_count: int,
) -> List[tuple[int, float, np.ndarray]]:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"cannot open video: {video_path}")
    total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    if total <= 0 or fps <= 0:
        capture.release()
        raise RuntimeError(f"invalid video metadata: {video_path}")

    indices = uniform_frame_indices(total, frame_count)
    frames = []
    for frame_index in indices:
        capture.set(cv2.CAP_PROP_POS_FRAMES, int(frame_index))
        ok, frame = capture.read()
        if not ok or frame is None or not frame.size:
            capture.release()
            raise RuntimeError(f"decode failed at frame {frame_index}: {video_path}")
        frames.append((int(frame_index), frame_index / fps, frame))
    capture.release()
    return frames


def uniform_frame_indices(total: int, frame_count: int) -> List[int]:
    """Return uniformly spaced indices including the first and last frame."""
    if total <= 0:
        raise ValueError("total frame count must be positive")
    if frame_count <= 0 or frame_count > total:
        raise ValueError("sample frame count must be in [1, total]")
    if frame_count == 1:
        return [0]
    # Boundary events are disproportionately likely to occur at video
    # start/end, so interior-only uniform sampling is unsafe.
    return [int(index) for index in np.linspace(0, total - 1, num=frame_count)]


def render_dense_sheets(
    row: Dict[str, Any],
    output_dir: Path,
    frame_count: int,
    frames_per_sheet: int,
) -> List[str]:
    if frames_per_sheet <= 0 or frames_per_sheet % 4:
        raise ValueError("frames-per-sheet must be a positive multiple of four")
    local_path = Path(row["video"]["local_path"])
    frames = sample_dense_frames(local_path, frame_count)
    video_id = row["video"]["video_id"]
    output_paths = []
    for page_index, start in enumerate(range(0, len(frames), frames_per_sheet), 1):
        page_frames = frames[start : start + frames_per_sheet]
        tiles = []
        for frame_index, timestamp_s, frame in page_frames:
            resized = cv2.resize(frame, (320, 180), interpolation=cv2.INTER_AREA)
            label = np.full((24, 320, 3), 245, dtype=np.uint8)
            cv2.putText(
                label,
                f"frame={frame_index}  t={timestamp_s:.2f}s",
                (8, 17),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (20, 20, 20),
                1,
                cv2.LINE_AA,
            )
            tiles.append(np.vstack([label, resized]))
        while len(tiles) % 4:
            tiles.append(np.full_like(tiles[0], 245))
        body = np.vstack(
            [
                np.hstack(tiles[index : index + 4])
                for index in range(0, len(tiles), 4)
            ]
        )
        header = np.full((82, body.shape[1], 3), 245, dtype=np.uint8)
        header_lines = [
            (
                f"{video_id} | {row['source_metadata']['dim']} | "
                f"dense page {page_index}"
            ),
            f"Q: {row['question']['text'][:170]}",
        ]
        for line_index, text in enumerate(header_lines):
            cv2.putText(
                header,
                text,
                (10, 27 + line_index * 32),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.52,
                (20, 20, 20),
                1,
                cv2.LINE_AA,
            )
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{video_id}_p{page_index:02d}.jpg"
        ok, encoded = cv2.imencode(".jpg", np.vstack([header, body]))
        if not ok:
            raise RuntimeError(f"failed to encode dense sheet: {output_path}")
        encoded.tofile(str(output_path))
        output_paths.append(str(output_path))
    return output_paths


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    args = parse_args()
    if args.frame_count < 12:
        raise ValueError("dense review requires at least 12 frames per video")

    candidates = load_jsonl(args.manifest)
    screening_document = json.loads(args.screening.read_text(encoding="utf-8"))
    screening_by_id = validate_inputs(candidates, screening_document)
    screened = merge_screening(
        candidates,
        screening_by_id,
        screening_document["screening_stage"],
    )
    selected = select_deep10(screened)

    for row in selected:
        row["video"]["dense_contact_sheet_paths"] = render_dense_sheets(
            row,
            args.dense_contact_dir,
            args.frame_count,
            args.frames_per_sheet,
        )

    write_jsonl(args.screened_output, screened)
    write_jsonl(args.deep10_output, selected)
    report = {
        "schema_version": "tstep-toc-deep10-selection-v0.1",
        "gold_accessed": False,
        "coarse_screen_count": len(screened),
        "coarse_status_counts": dict(
            Counter(row["screening"]["ledger_critical_status"] for row in screened)
        ),
        "coarse_eligibility_counts": dict(
            Counter(row["screening"]["deep_annotation_eligible"] for row in screened)
        ),
        "selected_count": len(selected),
        "selected_by_dim": dict(
            Counter(row["source_metadata"]["dim"] for row in selected)
        ),
        "selection_quotas": SELECTION_QUOTAS,
        "selected_sample_ids": [row["sample_id"] for row in selected],
        "dense_frame_count_per_video": args.frame_count,
        "dense_review_status": "pending",
        "warning": (
            "The deep-10 is a stratified shortlist, not an accepted annotation set. "
            "Dense answer-blind temporal review remains required."
        ),
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
