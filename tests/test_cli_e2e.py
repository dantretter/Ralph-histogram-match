"""End-to-end CLI tests: invoke `python -m lumamatch` as a real subprocess.

In-process tests of `main()` (see test_cli_args.py, test_cli_report.py) can't
catch packaging problems -- a broken `__main__.py`, an import that only works
under pytest's path manipulation, a stray import-time print. This module runs
the genuine command line and inspects exit codes, stdout, stderr, and the
files actually written to disk.
"""

import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from lumamatch.csv_writer import CSV_HEADER, read_histogram_csv
from lumamatch.histogram import DEFAULT_BINS, bin_edges
from lumamatch.io_image import save_rgb
from tests.curves import apply_curve_to_image, random_monotonic_curve
from tests.images import synthetic_reference

SRC_DIR = Path(__file__).resolve().parents[1] / "src"


def _run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Invoke `python -m lumamatch` as a real subprocess using the venv interpreter."""
    env = {**os.environ, "PYTHONPATH": str(SRC_DIR)}
    return subprocess.run(
        [sys.executable, "-m", "lumamatch", *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=cwd,
    )


@pytest.fixture
def image_pair(tmp_path) -> tuple[Path, Path]:
    """Write a reference/target PNG pair related by a seeded monotonic L* curve."""
    rng = np.random.default_rng(99)
    edges = bin_edges(DEFAULT_BINS)
    ref_rgb = synthetic_reference(rng)
    curve = random_monotonic_curve(rng, bins=DEFAULT_BINS)
    tgt_rgb = apply_curve_to_image(ref_rgb, curve, edges)

    ref_path = tmp_path / "ref.png"
    tgt_path = tmp_path / "tgt.png"
    save_rgb(ref_path, ref_rgb)
    save_rgb(tgt_path, tgt_rgb)
    return ref_path, tgt_path


def test_success_overwrite_guard_and_force(tmp_path, image_pair):
    ref_path, tgt_path = image_pair
    image_out = tmp_path / "tgt_matched.png"
    csv_out = tmp_path / "tgt_histograms.csv"

    proc = _run([str(ref_path), str(tgt_path)], cwd=tmp_path)

    assert proc.returncode == 0
    assert proc.stderr == ""
    assert "EMD" in proc.stdout
    assert "tgt_matched.png" in proc.stdout
    assert "tgt_histograms.csv" in proc.stdout
    assert image_out.exists() and image_out.stat().st_size > 0
    assert csv_out.exists() and csv_out.stat().st_size > 0

    metadata, rows = read_histogram_csv(csv_out)
    assert ",".join(CSV_HEADER) in csv_out.read_text(encoding="utf-8")
    assert len(rows) == DEFAULT_BINS

    reference_pixels = int(metadata["image1_pixels"])
    target_pixels = int(metadata["image2_pixels"])
    assert sum(int(row[4]) for row in rows) == reference_pixels
    assert sum(int(row[5]) for row in rows) == target_pixels
    assert sum(int(row[6]) for row in rows) == target_pixels

    image_bytes_before = image_out.read_bytes()
    csv_bytes_before = csv_out.read_bytes()

    second = _run([str(ref_path), str(tgt_path)], cwd=tmp_path)

    assert second.returncode == 2
    assert second.stdout == ""
    assert "--force" in second.stderr
    assert image_out.read_bytes() == image_bytes_before
    assert csv_out.read_bytes() == csv_bytes_before

    third = _run([str(ref_path), str(tgt_path), "--force"], cwd=tmp_path)

    assert third.returncode == 0
    assert image_out.exists()
    assert csv_out.exists()
    metadata_after_force, rows_after_force = read_histogram_csv(csv_out)
    assert len(rows_after_force) == DEFAULT_BINS
    assert metadata_after_force["image2_pixels"] == metadata["image2_pixels"]


def test_quiet_produces_empty_stdout(tmp_path, image_pair):
    ref_path, tgt_path = image_pair

    proc = _run([str(ref_path), str(tgt_path), "--quiet"], cwd=tmp_path)

    assert proc.returncode == 0
    assert proc.stdout == ""


def test_help_lists_key_flags(tmp_path):
    proc = _run(["--help"], cwd=tmp_path)

    assert proc.returncode == 0
    assert "--bins" in proc.stdout
    assert "--force" in proc.stdout
    assert "--quiet" in proc.stdout


def test_version_prints_a_version_string(tmp_path):
    proc = _run(["--version"], cwd=tmp_path)

    assert proc.returncode == 0
    assert any(char.isdigit() for char in proc.stdout)


def test_nonexistent_reference_fails_cleanly(tmp_path, image_pair):
    _, tgt_path = image_pair
    missing_ref = tmp_path / "missing.png"

    proc = _run([str(missing_ref), str(tgt_path)], cwd=tmp_path)

    assert proc.returncode == 2
    assert proc.stdout == ""
    assert proc.stderr.startswith("error:")
    assert "missing.png" in proc.stderr
    assert not (tmp_path / "tgt_matched.png").exists()
    assert not (tmp_path / "tgt_histograms.csv").exists()
