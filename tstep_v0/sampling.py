"""Versioned sampling primitives for the Phase 0 four-stage review protocol."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Dict, List


SAMPLER_VERSION = "tstep-four-stage-sampler-v0.2.2"


@dataclass(frozen=True)
class FrameSample:
    frame_index: int
    requested_pts_ms: int
    actual_pts_ms: int
    pts_source: str
    endpoint_role: str | None = None

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def video_last_pts_ms(frame_count: int, fps: float) -> int:
    if frame_count <= 0 or fps <= 0:
        raise ValueError("frame_count and fps must be positive")
    return round((frame_count - 1) / fps * 1000)


def uniform_frame_indices(total: int, frame_count: int) -> List[int]:
    """Uniform integer frame indices with exact first/last inclusion."""

    if total <= 0:
        raise ValueError("total frame count must be positive")
    if frame_count <= 0 or frame_count > total:
        raise ValueError("sample frame count must be in [1, total]")
    if frame_count == 1:
        return [0]
    indices = [
        round(index * (total - 1) / (frame_count - 1))
        for index in range(frame_count)
    ]
    if len(indices) != len(set(indices)):
        raise ValueError("uniform sampling produced duplicate frame indices")
    indices[0] = 0
    indices[-1] = total - 1
    return indices


def inclusive_timestamps_ms(
    start_ms: int,
    end_ms: int,
    step_ms: int,
    *,
    allow_single_frame: bool = False,
) -> List[int]:
    """Return an endpoint-inclusive PTS request grid."""

    if start_ms < 0 or end_ms < start_ms or step_ms <= 0:
        raise ValueError(
            f"invalid window start={start_ms}, end={end_ms}, step={step_ms}"
        )
    if start_ms == end_ms:
        if allow_single_frame:
            return [start_ms]
        raise ValueError("zero-length window requires allow_single_frame=True")
    values = list(range(start_ms, end_ms + 1, step_ms))
    if values[-1] != end_ms:
        values.append(end_ms)
    return values


def nearest_frame_index(requested_pts_ms: int, frame_count: int, fps: float) -> int:
    if requested_pts_ms < 0:
        raise ValueError("requested PTS must be non-negative")
    last_pts = video_last_pts_ms(frame_count, fps)
    clamped = min(requested_pts_ms, last_pts)
    return min(frame_count - 1, max(0, round(clamped / 1000.0 * fps)))


def pts_tolerance_ms(fps: float) -> int:
    """Maximum decoder-vs-index PTS drift accepted without manual review."""

    if fps <= 0:
        raise ValueError("fps must be positive")
    return max(5, math.ceil(2000.0 / fps))


def validate_pts_observation(
    actual_pts_ms: int,
    fps_derived_pts_ms: int,
    *,
    previous_actual_pts_ms: int | None,
    fps: float,
) -> int:
    """Validate monotonic decoder PTS and return decoder/index delta.

    A seek may legitimately land within a frame or two of an FPS-derived
    timestamp.  Larger drift is not silently labelled exact: the sampling run
    stops so the clip can be handled as a variable-frame-rate/manual case.
    """

    if actual_pts_ms < 0 or fps_derived_pts_ms < 0:
        raise ValueError("PTS values must be non-negative")
    if previous_actual_pts_ms is not None and actual_pts_ms < previous_actual_pts_ms:
        raise ValueError("decoded PTS sequence must be monotonic")
    delta_ms = actual_pts_ms - fps_derived_pts_ms
    tolerance_ms = pts_tolerance_ms(fps)
    if abs(delta_ms) > tolerance_ms:
        raise ValueError(
            "decoder PTS differs from FPS-derived PTS beyond tolerance: "
            f"delta={delta_ms}ms tolerance={tolerance_ms}ms"
        )
    return delta_ms
