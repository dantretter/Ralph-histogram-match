"""Self-test for the synthetic image fixtures in `images.py`."""

import numpy as np

from lumamatch.color import srgb_to_lab
from lumamatch.histogram import DEFAULT_BINS, l_histogram
from tests.images import flat_image, gradient_image, synthetic_reference


def test_synthetic_reference_is_deterministic():
    image_a = synthetic_reference(np.random.default_rng(0))
    image_b = synthetic_reference(np.random.default_rng(0))
    assert np.array_equal(image_a, image_b)


def test_synthetic_reference_shape_and_dtype():
    image = synthetic_reference(np.random.default_rng(0), height=128, width=192)
    assert image.shape == (128, 192, 3)
    assert image.dtype == np.uint8


def test_synthetic_reference_has_broad_l_histogram():
    image = synthetic_reference(np.random.default_rng(0))
    lab = srgb_to_lab(image)
    counts, _ = l_histogram(lab[..., 0], bins=DEFAULT_BINS)
    assert np.count_nonzero(counts) >= 200


def test_synthetic_reference_spans_l_range():
    image = synthetic_reference(np.random.default_rng(0))
    lab = srgb_to_lab(image)
    l_star = lab[..., 0]
    assert l_star.min() <= 5
    assert l_star.max() >= 95


def test_synthetic_reference_has_saturated_chroma():
    image = synthetic_reference(np.random.default_rng(0))
    lab = srgb_to_lab(image)
    chroma = np.hypot(lab[..., 1], lab[..., 2])
    assert chroma.max() > 40


def test_flat_image_has_one_unique_value():
    image = flat_image(128)
    assert np.unique(image).size == 1
    assert np.all(image == 128)


def test_gradient_image_has_many_unique_levels():
    image = gradient_image()
    assert np.unique(image).size > 200
