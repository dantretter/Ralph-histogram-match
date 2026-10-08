import numpy as np
import pytest

from lumamatch.color import srgb_to_lab
from lumamatch.io_image import load_rgb, save_rgb
from lumamatch.pipeline import match_luminance


def _gradient_image(seed: int, shape: tuple[int, int] = (32, 32)) -> np.ndarray:
    """Build a synthetic RGB image with a smooth luminance gradient plus color."""
    rng = np.random.default_rng(seed)
    h, w = shape
    ramp = np.linspace(0, 255, w, dtype=np.float64)
    gray = np.tile(ramp, (h, 1))
    tint = rng.integers(0, 60, size=(h, w, 3)).astype(np.float64)
    rgb = np.clip(gray[..., None] + tint, 0, 255).astype(np.uint8)
    return rgb


@pytest.fixture
def image_pair(tmp_path):
    reference_path = tmp_path / "reference.png"
    target_path = tmp_path / "subject.png"

    save_rgb(reference_path, _gradient_image(seed=0))
    save_rgb(target_path, _gradient_image(seed=1))

    return reference_path, target_path


def test_match_luminance_reduces_emd(image_pair):
    reference_path, target_path = image_pair

    result = match_luminance(reference_path, target_path)

    assert result.emd_after < result.emd_before
    assert result.bins == 256


def test_match_luminance_writes_both_outputs(image_pair):
    reference_path, target_path = image_pair

    result = match_luminance(reference_path, target_path)

    assert result.image_out.exists()
    assert result.csv_out.exists()


def test_match_luminance_output_matches_target_dimensions(image_pair):
    reference_path, target_path = image_pair
    target_rgb = load_rgb(target_path)

    result = match_luminance(reference_path, target_path)
    out_rgb = load_rgb(result.image_out)

    assert out_rgb.shape == target_rgb.shape


def test_match_luminance_preserves_ab_channels(image_pair):
    reference_path, target_path = image_pair
    target_rgb = load_rgb(target_path)
    target_lab = srgb_to_lab(target_rgb)

    result = match_luminance(reference_path, target_path)
    out_lab = srgb_to_lab(load_rgb(result.image_out))

    # Only approximate after an 8-bit RGB round-trip through the tone-mapped
    # L*, since a*/b* are recomputed from clipped/quantized RGB rather than
    # copied verbatim; the exact identity holds in the pipeline's internal
    # Lab arrays, which this black-box test cannot observe directly.
    assert np.abs(out_lab[..., 1] - target_lab[..., 1]).mean() < 2.0
    assert np.abs(out_lab[..., 2] - target_lab[..., 2]).mean() < 2.0


def test_match_luminance_overwrite_guard_blocks_before_writing(image_pair):
    reference_path, target_path = image_pair

    first = match_luminance(reference_path, target_path)
    image_mtime = first.image_out.stat().st_mtime_ns
    csv_mtime = first.csv_out.stat().st_mtime_ns

    with pytest.raises(FileExistsError):
        match_luminance(reference_path, target_path)

    assert first.image_out.stat().st_mtime_ns == image_mtime
    assert first.csv_out.stat().st_mtime_ns == csv_mtime


def test_match_luminance_force_overwrites(image_pair):
    reference_path, target_path = image_pair

    match_luminance(reference_path, target_path)
    result = match_luminance(reference_path, target_path, force=True)

    assert result.image_out.exists()
    assert result.csv_out.exists()
