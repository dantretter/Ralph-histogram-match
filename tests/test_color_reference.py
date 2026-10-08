"""External validation of the hand-rolled sRGB<->CIELab math.

Anchor L*a*b* values are standard sRGB/D65 references (e.g. as tabulated by
Bruce Lindbloom), independent of this codebase's own matrices, so a shared
wrong constant in both conversion directions cannot hide behind round-trip
self-consistency alone.
"""

import numpy as np
import pytest

from lumamatch.color import lab_l_channel, lab_to_srgb, srgb_to_lab

# (name, rgb, expected_L, expected_a, expected_b)
REFERENCE_ANCHORS = [
    ("black", (0, 0, 0), 0.0, 0.0, 0.0),
    ("white", (255, 255, 255), 100.0, 0.0, 0.0),
    ("mid_grey_128", (128, 128, 128), 53.59, 0.0, 0.0),
    ("pure_red", (255, 0, 0), 53.24, 80.09, 67.20),
    ("pure_green", (0, 255, 0), 87.73, -86.18, 83.18),
    ("pure_blue", (0, 0, 255), 32.30, 79.19, -107.86),
]


@pytest.mark.parametrize(
    "rgb,expected_l,expected_a,expected_b",
    [anchor[1:] for anchor in REFERENCE_ANCHORS],
    ids=[anchor[0] for anchor in REFERENCE_ANCHORS],
)
def test_known_anchor_matches_reference_lab(rgb, expected_l, expected_a, expected_b):
    pixel = np.array([[rgb]], dtype=np.uint8)
    lab = srgb_to_lab(pixel)
    assert lab[0, 0, 0] == pytest.approx(expected_l, abs=0.05)
    assert lab[0, 0, 1] == pytest.approx(expected_a, abs=0.05)
    assert lab[0, 0, 2] == pytest.approx(expected_b, abs=0.05)


def test_strided_rgb_cube_round_trips_byte_exact():
    values = np.arange(0, 256, 17, dtype=np.uint8)
    r, g, b = np.meshgrid(values, values, values, indexing="ij")
    cube = np.stack([r, g, b], axis=-1).reshape(64, 64, 3)

    recovered, _ = lab_to_srgb(srgb_to_lab(cube))

    np.testing.assert_array_equal(recovered, cube)


def test_grey_levels_have_monotonically_increasing_l():
    greys = np.arange(256, dtype=np.uint8)
    rgb = np.stack([greys, greys, greys], axis=-1).reshape(1, 256, 3)
    lab = srgb_to_lab(rgb)
    lum = lab_l_channel(lab)
    assert np.all(np.diff(lum) > 0)


def test_replacing_l_leaves_a_b_bit_identical():
    rng = np.random.default_rng(1)
    rgb = rng.integers(0, 256, size=(32, 32, 3), dtype=np.uint8)
    lab = srgb_to_lab(rgb)

    replaced = lab.copy()
    replaced[..., 0] = rng.uniform(0, 100, size=(32, 32))

    np.testing.assert_array_equal(replaced[..., 1], lab[..., 1])
    np.testing.assert_array_equal(replaced[..., 2], lab[..., 2])
