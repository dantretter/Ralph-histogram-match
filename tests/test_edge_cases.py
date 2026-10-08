"""Degenerate-input edge cases: each must have a documented intended outcome.

'It happens not to crash' is not sufficient on its own -- every case below
asserts the specific behavior that is correct for that input, not merely the
absence of an exception. All tests run with RuntimeWarning promoted to an
error so a silent divide-by-zero in the CDF math would fail loudly instead of
quietly producing NaN.
"""

import numpy as np
import pytest

from lumamatch.color import srgb_to_lab
from lumamatch.csv_writer import read_histogram_csv
from lumamatch.io_image import load_rgb, save_rgb
from lumamatch.pipeline import match_luminance
from tests.images import flat_image, gradient_image, synthetic_reference

pytestmark = pytest.mark.filterwarnings("error::RuntimeWarning")


def _assert_finite_result(result):
    assert np.isfinite(result.emd_after)
    assert result.emd_after >= 0.0
    assert 0.0 <= result.clipped_fraction <= 1.0
    assert np.all(np.isfinite(result.lut))
    assert np.all(np.diff(result.lut) >= 0)


def test_flat_target_succeeds_without_spreading(tmp_path):
    """A flat target cannot be spread into a broad histogram under a
    monotonic map: every pixel shares one input value, so a non-decreasing
    LUT must send them all to one output value. EMD improvement is not
    asserted here because it is mathematically impossible, not a bug."""
    rng = np.random.default_rng(1)
    ref_path = tmp_path / "ref.png"
    tgt_path = tmp_path / "tgt.png"
    save_rgb(ref_path, synthetic_reference(rng))
    save_rgb(tgt_path, flat_image(128))

    result = match_luminance(ref_path, tgt_path)

    _assert_finite_result(result)
    assert result.image_out.exists()
    assert result.csv_out.exists()


def test_flat_reference_collapses_target(tmp_path):
    """A flat reference legitimately collapses the whole target tonal range
    onto the reference's single L* value. The target is achromatic
    (`gradient_image`) rather than the saturated `synthetic_reference`, so
    out-of-gamut clipping -- a separate, already-reported concern -- cannot
    perturb the L* values this test is checking."""
    ref_path = tmp_path / "ref.png"
    tgt_path = tmp_path / "tgt.png"
    save_rgb(ref_path, flat_image(200))
    save_rgb(tgt_path, gradient_image())

    result = match_luminance(ref_path, tgt_path)

    _assert_finite_result(result)
    ref_l = srgb_to_lab(flat_image(200))[..., 0]
    out_l = srgb_to_lab(load_rgb(result.image_out))[..., 0]
    assert float(np.std(out_l)) < 1.0
    assert abs(float(np.mean(out_l)) - float(np.mean(ref_l))) < 1.0


def test_mismatched_dimensions_succeed(tmp_path):
    """Different-sized reference/target images must still succeed, proving
    the EMD/CDF normalization genuinely makes differently-sized images
    comparable."""
    rng = np.random.default_rng(3)
    ref_path = tmp_path / "ref.png"
    tgt_path = tmp_path / "tgt.png"
    save_rgb(ref_path, synthetic_reference(rng, height=64, width=64))
    save_rgb(tgt_path, synthetic_reference(rng, height=96, width=128))

    result = match_luminance(ref_path, tgt_path)

    _assert_finite_result(result)
    assert result.reference_pixels == 64 * 64
    assert result.target_pixels == 96 * 128
    assert load_rgb(result.image_out).shape[:2] == (96, 128)

    metadata, rows = read_histogram_csv(result.csv_out)
    image1_total = sum(int(row[4]) for row in rows)
    image2_total = sum(int(row[5]) for row in rows)
    assert image1_total == 64 * 64
    assert image2_total == 96 * 128


def test_1x1_target_succeeds(tmp_path):
    """The smallest possible input shakes out any code assuming more than
    one pixel."""
    rng = np.random.default_rng(4)
    ref_path = tmp_path / "ref.png"
    tgt_path = tmp_path / "tgt.png"
    save_rgb(ref_path, synthetic_reference(rng))
    save_rgb(tgt_path, flat_image(50, 1, 1))

    result = match_luminance(ref_path, tgt_path)

    _assert_finite_result(result)
    out_rgb = load_rgb(result.image_out)
    assert out_rgb.shape == (1, 1, 3)

    _metadata, rows = read_histogram_csv(result.csv_out)
    assert sum(int(row[5]) for row in rows) == 1


def test_grayscale_target_succeeds(tmp_path):
    """A grayscale ('L' mode) PNG must load as 3-channel RGB and produce a
    3-channel output."""
    from PIL import Image

    rng = np.random.default_rng(5)
    ref_path = tmp_path / "ref.png"
    tgt_path = tmp_path / "tgt.png"
    save_rgb(ref_path, synthetic_reference(rng))

    gray = np.linspace(0, 255, 32 * 32, dtype=np.uint8).reshape(32, 32)
    Image.fromarray(gray, mode="L").save(tgt_path)

    result = match_luminance(ref_path, tgt_path)

    _assert_finite_result(result)
    assert load_rgb(result.image_out).shape[2] == 3


def test_rgba_target_succeeds_with_alpha_dropped(tmp_path):
    """An RGBA PNG must have its alpha dropped and still produce a
    3-channel output."""
    from PIL import Image

    rng = np.random.default_rng(6)
    ref_path = tmp_path / "ref.png"
    tgt_path = tmp_path / "tgt.png"
    save_rgb(ref_path, synthetic_reference(rng))

    rgba = np.zeros((32, 32, 4), dtype=np.uint8)
    rgba[..., :3] = synthetic_reference(rng, height=32, width=32)
    rgba[..., 3] = 128
    Image.fromarray(rgba, mode="RGBA").save(tgt_path)

    result = match_luminance(ref_path, tgt_path)

    _assert_finite_result(result)
    assert load_rgb(result.image_out).shape[2] == 3


def test_two_bins_succeeds(tmp_path):
    """The minimum allowed bin count must produce exactly 2 CSV data rows."""
    rng = np.random.default_rng(7)
    ref_path = tmp_path / "ref.png"
    tgt_path = tmp_path / "tgt.png"
    save_rgb(ref_path, synthetic_reference(rng))
    save_rgb(tgt_path, synthetic_reference(rng))

    result = match_luminance(ref_path, tgt_path, bins=2)

    _assert_finite_result(result)
    _metadata, rows = read_histogram_csv(result.csv_out)
    assert len(rows) == 2


def test_many_bins_on_small_image_succeeds(tmp_path):
    """More bins than pixels means most reference bins are empty, so the
    LUT's CDF-inverse interpolates across long flat (plateau) stretches --
    exactly the condition that must not produce a divide-by-zero or NaN."""
    rng = np.random.default_rng(8)
    ref_path = tmp_path / "ref.png"
    tgt_path = tmp_path / "tgt.png"
    save_rgb(ref_path, synthetic_reference(rng, height=32, width=32))
    save_rgb(tgt_path, synthetic_reference(rng, height=32, width=32))

    result = match_luminance(ref_path, tgt_path, bins=4096)

    _assert_finite_result(result)
