"""Synthetic test images for the round-trip and banding test suites.

`synthetic_reference` is the fixture the TASK-21 round-trip test distorts and
tries to recover. Its L* distribution must be broad and its colors must be
saturated enough to exercise gamut clipping, or the round-trip test would
pass trivially and hide real bugs. A diagonal grey gradient supplies the
broad L* coverage; saturated color patches supply the chroma; mild noise
fills in histogram bins a pure gradient would leave sparse.
"""

import numpy as np

PATCH_ROWS = 2
PATCH_COLS = 4
NOISE_SIGMA = 4.0

_FIXED_SATURATED_COLORS = [
    (255, 0, 0),
    (0, 255, 0),
    (0, 0, 255),
    (0, 255, 255),
    (255, 0, 255),
    (255, 255, 0),
]


def _random_saturated_color(rng: np.random.Generator) -> tuple[int, int, int]:
    """Return a random non-grey corner of the RGB cube (chroma well above 40)."""
    while True:
        corner = rng.integers(0, 2, size=3) * 255
        if not (corner[0] == corner[1] == corner[2]):
            return int(corner[0]), int(corner[1]), int(corner[2])


def synthetic_reference(
    rng: np.random.Generator, height: int = 128, width: int = 192
) -> np.ndarray:
    """Build a deterministic synthetic RGB image with broad L* coverage and real chroma.

    A diagonal grey gradient spans the full tonal range, saturated color
    patches are stamped at deterministic grid positions to exercise gamut
    clipping, and mild noise is added to populate the full histogram.
    """
    x_ramp = np.linspace(0.0, 255.0, width)
    y_ramp = np.linspace(0.0, 255.0, height)
    base = (x_ramp[None, :] + y_ramp[:, None]) / 2.0
    image = np.repeat(base[:, :, None], 3, axis=2)

    colors = [*_FIXED_SATURATED_COLORS, _random_saturated_color(rng), _random_saturated_color(rng)]

    cell_h = max(1, height // PATCH_ROWS)
    cell_w = max(1, width // PATCH_COLS)
    patch_h = max(1, cell_h // 2)
    patch_w = max(1, cell_w // 2)

    for i, color in enumerate(colors):
        row, col = divmod(i, PATCH_COLS)
        y0 = row * cell_h + (cell_h - patch_h) // 2
        x0 = col * cell_w + (cell_w - patch_w) // 2
        y1 = min(height, y0 + patch_h)
        x1 = min(width, x0 + patch_w)
        image[y0:y1, x0:x1] = color

    noise = rng.normal(0.0, NOISE_SIGMA, size=image.shape)
    image = np.clip(image + noise, 0, 255)
    return image.astype(np.uint8)


def flat_image(value: int, height: int = 32, width: int = 32) -> np.ndarray:
    """A single-color image, for degenerate edge-case tests."""
    return np.full((height, width, 3), value, dtype=np.uint8)


def gradient_image(height: int = 64, width: int = 1024) -> np.ndarray:
    """A smooth grayscale ramp, for the anti-banding check."""
    ramp = np.round(np.linspace(0.0, 255.0, width))
    image = np.tile(ramp, (height, 1))
    return np.repeat(image[:, :, None], 3, axis=2).astype(np.uint8)
