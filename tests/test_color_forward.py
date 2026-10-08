import numpy as np
import pytest

from lumamatch.color import lab_l_channel, srgb_to_lab


def _solid(rgb_value: tuple[int, int, int]) -> np.ndarray:
    return np.full((1, 1, 3), rgb_value, dtype=np.uint8)


def test_pure_black_maps_to_lab_zero():
    lab = srgb_to_lab(_solid((0, 0, 0)))
    np.testing.assert_allclose(lab[0, 0], [0.0, 0.0, 0.0], atol=1e-9)


def test_pure_white_maps_to_l100_a0_b0():
    lab = srgb_to_lab(_solid((255, 255, 255)))
    np.testing.assert_allclose(lab[0, 0], [100.0, 0.0, 0.0], atol=1e-6)


def test_mid_grey_matches_known_l_value():
    lab = srgb_to_lab(_solid((128, 128, 128)))
    assert abs(lab[0, 0, 0] - 53.5850) < 1e-3


def test_output_dtype_and_shape():
    rgb = np.zeros((4, 5, 3), dtype=np.uint8)
    lab = srgb_to_lab(rgb)
    assert lab.dtype == np.float64
    assert lab.shape == (4, 5, 3)


def test_l_star_within_valid_range_for_random_image():
    rng = np.random.default_rng(42)
    rgb = rng.integers(0, 256, size=(64, 64, 3), dtype=np.uint8)
    lab = srgb_to_lab(rgb)
    assert lab[..., 0].min() >= 0.0
    assert lab[..., 0].max() <= 100.0


def test_rejects_non_uint8_dtype():
    rgb = np.zeros((2, 2, 3), dtype=np.float64)
    with pytest.raises(ValueError, match="uint8"):
        srgb_to_lab(rgb)


def test_rejects_wrong_shape():
    rgb = np.zeros((2, 2, 4), dtype=np.uint8)
    with pytest.raises(ValueError, match="shape"):
        srgb_to_lab(rgb)


def test_lab_l_channel_returns_contiguous_copy():
    lab = srgb_to_lab(_solid((10, 20, 30)))
    l_channel = lab_l_channel(lab)
    assert l_channel.flags["C_CONTIGUOUS"]
    assert l_channel.shape == (1, 1)
    np.testing.assert_allclose(l_channel, lab[..., 0])
