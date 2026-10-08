"""Format coverage: prove the pipeline works for every supported I/O combination.

Format handling is where the most environment-dependent breakage lives
(libheif availability, JPEG subsampling, palette conversion), so this test
is the canary for I/O regressions. The same reference/target pair (fixed
seed) is saved under each extension combination so format is the only
variable between cases.
"""

import numpy as np
import pytest
from PIL import Image

from lumamatch.color import srgb_to_lab
from lumamatch.csv_writer import read_histogram_csv
from lumamatch.histogram import bin_edges
from lumamatch.io_image import load_rgb, save_rgb
from lumamatch.pipeline import match_luminance
from tests.curves import apply_curve_to_image, random_monotonic_curve
from tests.images import synthetic_reference

SEED = 11
BINS = 256

PAIRS = [
    (".png", ".png"),
    (".jpg", ".jpg"),
    (".heic", ".heic"),
    (".heic", ".png"),
    (".png", ".jpg"),
]

PILLOW_FORMAT = {".png": "PNG", ".jpg": "JPEG", ".heic": "HEIF"}

# The looser JPEG/HEIC bound absorbs codec error, not tone-mapping error:
# both formats re-quantize chroma/luma on save, so a byte-exact L* match is
# impossible even with a perfect LUT. PNG is lossless and is the case that
# actually validates the tone-mapping math; its tolerance matches the
# round-trip test's.
TOLERANCE = {".png": 1.0, ".jpg": 3.0, ".heic": 3.0}


@pytest.mark.parametrize(
    "reference_ext,target_ext",
    PAIRS,
    ids=[f"ref{r}-tgt{t}" for r, t in PAIRS],
)
def test_format_coverage(tmp_path, reference_ext, target_ext):
    rng = np.random.default_rng(SEED)
    edges = bin_edges(BINS)

    ref_rgb = synthetic_reference(rng)
    curve = random_monotonic_curve(rng, bins=BINS)
    tgt_rgb = apply_curve_to_image(ref_rgb, curve, edges)

    ref_path = tmp_path / f"ref{reference_ext}"
    tgt_path = tmp_path / f"tgt{target_ext}"
    save_rgb(ref_path, ref_rgb)
    save_rgb(tgt_path, tgt_rgb)

    result = match_luminance(ref_path, tgt_path, bins=BINS)

    assert result.image_out.exists()
    assert result.image_out.stat().st_size > 0
    assert result.csv_out.exists()
    assert result.csv_out.stat().st_size > 0
    assert result.image_out.suffix == target_ext

    with Image.open(result.image_out) as img:
        assert img.format == PILLOW_FORMAT[target_ext]

    out_rgb = load_rgb(result.image_out)
    assert out_rgb.shape == tgt_rgb.shape

    assert result.emd_after < result.emd_before
    assert result.emd_reduction > 0.8

    l_out = srgb_to_lab(out_rgb)[..., 0]
    l_ref = srgb_to_lab(ref_rgb)[..., 0]
    mean_abs = float(np.mean(np.abs(l_out - l_ref)))
    assert mean_abs < TOLERANCE[target_ext], (
        f"ref={reference_ext} tgt={target_ext}: mean |L_out - L_ref| = {mean_abs:.4f}"
    )

    metadata, rows = read_histogram_csv(result.csv_out)
    assert len(rows) == result.bins
    assert metadata["image2"] == str(result.target_path)
