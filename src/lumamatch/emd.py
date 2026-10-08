"""1-D Earth Mover's Distance (Wasserstein-1) between L* histograms.

For one-dimensional distributions, the optimal transport cost reduces to the
integral of the absolute CDF difference, so no optimal-transport solver is
needed. Both histograms are normalized to PMFs first, so inputs with
different total pixel counts remain directly comparable.
"""

import numpy as np

from lumamatch.histogram import bin_width, to_pmf


def emd(counts_a: np.ndarray, counts_b: np.ndarray, edges: np.ndarray) -> float:
    """Return the Wasserstein-1 distance between two histograms, in L* units.

    Args:
        counts_a: histogram counts for distribution A.
        counts_b: histogram counts for distribution B, same shape as `counts_a`.
        edges: shared bin edges, length `len(counts_a) + 1`.
    """
    if counts_a.shape != counts_b.shape:
        raise ValueError(
            f"counts_a and counts_b must have the same shape, "
            f"got {counts_a.shape} and {counts_b.shape}"
        )
    if len(edges) != len(counts_a) + 1:
        raise ValueError(
            f"edges must have length len(counts) + 1, "
            f"got {len(edges)} edges for {len(counts_a)} counts"
        )

    pmf_a = to_pmf(counts_a)
    pmf_b = to_pmf(counts_b)
    cdf_a = np.cumsum(pmf_a)
    cdf_b = np.cumsum(pmf_b)
    return float(np.abs(cdf_a - cdf_b).sum() * bin_width(edges))


def emd_reduction(before: float, after: float) -> float:
    """Return the fractional EMD reduction `1.0 - after / before`.

    A negative result means the match got worse and is returned as-is, not
    clamped, so a regression stays visible.
    """
    if before == 0.0:
        return 0.0
    return 1.0 - after / before
