"""Random monotonic L* tone curve generator, used to manufacture "image 2".

A curve distorts a known-good reference image's L* channel; the pipeline's
job is to undo that distortion and recover the reference's histogram. The
curve is built as a cumulative sum of strictly-positive increments, which
guarantees strict monotonicity structurally rather than by rejection
sampling, then rescaled onto a random sub-range of [0, 100] so the test
suite exercises both gamma-like and heavily range-compressing distortions.
"""

import numpy as np

from lumamatch.color import lab_to_srgb, srgb_to_lab
from lumamatch.histogram import L_MAX, L_MIN, bin_centers

MIN_INCREMENT = 0.05
MAX_INCREMENT = 1.0


def random_monotonic_curve(rng: np.random.Generator, bins: int) -> np.ndarray:
    """Return a strictly-increasing float64 curve of length `bins` over [0, 100]."""
    increments = rng.uniform(MIN_INCREMENT, MAX_INCREMENT, size=bins)
    curve = np.cumsum(increments)

    low = rng.uniform(0.0, 25.0)
    high = rng.uniform(75.0, 100.0)
    curve = low + (curve - curve[0]) * (high - low) / (curve[-1] - curve[0])

    curve = np.clip(curve, L_MIN, L_MAX)

    if not np.all(np.isfinite(curve)):
        raise ValueError("curve contains NaN or inf")
    if not np.all(np.diff(curve) > 0):
        raise ValueError("curve is not strictly increasing")

    return curve


def apply_curve_to_image(rgb: np.ndarray, curve: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """Apply `curve` to the L* channel of `rgb`, leaving a*/b* untouched.

    Returns a uint8 RGB array of the same shape as `rgb`.
    """
    lab = srgb_to_lab(rgb)
    centers = bin_centers(edges)
    lab = lab.copy()
    lab[..., 0] = np.interp(lab[..., 0], centers, curve)
    distorted, _clipped_fraction = lab_to_srgb(lab)
    return distorted
