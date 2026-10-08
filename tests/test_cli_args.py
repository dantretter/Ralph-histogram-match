import numpy as np
import pytest

from lumamatch.cli import build_parser, main
from lumamatch.io_image import save_rgb


def test_defaults():
    args = build_parser().parse_args(["a.png", "b.png"])

    assert args.bins == 256
    assert args.quality == 95
    assert args.force is False
    assert args.quiet is False


def test_bins_override():
    args = build_parser().parse_args(["a.png", "b.png", "--bins", "512"])

    assert args.bins == 512


@pytest.mark.parametrize("value", ["1", "0", "-5"])
def test_bins_below_minimum_rejected(value):
    with pytest.raises(SystemExit) as exc_info:
        build_parser().parse_args(["a.png", "b.png", "--bins", value])

    assert exc_info.value.code == 2


def test_quality_above_maximum_rejected():
    with pytest.raises(SystemExit) as exc_info:
        build_parser().parse_args(["a.png", "b.png", "--quality", "101"])

    assert exc_info.value.code == 2


def test_missing_positionals_rejected():
    with pytest.raises(SystemExit) as exc_info:
        build_parser().parse_args([])

    assert exc_info.value.code == 2


def test_force_and_quiet_flags():
    args = build_parser().parse_args(["a.png", "b.png", "--force", "--quiet"])

    assert args.force is True
    assert args.quiet is True


def _gradient_image(seed: int, shape: tuple[int, int] = (16, 16)) -> np.ndarray:
    rng = np.random.default_rng(seed)
    h, w = shape
    ramp = np.linspace(0, 255, w, dtype=np.float64)
    gray = np.tile(ramp, (h, 1))
    tint = rng.integers(0, 60, size=(h, w, 3)).astype(np.float64)
    return np.clip(gray[..., None] + tint, 0, 255).astype(np.uint8)


def test_main_runs_pipeline_and_returns_zero(tmp_path, capsys):
    reference_path = tmp_path / "reference.png"
    target_path = tmp_path / "subject.png"
    save_rgb(reference_path, _gradient_image(seed=0))
    save_rgb(target_path, _gradient_image(seed=1))

    exit_code = main([str(reference_path), str(target_path)])
    capsys.readouterr()

    assert exit_code == 0
    assert (tmp_path / "subject_matched.png").exists()
    assert (tmp_path / "subject_histograms.csv").exists()
