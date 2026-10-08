"""Output path resolution and overwrite guard.

Both outputs for a match operation live beside the target image, using a
fixed naming scheme rather than user-supplied overrides (the PRD intentionally
does not expose `--out-image`/`--out-csv`). This module has no dependency on
numpy, PIL, or any other project module, so it stays trivially testable.
"""

import os
from pathlib import Path

MATCHED_SUFFIX = "_matched"
CSV_SUFFIX = "_histograms"
CSV_EXTENSION = ".csv"


def resolve_outputs(target_path: Path | str, force: bool = False) -> tuple[Path, Path]:
    """Derive the matched-image and histogram-CSV output paths for a target image.

    Args:
        target_path: path to the image being modified (image 2).
        force: if True, skip the overwrite guard.

    Returns:
        A tuple of (image_out, csv_out), both in the target's parent directory.

    Raises:
        FileNotFoundError: if the target's parent directory does not exist.
        PermissionError: if the target's parent directory is not writable.
        FileExistsError: if `force` is False and either output already exists.
            Both existence checks run before raising, so the error always
            reflects the full picture and nothing is written either way.
    """
    target = Path(target_path).expanduser()
    parent = target.parent
    stem = target.stem
    suffix = target.suffix

    if not parent.is_dir():
        raise FileNotFoundError(f"directory does not exist: {parent}")
    if not os.access(parent, os.W_OK):
        raise PermissionError(f"cannot write to {parent}")

    # A target already named `*_matched.ext` yields `*_matched_matched.ext`.
    # This is intentional, not a bug: special-casing it would be surprising
    # in its own way, and the plain concatenation is never ambiguous.
    image_out = parent / f"{stem}{MATCHED_SUFFIX}{suffix}"
    csv_out = parent / f"{stem}{CSV_SUFFIX}{CSV_EXTENSION}"

    if not force:
        if image_out.exists():
            raise FileExistsError(f"{image_out} already exists (use --force to overwrite)")
        if csv_out.exists():
            raise FileExistsError(f"{csv_out} already exists (use --force to overwrite)")

    return image_out, csv_out
