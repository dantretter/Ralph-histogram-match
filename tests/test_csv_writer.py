from pathlib import Path

import numpy as np
import pytest

from lumamatch.csv_writer import CSV_HEADER, read_histogram_csv, write_histogram_csv
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
        "image_out": Path("target_matched.png"),
        "csv_out": Path("target_histograms.csv"),
    }
    kwargs.update(overrides)
    return MatchResult(**kwargs)


def test_structure(tmp_path):
    result = _make_valid()
    csv_path = tmp_path / "out.csv"
    write_histogram_csv(csv_path, result)

    lines = csv_path.read_text(encoding="utf-8").splitlines()
    assert all(line.startswith("# ") for line in lines[:8])
    assert lines[8] == ",".join(CSV_HEADER)
    assert "" not in lines
    data_rows = lines[9:]
    assert len(data_rows) == result.bins


def test_column_sums_and_metadata(tmp_path):
    result = _make_valid()
    csv_path = tmp_path / "out.csv"
    write_histogram_csv(csv_path, result)

    meta, rows = read_histogram_csv(csv_path)

    assert sum(int(r[4]) for r in rows) == result.reference_pixels
    assert sum(int(r[5]) for r in rows) == result.target_pixels
    assert sum(int(r[6]) for r in rows) == result.target_pixels

    assert meta["bins"] == str(result.bins)
    assert float(meta["emd_after"]) <= float(meta["emd_before"])


def test_numeric_formatting(tmp_path):
    result = _make_valid()
    csv_path = tmp_path / "out.csv"
    write_histogram_csv(csv_path, result)

    _, rows = read_histogram_csv(csv_path)

    for row in rows:
        for count_field in row[4:7]:
            assert "." not in count_field
            assert "e" not in count_field.lower()

    assert float(rows[0][1]) == pytest.approx(0.0)
    assert float(rows[-1][3]) == pytest.approx(100.0)
