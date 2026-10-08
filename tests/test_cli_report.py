"""Tests for lumamatch.cli success reporting and error handling."""

import re

import numpy as np

from lumamatch.cli import main
from lumamatch.io_image import save_rgb


def _gradient_image(seed: int, shape: tuple[int, int] = (16, 16)) -> np.ndarray:
    rng = np.random.default_rng(seed)
    h, w = shape
    ramp = np.linspace(0, 255, w, dtype=np.float64)
    gray = np.tile(ramp, (h, 1))
    tint = rng.integers(0, 60, size=(h, w, 3)).astype(np.float64)
    return np.clip(gray[..., None] + tint, 0, 255).astype(np.uint8)


def _save_pair(tmp_path):
    reference_path = tmp_path / "reference.png"
    target_path = tmp_path / "subject.png"
    save_rgb(reference_path, _gradient_image(seed=0))
    save_rgb(target_path, _gradient_image(seed=1))
    return reference_path, target_path


def test_success_report_content(tmp_path, capsys):
    reference_path, target_path = _save_pair(tmp_path)

    exit_code = main([str(reference_path), str(target_path)])
    out, err = capsys.readouterr()

    assert exit_code == 0
    assert err == ""
    assert "EMD" in out
    assert "-> " in out
    assert "L*" in out
    assert "% reduction" in out
    assert "clipped" in out
    assert "subject_matched.png" in out
    assert "subject_histograms.csv" in out
    assert re.search(r"EMD:\s+\d+\.\d{3} -> \d+\.\d{3} L\*", out)


def test_error_on_missing_reference(tmp_path, capsys):
    _, target_path = _save_pair(tmp_path)
    missing = tmp_path / "missing.png"

    exit_code = main([str(missing), str(target_path)])
    out, err = capsys.readouterr()

    assert exit_code == 2
    assert out == ""
    assert err.startswith("error:")


def test_error_on_unsupported_extension(tmp_path, capsys):
    reference_path, _ = _save_pair(tmp_path)
    bad_target = tmp_path / "subject.bmp"
    bad_target.write_bytes(b"not actually a bmp")

    exit_code = main([str(reference_path), str(bad_target)])
    out, err = capsys.readouterr()

    assert exit_code == 2
    assert out == ""
    assert err.startswith("error:")


def test_error_on_corrupt_file(tmp_path, capsys):
    reference_path, _ = _save_pair(tmp_path)
    corrupt_target = tmp_path / "subject.png"
    corrupt_target.write_bytes(b"not a real png")

    exit_code = main([str(reference_path), str(corrupt_target)])
    out, err = capsys.readouterr()

    assert exit_code == 2
    assert out == ""
    assert err.startswith("error:")


def test_error_on_existing_output_mentions_force(tmp_path, capsys):
    reference_path, target_path = _save_pair(tmp_path)

    first = main([str(reference_path), str(target_path)])
    capsys.readouterr()
    assert first == 0

    second = main([str(reference_path), str(target_path)])
    out, err = capsys.readouterr()

    assert second == 2
    assert out == ""
    assert "--force" in err

    forced = main([str(reference_path), str(target_path), "--force"])
    capsys.readouterr()
    assert forced == 0


def test_quiet_suppresses_success_output(tmp_path, capsys):
    reference_path, target_path = _save_pair(tmp_path)

    exit_code = main([str(reference_path), str(target_path), "--quiet"])
    out, err = capsys.readouterr()

    assert exit_code == 0
    assert out == ""
    assert err == ""


def test_quiet_still_reports_errors(tmp_path, capsys):
    _, target_path = _save_pair(tmp_path)
    missing = tmp_path / "missing.png"

    exit_code = main([str(missing), str(target_path), "--quiet"])
    out, err = capsys.readouterr()

    assert exit_code == 2
    assert out == ""
    assert err.startswith("error:")


def test_unexpected_exception_returns_one_with_single_line_error(tmp_path, capsys, monkeypatch):
    reference_path, target_path = _save_pair(tmp_path)

    def _boom(**kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr("lumamatch.cli.match_luminance", _boom)

    exit_code = main([str(reference_path), str(target_path)])
    out, err = capsys.readouterr()

    assert exit_code == 1
    assert out == ""
    assert err.strip().startswith("error: unexpected failure:")
    assert len(err.strip().splitlines()) == 1
