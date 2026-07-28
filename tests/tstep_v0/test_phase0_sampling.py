from scripts.tstep_phase0_prepare_deep10 import uniform_frame_indices
from scripts.tstep_phase0_render_targeted_windows import timestamps


def test_uniform_frame_indices_include_both_video_boundaries():
    indices = uniform_frame_indices(total=101, frame_count=5)

    assert indices == [0, 25, 50, 75, 100]


def test_uniform_frame_indices_reject_impossible_sample_count():
    try:
        uniform_frame_indices(total=3, frame_count=4)
    except ValueError as error:
        assert "sample frame count" in str(error)
    else:
        raise AssertionError("expected invalid sample count to raise")


def test_targeted_timestamps_include_requested_end_boundary():
    values = timestamps(start_s=0.0, end_s=1.0, step_s=0.3)

    assert values[0] == 0.0
    assert values[-1] == 1.0
