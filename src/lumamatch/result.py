"""The complete output of one match operation.

`MatchResult` is the single hand-off object between the pipeline, the CSV
writer, and the CLI reporter. It is frozen and its array fields are made
read-only in `__post_init__`, so none of its consumers may mutate it.
"""

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from lumamatch.emd import emd_reduction as _emd_reduction


@dataclass(frozen=True)
class MatchResult:
    """Complete output of one match operation.

    Arrays (`edges`, `hist_reference`, `hist_target`, `hist_target_matched`,
    `lut`) must not be mutated by consumers; they are marked read-only.
    """

    reference_path: Path
    target_path: Path
    bins: int
    edges: np.ndarray
    hist_reference: np.ndarray
    hist_target: np.ndarray
    hist_target_matched: np.ndarray
    lut: np.ndarray
    emd_before: float
    emd_after: float
    clipped_fraction: float
    reference_pixels: int
    target_pixels: int
    image_out: Path
    csv_out: Path

    def __post_init__(self) -> None:
        for name in ("hist_reference", "hist_target", "hist_target_matched", "lut"):
            arr = getattr(self, name)
            if len(arr) != self.bins:
                raise ValueError(f"{name} must have length bins ({self.bins}), got {len(arr)}")
        if len(self.edges) != self.bins + 1:
            raise ValueError(
                f"edges must have length bins + 1 ({self.bins + 1}), got {len(self.edges)}"
            )

        if not (0.0 <= self.clipped_fraction <= 1.0):
            raise ValueError(
                f"clipped_fraction must be within [0.0, 1.0], got {self.clipped_fraction}"
            )

        if int(self.hist_reference.sum()) != self.reference_pixels:
            raise ValueError(
                f"hist_reference sums to {int(self.hist_reference.sum())}, "
                f"expected reference_pixels ({self.reference_pixels})"
            )
        for name in ("hist_target", "hist_target_matched"):
            arr = getattr(self, name)
            if int(arr.sum()) != self.target_pixels:
                raise ValueError(
                    f"{name} sums to {int(arr.sum())}, "
                    f"expected target_pixels ({self.target_pixels})"
                )

        for name in ("edges", "hist_reference", "hist_target", "hist_target_matched", "lut"):
            getattr(self, name).flags.writeable = False

    @property
    def emd_reduction(self) -> float:
        """Fractional EMD improvement between `emd_before` and `emd_after`."""
        return _emd_reduction(self.emd_before, self.emd_after)
