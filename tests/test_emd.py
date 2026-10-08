import numpy as np
import pytest

from lumamatch.emd import emd, emd_reduction
from lumamatch.histogram import bin_edges


def _spike(bins: int, index: int) -> np.ndarray:
    counts = np.zeros(bins, dtype=np.int64)
    counts[index] = 1
    return counts


def test_emd_of_known_spike_separation():
    bins = 100
    edges = bin_edges(bins)
    a = _spike(bins, 10)
    b = _spike(bins, 30)
    assert emd(a, b, edges) == pytest.approx(20.0, abs=1e-9)


def test_emd_identity_is_zero():
    bins = 100
    edges = bin_edges(bins)
    a = _spike(bins, 42)
    assert emd(a, a, edges) == 0.0


def test_emd_is_symmetric():
    bins = 100
    edges = bin_edges(bins)
    a = _spike(bins, 10)
    b = _spike(bins, 30)
    assert emd(a, b, edges) == pytest.approx(emd(b, a, edges))


def test_emd_is_scale_invariant():
    bins = 100
    edges = bin_edges(bins)
    a = _spike(bins, 10)
    b = _spike(bins, 30)
    assert emd(a, b, edges) == pytest.approx(emd(a * 7, b, edges))


def test_emd_raises_on_mismatched_counts_length():
    bins = 100
    edges = bin_edges(bins)
    a = _spike(bins, 10)
    b = np.zeros(bins - 1, dtype=np.int64)
    b[5] = 1
    with pytest.raises(ValueError, match="same shape"):
        emd(a, b, edges)


def test_emd_raises_on_wrong_edges_length():
    bins = 100
    a = _spike(bins, 10)
    b = _spike(bins, 30)
    wrong_edges = bin_edges(bins - 1)
    with pytest.raises(ValueError, match="length"):
        emd(a, b, wrong_edges)


def test_emd_raises_on_all_zero_histogram():
    bins = 100
    edges = bin_edges(bins)
    a = np.zeros(bins, dtype=np.int64)
    b = _spike(bins, 30)
    with pytest.raises(ValueError, match="zero"):
        emd(a, b, edges)


def test_emd_reduction_typical_case():
    assert emd_reduction(10.0, 0.5) == pytest.approx(0.95)


def test_emd_reduction_perfect_match():
    assert emd_reduction(10.0, 0.0) == 1.0


def test_emd_reduction_nothing_to_improve():
    assert emd_reduction(0.0, 0.0) == 0.0


def test_emd_reduction_regression_is_negative_not_clamped():
    assert emd_reduction(1.0, 2.0) == pytest.approx(-1.0)
