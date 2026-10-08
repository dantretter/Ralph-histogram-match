import numpy as np
import pytest

from lumamatch.histogram import bin_centers, bin_edges, bin_width, l_histogram, to_pmf


def test_counts_sum_equals_size_for_random_array():
    rng = np.random.default_rng(0)
    values = rng.uniform(0.0, 100.0, size=10_000)
    counts, _ = l_histogram(values)
    assert counts.sum() == values.size


def test_exact_max_counted_in_last_bin():
    counts, _ = l_histogram(np.array([100.0]))
    assert counts[-1] == 1
    assert counts.sum() == 1


def test_exact_min_counted_in_first_bin():
    counts, _ = l_histogram(np.array([0.0]))
    assert counts[0] == 1
    assert counts.sum() == 1


def test_out_of_range_values_are_clipped_not_dropped():
    counts, _ = l_histogram(np.array([-5.0, 105.0]))
    assert counts.sum() == 2
    assert counts[0] == 1
    assert counts[-1] == 1


def test_edges_match_fixed_linspace_exactly():
    bins = 32
    _, edges = l_histogram(np.array([50.0]), bins=bins)
    assert np.array_equal(edges, np.linspace(0.0, 100.0, bins + 1))


def test_bins_must_be_at_least_two():
    with pytest.raises(ValueError, match="bins must be >= 2"):
        l_histogram(np.array([1.0]), bins=1)


def test_empty_array_raises():
    with pytest.raises(ValueError, match="at least one pixel"):
        l_histogram(np.array([]))


def test_bin_centers_and_width():
    bins = 256
    edges = bin_edges(bins)
    centers = bin_centers(edges)
    assert centers.shape == (bins,)
    assert bin_width(edges) == pytest.approx(100.0 / bins)


def test_counts_and_edges_dtype():
    counts, edges = l_histogram(np.array([10.0, 20.0, 30.0]))
    assert counts.dtype == np.int64
    assert edges.dtype == np.float64


def test_to_pmf_sums_to_one():
    counts, _ = l_histogram(np.array([10.0, 20.0, 30.0]))
    pmf = to_pmf(counts)
    assert pmf.sum() == pytest.approx(1.0)


def test_to_pmf_raises_on_all_zero():
    with pytest.raises(ValueError, match="zero"):
        to_pmf(np.zeros(8, dtype=np.int64))
