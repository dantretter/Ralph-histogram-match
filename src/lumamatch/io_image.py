"""Image loading for HEIC/HEIF, JPG, and PNG.

Normalizes format differences (palette, grayscale, alpha, EXIF orientation)
so the rest of the pipeline only ever sees a uint8 (H, W, 3) RGB array.
"""

from pathlib import Path

import numpy as np
import pillow_heif
from PIL import Image, ImageOps, UnidentifiedImageError

# Must be called before any .heic/.heif file is opened via Image.open.
pillow_heif.register_heif_opener()

SUPPORTED_EXTENSIONS = frozenset({".heic", ".heif", ".jpg", ".jpeg", ".png"})


def _validate_source(path: Path | str) -> Path:
    """Resolve path, checking extension support and file existence."""
    resolved = Path(path).expanduser().resolve()
    suffix = resolved.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"unsupported image format '{suffix}'; supported: {supported}")
    if not resolved.is_file():
        raise FileNotFoundError(str(resolved))
    return resolved


def load_rgb(path: Path | str) -> np.ndarray:
    """Load an image file as a uint8 RGB array of shape (H, W, 3)."""
    resolved = _validate_source(path)

    try:
        with Image.open(resolved) as img:
            img = ImageOps.exif_transpose(img) or img
            if img.mode != "RGB":
                img = img.convert("RGB")
            array = np.asarray(img, dtype=np.uint8)
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"could not decode {resolved}: {exc}") from exc

    if array.ndim != 3 or array.shape[2] != 3:
        raise ValueError(f"unexpected array shape {array.shape} decoding {resolved}")

    return array
