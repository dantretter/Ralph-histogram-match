"""Hand-rolled sRGB <-> CIELab conversion (D65 white point, float64).

Reference: standard sRGB/D65 primaries and D65 reference white, as tabulated
by Bruce Lindbloom (http://www.brucelindbloom.com/index.html?Eqn_RGB_XYZ_Matrix.html).
"""

import numpy as np

# sRGB (linear) to CIE XYZ, D65 white point (Lindbloom / IEC 61966-2-1).
SRGB_TO_XYZ = np.array(
    [
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041],
    ]
)

# D65 reference white in XYZ (Y normalized to 1.0): 0.95047 / 1.00000 / 1.08883
# to 7 decimal places. Derived as the matrix's own row sums (RGB (1,1,1) through
# SRGB_TO_XYZ) rather than re-entered as independently-rounded literals, so pure
# white round-trips to L*=100, a*=b*=0 at float precision instead of leaving
# ~1e-5 noise from the matrix's Y row summing to 1.0000001, not exactly 1.0.
D65_WHITE = SRGB_TO_XYZ @ np.array([1.0, 1.0, 1.0])

# CIE Lab piecewise-linear/cubic threshold, as a fraction of (6/29).
DELTA = 6 / 29
DELTA_CUBED = DELTA**3


def _srgb_to_linear(c: np.ndarray) -> np.ndarray:
    """Invert the sRGB transfer function. `c` is float64 in [0, 1]."""
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _linear_rgb_to_xyz(rgb_lin: np.ndarray) -> np.ndarray:
    """Convert linear sRGB (H, W, 3) to CIE XYZ (H, W, 3), Y in [0, 1]."""
    return rgb_lin @ SRGB_TO_XYZ.T


def _lab_f(t: np.ndarray) -> np.ndarray:
    """CIE Lab nonlinearity. Uses cbrt so float noise never yields NaN."""
    return np.where(t > DELTA_CUBED, np.cbrt(t), t / (3 * DELTA**2) + 4 / 29)


def srgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """Convert an 8-bit sRGB image to CIELab.

    Args:
        rgb: uint8 array of shape (H, W, 3).

    Returns:
        float64 array of shape (H, W, 3) with channels L*, a*, b*.
        L* is clipped to [0, 100] to absorb floating-point noise.
    """
    if rgb.dtype != np.uint8:
        raise ValueError(f"rgb must be uint8, got dtype {rgb.dtype}")
    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError(f"rgb must have shape (H, W, 3), got shape {rgb.shape}")

    rgb_norm = rgb.astype(np.float64) / 255.0
    rgb_lin = _srgb_to_linear(rgb_norm)
    xyz = _linear_rgb_to_xyz(rgb_lin)
    xyz_r = xyz / D65_WHITE

    fx = _lab_f(xyz_r[..., 0])
    fy = _lab_f(xyz_r[..., 1])
    fz = _lab_f(xyz_r[..., 2])

    lum = 116 * fy - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)

    lab = np.stack([lum, a, b], axis=-1)
    lab[..., 0] = np.clip(lab[..., 0], 0, 100)
    return lab


def lab_l_channel(lab: np.ndarray) -> np.ndarray:
    """Return a contiguous float64 copy of the L* channel."""
    return np.ascontiguousarray(lab[..., 0])
