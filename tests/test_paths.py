import os
import stat

import pytest

from lumamatch.paths import resolve_outputs


def test_derives_matched_image_and_csv_paths(tmp_path):
    target = tmp_path / "photo.jpg"
    target.touch()

    image_out, csv_out = resolve_outputs(target)

    assert image_out == tmp_path / "photo_matched.jpg"
    assert csv_out == tmp_path / "photo_histograms.csv"


def test_preserves_uppercase_suffix(tmp_path):
    target = tmp_path / "photo.PNG"
    target.touch()

    image_out, _csv_out = resolve_outputs(target)

    assert image_out == tmp_path / "photo_matched.PNG"


def test_existing_image_output_raises_without_force(tmp_path):
    target = tmp_path / "photo.jpg"
    target.touch()
    (tmp_path / "photo_matched.jpg").touch()

    with pytest.raises(FileExistsError) as exc_info:
        resolve_outputs(target, force=False)

    assert "photo_matched.jpg" in str(exc_info.value)
    assert "--force" in str(exc_info.value)
    assert not (tmp_path / "photo_histograms.csv").exists()


def test_existing_csv_output_raises_without_force(tmp_path):
    target = tmp_path / "photo.jpg"
    target.touch()
    (tmp_path / "photo_histograms.csv").touch()

    with pytest.raises(FileExistsError) as exc_info:
        resolve_outputs(target, force=False)

    assert "photo_histograms.csv" in str(exc_info.value)
    assert "--force" in str(exc_info.value)


def test_both_existing_outputs_name_image_first(tmp_path):
    target = tmp_path / "photo.jpg"
    target.touch()
    (tmp_path / "photo_matched.jpg").touch()
    (tmp_path / "photo_histograms.csv").touch()

    with pytest.raises(FileExistsError) as exc_info:
        resolve_outputs(target, force=False)

    assert "photo_matched.jpg" in str(exc_info.value)


def test_force_true_allows_existing_outputs(tmp_path):
    target = tmp_path / "photo.jpg"
    target.touch()
    (tmp_path / "photo_matched.jpg").touch()
    (tmp_path / "photo_histograms.csv").touch()

    image_out, csv_out = resolve_outputs(target, force=True)

    assert image_out == tmp_path / "photo_matched.jpg"
    assert csv_out == tmp_path / "photo_histograms.csv"


def test_nonexistent_parent_directory_raises_file_not_found(tmp_path):
    target = tmp_path / "missing" / "photo.jpg"

    with pytest.raises(FileNotFoundError):
        resolve_outputs(target)


@pytest.mark.skipif(os.geteuid() == 0, reason="root bypasses os.access permission checks")
def test_read_only_parent_directory_raises_permission_error(tmp_path):
    target = tmp_path / "photo.jpg"
    target.touch()
    original_mode = tmp_path.stat().st_mode
    os.chmod(tmp_path, stat.S_IRUSR | stat.S_IXUSR)

    try:
        with pytest.raises(PermissionError):
            resolve_outputs(target)
    finally:
        os.chmod(tmp_path, original_mode)
