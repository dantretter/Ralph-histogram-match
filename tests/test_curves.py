import numpy as np

from lumamatch.color import srgb_to_lab
from lumamatch.histogram import L_MAX, L_MIN, bin_edges
from tests.curves import apply_curve_to_image, random_monotonic_curve

BINS = 256


def test_strict_monotonicity_and_range_over_seeds():
    for seed in range(20):
        rng = np.random.default_rng(seed)
        curve = random_monotonic_curve(rng, BINS)

        assert np.all(np.diff(curve) > 0)
        assert np.all(curve >= L_MIN)
        assert np.all(curve <= L_MAX)


def test_determinism_for_same_seed():
    curve_a = random_monotonic_curve(np.random.default_rng(42), BINS)
    curve_b = random_monotonic_curve(np.random.default_rng(42), BINS)

    assert np.array_equal(curve_a, curve_b)


def test_different_seeds_produce_visibly_different_curves():
    curve_0 = random_monotonic_curve(np.random.default_rng(0), BINS)
    curve_1 = random_monotonic_curve(np.random.default_rng(1), BINS)

    assert np.mean(np.abs(curve_0 - curve_1)) > 1.0


def test_apply_curve_to_image_shape_and_dtype():
    rng = np.random.default_rng(7)
    rgb = rng.integers(0, 256, size=(16, 16, 3), dtype=np.uint8)
    edges = bin_edges(BINS)
    curve = random_monotonic_curve(np.random.default_rng(1), BINS)

    out = apply_curve_to_image(rgb, curve, edges)

    assert out.shape == rgb.shape
    assert out.dtype == np.uint8


def test_apply_curve_to_image_preserves_ab():
    # Mid-range, muted colors stay well inside the sRGB gamut even after a
    # large L* shift, so this isolates the a*/b* preservation guarantee from
    # the separate (and already-reported) gamut-clipping behavior.
    rng = np.random.default_rng(13)
    rgb = rng.integers(64, 192, size=(16, 16, 3), dtype=np.uint8)
    edges = bin_edges(BINS)
    curve = random_monotonic_curve(np.random.default_rng(2), BINS)

    out = apply_curve_to_image(rgb, curve, edges)

    lab_src = srgb_to_lab(rgb)
    lab_out = srgb_to_lab(out)

    np.testing.assert_allclose(lab_out[..., 1], lab_src[..., 1], atol=1.0)
    np.testing.assert_allclose(lab_out[..., 2], lab_src[..., 2], atol=1.0)
