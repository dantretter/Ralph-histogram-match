from pathlib import Path

import numpy as np
import pytest

from lumamatch.result import MatchResult


def _make_valid(bins: int = 4, **overrides) -> MatchResult:
    kwargs = {
        "reference_path": Path("reference.png"),
        "target_path": Path("target.png"),
        "bins": bins,
        "edges": np.linspace(0.0, 100.0, bins + 1),
        "hist_reference": np.array([1, 2, 3, 4], dtype=np.int64),
        "hist_target": np.array([2, 2, 2, 4], dtype=np.int64),
        "hist_target_matched": np.array([1, 3, 3, 3], dtype=np.int64),
        "lut": np.array([0.0, 30.0, 60.0, 100.0], dtype=np.float64),
        "emd_before": 10.0,
        "emd_after": 0.5,
        "clipped_fraction": 0.0,
        "reference_pixels": 10,
        "target_pixels": 10,
        "reference_shape": (2, 5),
        "target_shape": (2, 5),
        "image_out": Path("target_matched.png"),
        "csv_out": Path("target_histograms.csv"),
    }
    kwargs.update(overrides)
    return MatchResult(**kwargs)


def test_valid_construction_succeeds():
    result = _make_valid()
    assert result.bins == 4


def test_emd_reduction_property():
    result = _make_valid()
    assert result.emd_reduction == pytest.approx(0.95)


def test_raises_on_wrong_histogram_length():
    with pytest.raises(ValueError, match="hist_target"):
        _make_valid(hist_target=np.array([1, 2, 3], dtype=np.int64))


def test_raises_on_wrong_edges_length():
    with pytest.raises(ValueError, match="edges"):
        _make_valid(edges=np.linspace(0.0, 100.0, 4))


def test_raises_on_clipped_fraction_above_one():
    with pytest.raises(ValueError, match="clipped_fraction"):
        _make_valid(clipped_fraction=1.5)


def test_raises_on_clipped_fraction_below_zero():
    with pytest.raises(ValueError, match="clipped_fraction"):
        _make_valid(clipped_fraction=-0.1)


def test_raises_when_hist_target_sum_disagrees_with_target_pixels():
    with pytest.raises(ValueError, match="target_pixels"):
        _make_valid(hist_target=np.array([1, 1, 1, 1], dtype=np.int64))


def test_raises_when_hist_reference_sum_disagrees_with_reference_pixels():
    with pytest.raises(ValueError, match="reference_pixels"):
        _make_valid(hist_reference=np.array([1, 1, 1, 1], dtype=np.int64))


def test_raises_when_reference_shape_disagrees_with_reference_pixels():
    with pytest.raises(ValueError, match="reference_shape"):
        _make_valid(reference_shape=(3, 5))


def test_arrays_are_read_only():
    result = _make_valid()
    with pytest.raises(ValueError):
        result.lut[0] = 5.0
