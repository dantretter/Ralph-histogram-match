"""Security regression tests: untrusted image input, output containment, no network.

Covers the defensive posture described in TASK-25: the decompression-bomb
guard stays active, malformed files fail cleanly as ValueError (not a raw PIL
exception), outputs can never land outside the target's directory, no source
metadata survives into the output, and the tool never touches the network.
"""

import socket

import numpy as np
import pytest
from PIL import Image

from lumamatch.histogram import bin_edges
from lumamatch.io_image import load_rgb, save_rgb
from lumamatch.paths import resolve_outputs
from lumamatch.pipeline import match_luminance
from tests.curves import apply_curve_to_image, random_monotonic_curve
from tests.images import synthetic_reference

SEED = 7
BINS = 256

MAGIC_BYTES = {
    ".png": b"\x89PNG\r\n\x1a\n",
    ".jpg": b"\xff\xd8\xff\xe0",
    ".heic": b"\x00\x00\x00\x18ftypheic",
}


def _plain_rgb(height=128, width=192):
    return np.zeros((height, width, 3), dtype=np.uint8)


def _distorted_pair(tmp_path, seed=SEED, bins=BINS):
    """Build a reference/target PNG pair via the same curve-distortion fixture used elsewhere."""
    rng = np.random.default_rng(seed)
    edges = bin_edges(bins)
    ref_rgb = synthetic_reference(rng)
    curve = random_monotonic_curve(rng, bins=bins)
    tgt_rgb = apply_curve_to_image(ref_rgb, curve, edges)

    ref_path = tmp_path / "ref.png"
    tgt_path = tmp_path / "tgt.png"
    save_rgb(ref_path, ref_rgb)
    save_rgb(tgt_path, tgt_rgb)
    return ref_path, tgt_path, ref_rgb, tgt_rgb


def test_decompression_bomb_raises_value_error(tmp_path, monkeypatch):
    path = tmp_path / "normal.png"
    save_rgb(path, _plain_rgb())

    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 100)

    with pytest.raises(ValueError, match=str(path)):
        load_rgb(path)


@pytest.mark.parametrize("suffix", [".png", ".jpg", ".heic"])
def test_garbage_bytes_after_magic_raises_value_error(tmp_path, suffix):
    path = tmp_path / f"garbage{suffix}"
    path.write_bytes(MAGIC_BYTES[suffix] + b"\x00\x01\x02\x03" * 16)

    with pytest.raises(ValueError, match=str(path)):
        load_rgb(path)


@pytest.mark.parametrize("suffix", [".png", ".jpg", ".heic"])
def test_truncated_file_raises_value_error(tmp_path, suffix):
    good_path = tmp_path / f"good{suffix}"
    save_rgb(good_path, _plain_rgb())
    truncated = good_path.read_bytes()[:40]

    bad_path = tmp_path / f"truncated{suffix}"
    bad_path.write_bytes(truncated)

    with pytest.raises(ValueError, match=str(bad_path)):
        load_rgb(bad_path)


def test_resolve_outputs_confines_to_target_parent(tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    target_path = sub / ".." / "sub" / "photo.png"

    image_out, csv_out = resolve_outputs(target_path)

    assert image_out.resolve().parent == sub.resolve()
    assert csv_out.resolve().parent == sub.resolve()


def test_output_strips_exif_gps_and_icc(tmp_path):
    ref_path, _tgt_path, _ref_rgb, tgt_rgb = _distorted_pair(tmp_path)

    tgt_path = tmp_path / "tgt_with_metadata.jpg"
    img = Image.fromarray(tgt_rgb, mode="RGB")
    exif = img.getexif()
    gps_ifd = {1: "N", 2: (40, 0, 0), 3: "W", 4: (74, 0, 0)}
    exif[0x8825] = gps_ifd  # GPSInfo tag, pointing at a fabricated GPS IFD
    fake_icc = b"fake-icc-profile" * 8
    img.save(tgt_path, exif=exif, icc_profile=fake_icc)

    result = match_luminance(ref_path, tgt_path)

    with Image.open(result.image_out) as out_img:
        out_exif = out_img.getexif()
        assert 0x8825 not in out_exif
        assert out_img.info.get("icc_profile") is None


def test_no_network_io_during_match(tmp_path, monkeypatch):
    def _forbidden_socket(*args, **kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", _forbidden_socket)

    ref_path, tgt_path, _ref_rgb, _tgt_rgb = _distorted_pair(tmp_path)

    result = match_luminance(ref_path, tgt_path, bins=BINS)

    assert result.image_out.exists()
    assert result.csv_out.exists()
