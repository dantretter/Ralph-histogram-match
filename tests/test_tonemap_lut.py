import numpy as np
import pytest

from lumamatch.histogram import L_MAX, L_MIN, bin_centers, bin_edges
from lumamatch.tonemap import assert_monotonic, build_lut


def _spike(bins: int, index: int) -> np.ndarray:
    counts = np.zeros(bins, dtype=np.int64)
    counts[index] = 1
    return counts


def _random_histograms(seed: int, bins: int = 256) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    src = rng.integers(1, 1000, size=bins).astype(np.int64)
    ref = rng.integers(1, 1000, size=bins).astype(np.int64)
    return src, ref


def test_identity_lut_is_near_bin_centers():
    bins = 256
    edges = bin_edges(bins)
    centers = bin_centers(edges)
    src, _ = _random_histograms(seed=1, bins=bins)

    lut = build_lut(src, src, edges)

    assert np.all(np.abs(lut - centers) <= 0.5)


@pytest.mark.parametrize("seed", range(50))
def test_random_histogram_pairs_are_monotonic(seed):
    bins = 256
    edges = bin_edges(bins)
    src, ref = _random_histograms(seed=seed, bins=bins)

    lut = build_lut(src, ref, edges)

    assert np.all(np.diff(lut) >= 0)


@pytest.mark.parametrize("seed", range(50))
def test_random_histogram_pairs_are_finite(seed):
    bins = 256
    edges = bin_edges(bins)
    src, ref = _random_histograms(seed=seed, bins=bins)

    lut = build_lut(src, ref, edges)

    assert np.all(np.isfinite(lut))
    assert_monotonic(lut)


def test_random_histogram_pairs_stay_in_range():
    bins = 256
    edges = bin_edges(bins)
    for seed in range(50):
        src, ref = _random_histograms(seed=seed, bins=bins)
        lut = build_lut(src, ref, edges)
        assert np.all(lut >= L_MIN)
        assert np.all(lut <= L_MAX)


def test_degenerate_source_single_spike_is_valid():
    bins = 256
    edges = bin_edges(bins)
    _, ref = _random_histograms(seed=2, bins=bins)
    src = _spike(bins, 0)

    lut = build_lut(src, ref, edges)

    assert np.all(np.diff(lut) >= 0)
    assert np.all(np.isfinite(lut))


def test_degenerate_reference_single_spike_maps_everything_near_it():
    bins = 256
    edges = bin_edges(bins)
    centers = bin_centers(edges)
    src, _ = _random_histograms(seed=3, bins=bins)
    ref = _spike(bins, bins - 1)

    lut = build_lut(src, ref, edges)

    bin_width = centers[1] - centers[0]
    assert np.all(np.abs(lut - centers[-1]) <= 2 * bin_width)


def test_mismatched_counts_length_raises():
    bins = 256
    edges = bin_edges(bins)
    src = np.ones(bins, dtype=np.int64)
    ref = np.ones(bins - 1, dtype=np.int64)
    with pytest.raises(ValueError, match="same shape"):
        build_lut(src, ref, edges)


def test_mismatched_edges_length_raises():
    bins = 256
    src = np.ones(bins, dtype=np.int64)
    ref = np.ones(bins, dtype=np.int64)
    wrong_edges = bin_edges(bins - 1)
    with pytest.raises(ValueError, match="length"):
        build_lut(src, ref, wrong_edges)


def test_assert_monotonic_raises_on_decrease():
    with pytest.raises(ValueError, match="non-decreasing"):
        assert_monotonic(np.array([1.0, 2.0, 1.5]))


def test_assert_monotonic_raises_on_nan():
    with pytest.raises(ValueError, match="NaN"):
        assert_monotonic(np.array([1.0, np.nan, 2.0]))
