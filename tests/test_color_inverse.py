import numpy as np
import pytest

from lumamatch.color import lab_to_srgb, srgb_to_lab


def test_all_grey_levels_round_trip_byte_exact():
    greys = np.arange(256, dtype=np.uint8)
    rgb = np.stack([greys, greys, greys], axis=-1).reshape(1, 256, 3)
    lab = srgb_to_lab(rgb)
    recovered, _ = lab_to_srgb(lab)
    np.testing.assert_array_equal(recovered, rgb)


def test_random_colors_round_trip_byte_exact():
    rng = np.random.default_rng(0)
    rgb = rng.integers(0, 256, size=(64, 64, 3), dtype=np.uint8)
    lab = srgb_to_lab(rgb)
    recovered, _ = lab_to_srgb(lab)
    np.testing.assert_array_equal(recovered, rgb)


def test_in_gamut_image_reports_no_clipping():
    rgb = np.full((8, 8, 3), 100, dtype=np.uint8)
    lab = srgb_to_lab(rgb)
    _, clipped_fraction = lab_to_srgb(lab)
    assert clipped_fraction == 0.0


def test_out_of_gamut_lab_reports_full_clipping():
    lab = np.zeros((2, 2, 3), dtype=np.float64)
    lab[..., 0] = 95.0
    lab[..., 1] = 80.0
    lab[..., 2] = -80.0
    _, clipped_fraction = lab_to_srgb(lab)
    assert clipped_fraction == 1.0


def test_rejects_non_float64_dtype():
    lab = np.zeros((2, 2, 3), dtype=np.float32)
    with pytest.raises(ValueError, match="float64"):
        lab_to_srgb(lab)


def test_rejects_wrong_shape():
    lab = np.zeros((2, 2, 2), dtype=np.float64)
    with pytest.raises(ValueError, match="shape"):
        lab_to_srgb(lab)
