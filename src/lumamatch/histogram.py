"""Fixed-domain L* histogram.

The domain is fixed at [0, 100] rather than data-derived so that any two
histograms produced by this tool share identical bin edges and are directly
comparable. This is a prerequisite for both the EMD calculation and the
CDF-based LUT.
"""

import numpy as np

DEFAULT_BINS = 256
L_MIN = 0.0
L_MAX = 100.0


def bin_edges(bins: int) -> np.ndarray:
    """Return `bins + 1` uniform edges over the fixed [L_MIN, L_MAX] domain."""
    return np.linspace(L_MIN, L_MAX, bins + 1)


def bin_centers(edges: np.ndarray) -> np.ndarray:
    """Return the midpoint of each bin given its edges."""
    return 0.5 * (edges[:-1] + edges[1:])


def bin_width(edges: np.ndarray) -> float:
    """Return the width of a single (uniform) bin."""
    return float(edges[1] - edges[0])


def l_histogram(l_star: np.ndarray, bins: int = DEFAULT_BINS) -> tuple[np.ndarray, np.ndarray]:
    """Compute a histogram of L* values over the fixed [0, 100] domain.

    Args:
        l_star: array of L* values, any shape.
        bins: number of uniform bins over [0, 100].

    Returns:
        A tuple of (int64 counts of length `bins`, float64 edges of length
        `bins + 1`). Values outside [0, 100] are clipped into range rather
        than discarded, so `counts.sum() == l_star.size` always holds.
    """
    if bins < 2:
        raise ValueError("bins must be >= 2")

    values = np.ravel(l_star).astype(np.float64, copy=False)
    if values.size == 0:
        raise ValueError("l_star must contain at least one pixel")

    clipped = np.clip(values, L_MIN, L_MAX)
    counts, _ = np.histogram(clipped, bins=bins, range=(L_MIN, L_MAX))

    edges = bin_edges(bins)
    return counts.astype(np.int64), edges.astype(np.float64)


def to_pmf(counts: np.ndarray) -> np.ndarray:
    """Normalize histogram counts into a probability mass function."""
    total = counts.sum()
    if total == 0:
        raise ValueError("counts must not sum to zero")
    return counts.astype(np.float64) / total
