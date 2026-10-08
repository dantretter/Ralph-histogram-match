import numpy as np
import pytest

from lumamatch.histogram import bin_centers, bin_edges, bin_width
from lumamatch.tonemap import apply_lut, build_lut


def _random_histograms(seed: int, bins: int = 256) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    src = rng.integers(1, 1000, size=bins).astype(np.int64)
    ref = rng.integers(1, 1000, size=bins).astype(np.int64)
    return src, ref


def test_output_shape_and_dtype_for_multidimensional_input():
    bins = 256
    edges = bin_edges(bins)
    src, ref = _random_histograms(seed=0, bins=bins)
    lut = build_lut(src, ref, edges)

    rng = np.random.default_rng(0)
    l_star = rng.uniform(0, 100, size=(7, 11))

    out = apply_lut(l_star, lut, edges)

    assert out.shape == (7, 11)
    assert out.dtype == np.float64


def test_output_within_range():
    bins = 256
    edges = bin_edges(bins)
    src, ref = _random_histograms(seed=1, bins=bins)
    lut = build_lut(src, ref, edges)

    rng = np.random.default_rng(1)
    l_star = rng.uniform(-10, 110, size=1000)

    out = apply_lut(l_star, lut, edges)

    assert np.all(out >= 0.0)
    assert np.all(out <= 100.0)


def test_monotonic_in_input():
    bins = 256
    edges = bin_edges(bins)
    src, ref = _random_histograms(seed=2, bins=bins)
    lut = build_lut(src, ref, edges)

    rng = np.random.default_rng(2)
    l_star = np.sort(rng.uniform(0, 100, size=2000))

    out = apply_lut(l_star, lut, edges)

    assert np.all(np.diff(out) >= 0)


def test_equal_inputs_produce_equal_outputs():
    bins = 256
    edges = bin_edges(bins)
    src, ref = _random_histograms(seed=3, bins=bins)
    lut = build_lut(src, ref, edges)

    l_star = np.array([42.0, 42.0, 7.5, 7.5, 99.9])
    out = apply_lut(l_star, lut, edges)

    assert out[0] == out[1]
    assert out[2] == out[3]


def test_clamping_below_first_and_above_last_center():
    bins = 256
    edges = bin_edges(bins)
    src, ref = _random_histograms(seed=4, bins=bins)
    lut = build_lut(src, ref, edges)

    out = apply_lut(np.array([0.0]), lut, edges)
    assert out[0] == pytest.approx(lut[0])

    out = apply_lut(np.array([100.0]), lut, edges)
    assert out[0] == pytest.approx(lut[-1])


def test_gradient_produces_more_distinct_values_than_bins_no_banding():
    bins = 16
    edges = bin_edges(bins)
    src, ref = _random_histograms(seed=5, bins=bins)
    lut = build_lut(src, ref, edges)

    ramp = np.linspace(0.0, 100.0, 1024)
    out = apply_lut(ramp, lut, edges)

    assert len(np.unique(out)) > bins


def test_identity_lut_returns_input_within_half_bin_width():
    bins = 256
    edges = bin_edges(bins)
    centers = bin_centers(edges)
    width = bin_width(edges)

    rng = np.random.default_rng(6)
    l_star = rng.uniform(centers[0], centers[-1], size=500)

    out = apply_lut(l_star, centers, edges)

    assert np.all(np.abs(out - l_star) <= width / 2 + 1e-9)


def test_mismatched_lut_edges_length_raises():
    bins = 256
    edges = bin_edges(bins)
    lut = np.ones(bins - 1, dtype=np.float64)

    with pytest.raises(ValueError, match="length"):
        apply_lut(np.array([50.0]), lut, edges)
