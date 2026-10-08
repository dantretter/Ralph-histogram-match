"""Monotonic tone LUT via CDF histogram specification.

In one dimension, the optimal transport map under any convex cost is the
monotone rearrangement T = F_ref^-1 . F_src. Classic CDF-based histogram
specification computes exactly this map, so it IS the EMD minimizer over
monotonic maps between the source and reference L* distributions — no search
or optimizer is required, the answer is closed-form and exact.
"""

import numpy as np

from lumamatch.histogram import L_MAX, L_MIN, bin_centers, to_pmf


def build_lut(src_counts: np.ndarray, ref_counts: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """Return the monotonic L* LUT that maps `src_counts` onto `ref_counts`.

    Args:
        src_counts: histogram counts for the image being transformed.
        ref_counts: histogram counts for the reference distribution, same
            shape as `src_counts`.
        edges: shared bin edges, length `len(src_counts) + 1`.

    Returns:
        float64 array of length `len(src_counts)`: the output L* value for
        each source bin, non-decreasing and clipped to [L_MIN, L_MAX].
    """
    if src_counts.shape != ref_counts.shape:
        raise ValueError(
            f"src_counts and ref_counts must have the same shape, "
            f"got {src_counts.shape} and {ref_counts.shape}"
        )
    if len(edges) != len(src_counts) + 1:
        raise ValueError(
            f"edges must have length len(src_counts) + 1, "
            f"got {len(edges)} edges for {len(src_counts)} counts"
        )

    src_cdf = np.cumsum(to_pmf(src_counts))
    ref_cdf = np.cumsum(to_pmf(ref_counts))
    src_cdf[-1] = 1.0
    ref_cdf[-1] = 1.0

    centers = bin_centers(edges)
    # Where ref_cdf is flat (empty reference bins), np.interp returns the
    # value at the first matching x, i.e. the left-continuous inverse. That
    # biases mapped values toward the low end of the plateau, which is the
    # correct monotone choice — averaging across a plateau could break
    # monotonicity instead.
    lut = np.interp(src_cdf, ref_cdf, centers)

    # Defensive: the interpolation above is already monotone by
    # construction, but this makes the non-decreasing guarantee
    # unconditional and cheap. Pixel ordering must never be reversed.
    lut = np.maximum.accumulate(lut)
    lut = np.clip(lut, L_MIN, L_MAX)

    assert_monotonic(lut)
    return lut


def apply_lut(l_star: np.ndarray, lut: np.ndarray, edges: np.ndarray) -> np.ndarray:
    """Map `l_star` through `lut` with linear interpolation over bin centers.

    Args:
        l_star: L* values of any shape.
        lut: per-bin output L* values, non-decreasing, length `bins`.
        edges: shared bin edges, length `len(lut) + 1`.

    Returns:
        float64 array the same shape as `l_star`, clipped to [L_MIN, L_MAX].
        Values at or below the first bin center clamp to `lut[0]`; values at
        or above the last bin center clamp to `lut[-1]`.
    """
    if len(lut) + 1 != len(edges):
        raise ValueError(
            f"edges must have length len(lut) + 1, got {len(edges)} edges for {len(lut)} lut values"
        )
    assert_monotonic(lut)

    centers = bin_centers(edges)
    values = np.asarray(l_star, dtype=np.float64)
    result = np.interp(values.ravel(), centers, lut)
    result = np.clip(result, L_MIN, L_MAX)
    return result.reshape(values.shape)


def assert_monotonic(lut: np.ndarray) -> None:
    """Raise `ValueError` unless `lut` is finite and non-decreasing."""
    if not np.all(np.isfinite(lut)):
        raise ValueError("LUT contains NaN or inf")
    if np.any(np.diff(lut) < 0):
        raise ValueError("LUT is not non-decreasing")
