"""Tests for lumamatch.io_image.load_rgb."""

import numpy as np
import pytest
from PIL import Image

from lumamatch.io_image import load_rgb


def _save(tmp_path, name, mode, size=(8, 6), color=None):
    if mode == "P":
        img = Image.new("RGB", size, color or (10, 20, 30)).convert("P")
    else:
        img = Image.new(mode, size, color)
    path = tmp_path / name
    img.save(path)
    return path


@pytest.mark.parametrize(
    ("name", "mode", "color"),
    [
        ("rgb.png", "RGB", (10, 20, 30)),
        ("rgb.jpg", "RGB", (10, 20, 30)),
        ("rgb.heic", "RGB", (10, 20, 30)),
        ("gray.png", "L", 128),
        ("alpha.png", "RGBA", (10, 20, 30, 128)),
        ("palette.png", "P", (10, 20, 30)),
    ],
)
def test_load_rgb_shape_and_dtype(tmp_path, name, mode, color):
    path = _save(tmp_path, name, mode, color=color)
    result = load_rgb(path)
    assert result.dtype == np.uint8
    assert result.ndim == 3
    assert result.shape[2] == 3


def test_load_rgb_grayscale_channels_equal(tmp_path):
    path = _save(tmp_path, "gray.png", "L", color=128)
    result = load_rgb(path)
    assert np.array_equal(result[..., 0], result[..., 1])
    assert np.array_equal(result[..., 1], result[..., 2])


def test_load_rgb_drops_alpha(tmp_path):
    path = _save(tmp_path, "alpha.png", "RGBA", color=(10, 20, 30, 0))
    result = load_rgb(path)
    assert result.shape[2] == 3


def test_load_rgb_unsupported_extension(tmp_path):
    path = tmp_path / "image.bmp"
    path.write_bytes(b"not actually a bmp")
    with pytest.raises(ValueError, match="unsupported image format"):
        load_rgb(path)


def test_load_rgb_missing_file(tmp_path):
    path = tmp_path / "missing.png"
    with pytest.raises(FileNotFoundError, match=str(path)):
        load_rgb(path)


def test_load_rgb_corrupt_file(tmp_path):
    path = tmp_path / "corrupt.png"
    path.write_bytes(b"not an image")
    with pytest.raises(ValueError, match="could not decode"):
        load_rgb(path)
