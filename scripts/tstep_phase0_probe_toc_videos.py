#!/usr/bin/env python3
"""Decode TOC candidates locally and emit answer-blind contact sheets."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Tuple

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tstep_v0.sampling import (
    SAMPLER_VERSION,
    pts_tolerance_ms,
    validate_pts_observation,
    video_last_pts_ms,
)

FRAME_RATIOS = (0.05, 0.25, 0.5, 0.75, 0.95)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "toc_phase0_candidates_30.jsonl",
    )
    parser.add_argument(
        "--video-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "videos" / "toc_candidates_30",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "toc_phase0_candidates_30_probed.jsonl",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "toc_video_probe_report.json",
    )
    parser.add_argument(
        "--screening-csv",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "toc_video_screening_30.csv",
    )
    parser.add_argument(
        "--contact-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "phase0" / "contact_sheets" / "toc_candidates_30",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = [
        json.loads(line)
        for line in args.manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    args.contact_dir.mkdir(parents=True, exist_ok=True)
    probed = []
    probe_rows = []
    for row in rows:
        video_id = row["video"]["video_id"]
        video_path = args.video_dir / f"{video_id}.mp4"
        probe, frames = probe_video(video_path)
        contact_path = args.contact_dir / f"{video_id}.jpg"
        if frames:
            write_contact_sheet(contact_path, frames, row, probe)
            probe["contact_sheet_path"] = str(contact_path)
        else:
            probe["contact_sheet_path"] = None

        updated = json.loads(json.dumps(row))
        updated["video"].update(
            {
                "local_path": str(video_path),
                "decode_status": probe["decode_status"],
                "duration_ms": probe["duration_ms"],
                "fps": probe["fps"],
                "frame_count": probe["frame_count"],
                "sampled_frame_count": probe["sampled_frame_count"],
                "contact_sheet_path": probe["contact_sheet_path"],
            }
        )
        probed.append(updated)
        probe_rows.append({"video_id": video_id, **probe})

    write_jsonl(args.output, probed)
    write_screening_csv(args.screening_csv, probed)
    report = {
        "schema_version": "tstep-toc-video-probe-v0.1",
        "sampler_version": SAMPLER_VERSION,
        "candidate_count": len(probe_rows),
        "decoded_count": sum(row["decode_status"] == "ok" for row in probe_rows),
        "failed_count": sum(row["decode_status"] != "ok" for row in probe_rows),
        "probe_rows": probe_rows,
        "warning": (
            "Decode success is not ledger eligibility. Human answer-blind "
            "screening remains required."
        ),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                key: value
                for key, value in report.items()
                if key != "probe_rows"
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if report["failed_count"] == 0 else 2


def probe_video(path: Path) -> Tuple[Dict[str, Any], List[np.ndarray]]:
    if not path.exists() or path.stat().st_size == 0:
        return (
            {
                "decode_status": "missing",
                "file_size_bytes": 0,
                "fps": None,
                "frame_count": None,
                "duration_ms": None,
                "sampled_frame_count": 0,
            },
            [],
        )

    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        return (
            {
                "decode_status": "open_failed",
                "file_size_bytes": path.stat().st_size,
                "fps": None,
                "frame_count": None,
                "duration_ms": None,
                "sampled_frame_count": 0,
            },
            [],
        )

    fps = float(capture.get(cv2.CAP_PROP_FPS))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_ms = (
        video_last_pts_ms(frame_count, fps)
        if fps > 0 and frame_count > 0
        else None
    )
    frames = []
    frame_samples = []
    previous_actual_pts_ms = None
    if frame_count > 0:
        for ratio in FRAME_RATIOS:
            frame_index = min(frame_count - 1, max(0, round((frame_count - 1) * ratio)))
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame = capture.read()
            if ok and frame is not None and frame.size:
                # OpenCV/FFmpeg reports seconds immediately after a seek on
                # some files, but milliseconds after the requested frame has
                # actually been decoded.  Read first, then query POS_MSEC.
                reported_pts_ms = float(capture.get(cv2.CAP_PROP_POS_MSEC))
                frames.append(frame)
                derived_pts_ms = round(frame_index / fps * 1000)
                if math.isfinite(reported_pts_ms) and reported_pts_ms >= 0:
                    actual_pts_ms = round(reported_pts_ms)
                    pts_source = "decoder_reported"
                else:
                    actual_pts_ms = derived_pts_ms
                    pts_source = "fps_derived"
                pts_delta_ms = validate_pts_observation(
                    actual_pts_ms,
                    derived_pts_ms,
                    previous_actual_pts_ms=previous_actual_pts_ms,
                    fps=fps,
                )
                previous_actual_pts_ms = actual_pts_ms
                frame_samples.append(
                    {
                        "ratio": ratio,
                        "frame_index": frame_index,
                        "actual_pts_ms": actual_pts_ms,
                        "pts_source": pts_source,
                        "fps_derived_pts_ms": derived_pts_ms,
                        "pts_delta_ms": pts_delta_ms,
                        "pts_tolerance_ms": pts_tolerance_ms(fps),
                    }
                )
    capture.release()
    return (
        {
            "decode_status": "ok" if len(frames) == len(FRAME_RATIOS) else "partial",
            "file_size_bytes": path.stat().st_size,
            "fps": fps if fps > 0 else None,
            "frame_count": frame_count if frame_count > 0 else None,
            "duration_ms": duration_ms,
            "sampled_frame_count": len(frames),
            "sampler_version": SAMPLER_VERSION,
            "sampling_stage": "coarse_5_frame",
            "frame_samples": frame_samples,
        },
        frames,
    )


def write_contact_sheet(
    path: Path,
    frames: List[np.ndarray],
    row: Mapping[str, Any],
    probe: Mapping[str, Any],
) -> None:
    tiles = []
    for frame in frames:
        tiles.append(cv2.resize(frame, (320, 180), interpolation=cv2.INTER_AREA))
    body = np.hstack(tiles)
    header = np.full((92, body.shape[1], 3), 245, dtype=np.uint8)
    metadata = row["source_metadata"]
    lines = [
        (
            f"{row['video']['video_id']} | {metadata['dim']} | "
            f"{metadata['tier']} | {probe['duration_ms']} ms"
        ),
        f"Subject: {metadata['subject_label']}",
        f"Q: {row['question']['text'][:180]}",
    ]
    for index, text in enumerate(lines):
        cv2.putText(
            header,
            text,
            (12, 24 + index * 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            (20, 20, 20),
            1,
            cv2.LINE_AA,
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded_ok, encoded = cv2.imencode(".jpg", np.vstack([header, body]))
    if not encoded_ok:
        raise RuntimeError(f"failed to encode contact sheet: {path}")
    encoded.tofile(str(path))


def write_screening_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    fieldnames = [
        "sample_id",
        "video_id",
        "dim",
        "tier",
        "subject_label",
        "contact_sheet_path",
        "subject_visible",
        "state_or_relation_change_visible",
        "static_frame_sufficient",
        "multi_instance_interference",
        "transition_dependent",
        "ledger_critical_status",
        "deep_annotation_eligible",
        "exclusion_reason",
        "reviewer",
        "review_confidence",
        "notes",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            metadata = row["source_metadata"]
            writer.writerow(
                {
                    "sample_id": row["sample_id"],
                    "video_id": row["video"]["video_id"],
                    "dim": metadata["dim"],
                    "tier": metadata["tier"],
                    "subject_label": metadata["subject_label"],
                    "contact_sheet_path": row["video"]["contact_sheet_path"],
                    "ledger_critical_status": "requires_video_review",
                }
            )


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
