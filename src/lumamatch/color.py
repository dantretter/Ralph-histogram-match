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

# CIE XYZ to linear sRGB, D65 white point: the exact inverse of SRGB_TO_XYZ,
# derived rather than hardcoded so the two matrices can never drift apart.
XYZ_TO_SRGB = np.linalg.inv(SRGB_TO_XYZ)


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


def _lab_f_inv(t: np.ndarray) -> np.ndarray:
    """Inverse of the CIE Lab nonlinearity. `t` is in f-space."""
    return np.where(t > DELTA, t**3, 3 * DELTA**2 * (t - 4 / 29))


def _xyz_to_linear_rgb(xyz: np.ndarray) -> np.ndarray:
    """Convert CIE XYZ (H, W, 3) to linear sRGB (H, W, 3)."""
    return xyz @ XYZ_TO_SRGB.T


def _linear_to_srgb(c: np.ndarray) -> np.ndarray:
    """Apply the forward sRGB transfer function. `c` is linear-light, may be out of [0, 1]."""
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.abs(c) ** (1 / 2.4) - 0.055)


def lab_to_srgb(lab: np.ndarray) -> tuple[np.ndarray, float]:
    """Convert CIELab back to 8-bit sRGB, the exact inverse of `srgb_to_lab`.

    Args:
        lab: float64 array of shape (H, W, 3) with channels L*, a*, b*.

    Returns:
        A tuple of (uint8 array of shape (H, W, 3), clipped_fraction), where
        clipped_fraction is the fraction of pixels where any channel fell
        outside [0, 1] before clipping, in [0.0, 1.0].
    """
    if lab.dtype != np.float64:
        raise ValueError(f"lab must be float64, got dtype {lab.dtype}")
    if lab.ndim != 3 or lab.shape[2] != 3:
        raise ValueError(f"lab must have shape (H, W, 3), got shape {lab.shape}")

    lum = lab[..., 0]
    a = lab[..., 1]
    b = lab[..., 2]

    fy = (lum + 16) / 116
    fx = fy + a / 500
    fz = fy - b / 200

    xyz_r = np.stack([_lab_f_inv(fx), _lab_f_inv(fy), _lab_f_inv(fz)], axis=-1)
    xyz = xyz_r * D65_WHITE

    rgb_lin = _xyz_to_linear_rgb(xyz)
    srgb = _linear_to_srgb(rgb_lin)

    out_of_range = (srgb < 0.0) | (srgb > 1.0)
    clipped_pixels = np.any(out_of_range, axis=-1)
    clipped_fraction = float(clipped_pixels.mean()) if clipped_pixels.size else 0.0

    srgb = np.clip(srgb, 0.0, 1.0)
    rgb = np.floor(srgb * 255.0 + 0.5).astype(np.uint8)
    return rgb, clipped_fraction
