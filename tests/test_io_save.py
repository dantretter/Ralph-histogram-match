"""Tests for lumamatch.io_image.save_rgb."""

import numpy as np
import pytest
from PIL import Image

from lumamatch.io_image import load_rgb, save_rgb


def _random_rgb(shape=(32, 48, 3), seed=0):
    rng = np.random.default_rng(seed)
    return rng.integers(0, 256, size=shape, dtype=np.uint8)


def test_save_rgb_png_round_trip_exact(tmp_path):
    rgb = _random_rgb()
    path = tmp_path / "out.png"
    save_rgb(path, rgb)
    result = load_rgb(path)
    assert np.array_equal(result, rgb)


def test_save_rgb_jpeg_readable(tmp_path):
    rgb = _random_rgb()
    path = tmp_path / "out.jpg"
    save_rgb(path, rgb, quality=95)
    assert path.exists()
    assert path.stat().st_size > 0
    result = load_rgb(path)
    assert result.shape == rgb.shape
    assert result.dtype == np.uint8
    assert np.abs(result.astype(np.int16) - rgb.astype(np.int16)).mean() < 8


def test_save_rgb_heic_readable(tmp_path):
    rgb = _random_rgb()
    path = tmp_path / "out.heic"
    save_rgb(path, rgb, quality=95)
    assert path.exists()
    assert path.stat().st_size > 0
    result = load_rgb(path)
    assert result.shape == rgb.shape
    assert result.dtype == np.uint8


def test_save_rgb_strips_exif(tmp_path):
    src_path = tmp_path / "src.jpg"
    img = Image.new("RGB", (8, 6), (10, 20, 30))
    exif = img.getexif()
    exif[0x0112] = 1  # Orientation tag
    img.save(src_path, exif=exif)

    rgb = load_rgb(src_path)
    out_path = tmp_path / "out.jpg"
    save_rgb(out_path, rgb)

    with Image.open(out_path) as reloaded:
        assert len(reloaded.getexif()) == 0


def test_save_rgb_unsupported_extension(tmp_path):
    rgb = _random_rgb()
    path = tmp_path / "out.tiff"
    with pytest.raises(ValueError, match="unsupported image format"):
        save_rgb(path, rgb)


def test_save_rgb_missing_directory(tmp_path):
    rgb = _random_rgb()
    path = tmp_path / "missing_dir" / "out.png"
    with pytest.raises(FileNotFoundError):
        save_rgb(path, rgb)


def test_save_rgb_wrong_dtype(tmp_path):
    rgb = _random_rgb().astype(np.float64)
    path = tmp_path / "out.png"
    with pytest.raises(ValueError, match="uint8"):
        save_rgb(path, rgb)


def test_save_rgb_wrong_shape(tmp_path):
    rgb = _random_rgb()[:, :, 0]
    path = tmp_path / "out.png"
    with pytest.raises(ValueError, match="shape"):
        save_rgb(path, rgb)
