"""Image loading and saving for HEIC/HEIF, JPG, and PNG.

Normalizes format differences (palette, grayscale, alpha, EXIF orientation)
so the rest of the pipeline only ever sees a uint8 (H, W, 3) RGB array.
Saving writes back to the format implied by the output extension, without
carrying over any source EXIF/ICC metadata.
"""

import warnings
from pathlib import Path

import numpy as np
import pillow_heif
from PIL import Image, ImageOps, UnidentifiedImageError

# Must be called before any .heic/.heif file is opened via Image.open.
pillow_heif.register_heif_opener()

# Pillow's Image.MAX_IMAGE_PIXELS decompression-bomb guard is intentionally
# left at its default (~89 million pixels) and must never be raised or set to
# None here: untrusted images are this tool's only real attack surface, and
# disabling the guard to silence a warning would reopen a DoS vector.

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
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(resolved) as img:
                img = ImageOps.exif_transpose(img) or img
                if img.mode != "RGB":
                    img = img.convert("RGB")
                array = np.asarray(img, dtype=np.uint8)
    except (Image.DecompressionBombWarning, Image.DecompressionBombError) as exc:
        raise ValueError(f"refusing to decode {resolved}: image too large") from exc
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError(f"could not decode {resolved}: {exc}") from exc

    if array.ndim != 3 or array.shape[2] != 3:
        raise ValueError(f"unexpected array shape {array.shape} decoding {resolved}")

    return array


def _validate_output(path: Path | str) -> Path:
    """Resolve an output path, checking extension support and parent dir."""
    resolved = Path(path).expanduser().resolve()
    suffix = resolved.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise ValueError(f"unsupported image format '{suffix}'; supported: {supported}")
    if not resolved.parent.is_dir():
        raise FileNotFoundError(str(resolved.parent))
    return resolved


def _save_kwargs(suffix: str, quality: int) -> dict:
    """Build format-specific Pillow save kwargs for a given extension."""
    if suffix in (".jpg", ".jpeg"):
        return {"quality": quality, "subsampling": 0, "optimize": True}
    if suffix in (".heic", ".heif"):
        return {"quality": quality}
    return {"optimize": True}


def save_rgb(path: Path | str, rgb: np.ndarray, quality: int = 95) -> None:
    """Save a uint8 (H, W, 3) RGB array to the format implied by path's extension.

    No EXIF or ICC metadata is written, regardless of source. JPEG is saved
    with subsampling=0 (4:4:4) to minimize chroma damage; PNG is lossless.
    """
    resolved = _validate_output(path)

    if rgb.dtype != np.uint8:
        raise ValueError(f"expected uint8 array, got dtype {rgb.dtype}")
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError(f"expected (H, W, 3) array, got shape {rgb.shape}")

    kwargs = _save_kwargs(resolved.suffix.lower(), quality)

    try:
        img = Image.fromarray(rgb, mode="RGB")
        img.save(resolved, **kwargs)
    except OSError as exc:
        raise ValueError(f"could not write {resolved}: {exc}") from exc
