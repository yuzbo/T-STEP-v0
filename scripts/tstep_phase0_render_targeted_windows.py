#!/usr/bin/env python3
"""Render high-density, answer-blind temporal windows for boundary review."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Mapping

import cv2
import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--spec",
        type=Path,
        default=PROJECT_ROOT
        / "data"
        / "phase0"
        / "toc_deep10_targeted_windows.json",
    )
    parser.add_argument(
        "--video-dir",
        type=Path,
        default=PROJECT_ROOT
        / "data"
        / "phase0"
        / "videos"
        / "toc_candidates_30",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT
        / "data"
        / "phase0"
        / "contact_sheets"
        / "toc_deep10_targeted",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=PROJECT_ROOT
        / "data"
        / "phase0"
        / "toc_deep10_targeted_render_report.json",
    )
    parser.add_argument("--frames-per-page", type=int, default=16)
    return parser.parse_args()


def timestamps(start_s: float, end_s: float, step_s: float) -> List[float]:
    if start_s < 0 or end_s < start_s or step_s <= 0:
        raise ValueError(
            f"invalid window start={start_s}, end={end_s}, step={step_s}"
        )
    count = int(np.floor((end_s - start_s) / step_s + 1e-9))
    values = [round(start_s + index * step_s, 6) for index in range(count + 1)]
    if not values or values[-1] < end_s - step_s * 0.25:
        values.append(end_s)
    return values


def decode_at_times(
    video_path: Path,
    requested_times: List[float],
) -> tuple[List[Dict[str, Any]], float]:
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise RuntimeError(f"cannot open video: {video_path}")
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    if fps <= 0 or frame_count <= 0:
        capture.release()
        raise RuntimeError(f"invalid video metadata: {video_path}")
    duration_s = frame_count / fps
    decoded = []
    for requested_s in requested_times:
        clamped_s = min(max(0.0, requested_s), max(0.0, duration_s - 1 / fps))
        frame_index = min(frame_count - 1, max(0, round(clamped_s * fps)))
        capture.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = capture.read()
        if not ok or frame is None or not frame.size:
            capture.release()
            raise RuntimeError(
                f"decode failed at t={requested_s:.3f}s frame={frame_index}: "
                f"{video_path}"
            )
        decoded.append(
            {
                "requested_s": requested_s,
                "actual_s": frame_index / fps,
                "frame_index": frame_index,
                "frame": frame,
            }
        )
    capture.release()
    return decoded, duration_s


def render_pages(
    output_dir: Path,
    video_id: str,
    window: Mapping[str, Any],
    decoded: List[Dict[str, Any]],
    frames_per_page: int,
) -> List[str]:
    if frames_per_page <= 0 or frames_per_page % 4:
        raise ValueError("frames-per-page must be a positive multiple of four")
    paths = []
    label = str(window["label"])
    for page_index, start in enumerate(range(0, len(decoded), frames_per_page), 1):
        page = decoded[start : start + frames_per_page]
        tiles = []
        for item in page:
            frame = cv2.resize(
                item["frame"], (320, 180), interpolation=cv2.INTER_AREA
            )
            caption = np.full((25, 320, 3), 245, dtype=np.uint8)
            cv2.putText(
                caption,
                (
                    f"t={item['actual_s']:.2f}s "
                    f"frame={item['frame_index']}"
                ),
                (8, 18),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (20, 20, 20),
                1,
                cv2.LINE_AA,
            )
            tiles.append(np.vstack([caption, frame]))
        while len(tiles) % 4:
            tiles.append(np.full_like(tiles[0], 245))
        body = np.vstack(
            [
                np.hstack(tiles[index : index + 4])
                for index in range(0, len(tiles), 4)
            ]
        )
        header = np.full((52, body.shape[1], 3), 245, dtype=np.uint8)
        cv2.putText(
            header,
            f"{video_id} | {label} | page {page_index}",
            (10, 32),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (20, 20, 20),
            1,
            cv2.LINE_AA,
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{video_id}__{label}__p{page_index:02d}.jpg"
        ok, encoded = cv2.imencode(".jpg", np.vstack([header, body]))
        if not ok:
            raise RuntimeError(f"failed to encode sheet: {output_path}")
        encoded.tofile(str(output_path))
        paths.append(str(output_path))
    return paths


def main() -> int:
    args = parse_args()
    document = json.loads(args.spec.read_text(encoding="utf-8"))
    if document.get("gold_accessed") is not False:
        raise ValueError("targeted-window spec must assert gold_accessed=false")
    seen_video_ids = set()
    report_rows = []
    for row in document["rows"]:
        video_id = row["video_id"]
        if video_id in seen_video_ids:
            raise ValueError(f"duplicate video_id: {video_id}")
        seen_video_ids.add(video_id)
        video_path = args.video_dir / f"{video_id}.mp4"
        window_reports = []
        for window in row["windows"]:
            requested = timestamps(
                float(window["start_s"]),
                float(window["end_s"]),
                float(window["step_s"]),
            )
            decoded, duration_s = decode_at_times(video_path, requested)
            paths = render_pages(
                args.output_dir,
                video_id,
                window,
                decoded,
                args.frames_per_page,
            )
            window_reports.append(
                {
                    **window,
                    "video_duration_s": duration_s,
                    "decoded_frame_count": len(decoded),
                    "page_paths": paths,
                }
            )
        report_rows.append({"video_id": video_id, "windows": window_reports})

    report = {
        "schema_version": "tstep-targeted-window-render-v0.1",
        "gold_accessed": False,
        "video_count": len(report_rows),
        "window_count": sum(len(row["windows"]) for row in report_rows),
        "decoded_frame_count": sum(
            window["decoded_frame_count"]
            for row in report_rows
            for window in row["windows"]
        ),
        "rows": report_rows,
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
                if key != "rows"
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
