# Project Build Log

`Current Status`
=================
**Last Updated:** 2026-10-08
**Tasks Completed:** 12 / 26
**Current Task:** TASK-12 Complete

----------------------------------------------

## Session Log

## 2026-10-08 — TASK-12: Implement interpolated LUT application to L* channel

Added `apply_lut(l_star, lut, edges) -> np.ndarray` to `src/lumamatch/tonemap.py`. Interpolates
per-pixel L* values against bin centers (not edges, to avoid a half-bin shift) via `np.interp`,
clamping outside the center range to `lut[0]`/`lut[-1]` and clipping to `[L_MIN, L_MAX]`.
Validates `len(lut) + 1 == len(edges)` and calls `assert_monotonic(lut)` before applying. New
`tests/test_tonemap_apply.py` covers shape/dtype preservation, range, monotonicity, equal-input
equality, end clamping, an anti-banding gradient check (more unique outputs than bins), identity
LUT tolerance, and the mismatched-length error path.

## 2026-10-08 — TASK-11: Implement monotonic tone LUT via CDF histogram specification

Added `src/lumamatch/tonemap.py`: `build_lut(src_counts, ref_counts, edges) -> np.ndarray`, the
core of the tool. The LUT is **closed-form optimal, not iterative** — in one dimension the
optimal transport map under any convex cost is the monotone rearrangement
`T = F_ref^-1 . F_src`, so CDF-based histogram specification is exactly the EMD minimizer over
monotonic maps. No greedy bin walk, no search, no optimizer.
- Validates shapes/edges length up front, same pattern as `emd.py`.
- Forces `cdf[-1] = 1.0` on both CDFs before inverting — cumsum of a PMF can land at
  `0.9999999999999998`, which would otherwise leave the brightest source bin short of the
  reference maximum and create a small systematic EMD floor.
- Inversion is one line: `np.interp(src_cdf, ref_cdf, centers)`. Where `ref_cdf` is flat (empty
  reference bins), `np.interp` returns the value at the first matching x — the left-continuous
  inverse, which is the correct monotone choice; averaging across a plateau could break
  monotonicity instead.
- `np.maximum.accumulate` + `np.clip` after the interpolation are defensive, not corrective: the
  interpolation is already monotone by construction, but this makes the non-decreasing guarantee
  unconditional and cheap, since preserved pixel ordering is a hard product requirement.
- `assert_monotonic(lut)` raises `ValueError` on any decrease or non-finite value; called at the
  end of `build_lut` so a violation can never escape into the pipeline, and reused directly from
  tests.
- `tests/test_tonemap_lut.py`: identity case (LUT within 0.5 L* of bin centers), monotonicity and
  finiteness across 50 seeded random histogram pairs, full-range bound checks, degenerate source
  (single spike) and degenerate reference (single spike) cases, mismatched-length `ValueError`
  paths, and direct `assert_monotonic` checks.
- Verified: `.venv/bin/pytest -q` → 173 passed; `.venv/bin/ruff check src tests` → clean;
  `ruff format` → no changes needed.

## 2026-10-08 — TASK-10: Implement Earth Mover's Distance between two histograms

Added `src/lumamatch/emd.py`: `emd(counts_a, counts_b, edges) -> float`, the 1-D Wasserstein-1
distance in L* units, reusing `to_pmf`/`bin_width` from `histogram.py` rather than reimplementing
normalization.
- Validates `counts_a.shape == counts_b.shape` and `len(edges) == len(counts_a) + 1` before any
  computation, raising `ValueError` naming the actual lengths.
- Core formula is two lines: PMF-normalize both histograms, `np.cumsum` each, then
  `abs(cdf_a - cdf_b).sum() * bin_width(edges)` — the bin-width multiplication is what converts
  the result from bin-index units to L* units, which is what makes the number comparable across
  different `--bins` values. No optimal-transport solver and no scipy dependency.
- `emd_reduction(before, after) -> float` returns `1.0 - after / before`, guarding `before == 0.0`
  by returning `0.0`; deliberately *not* clamped to `[0, 1]` so a regression (match got worse)
  surfaces as a visible negative number instead of being hidden at 0.
- `tests/test_emd.py`: analytically-known case (two single-bin spikes 20 bins apart in a 100-bin
  histogram over `[0, 100]` → EMD exactly 20.0, validating both the formula and unit scaling),
  identity (`emd(a, a, edges) == 0.0`), symmetry, scale invariance (`counts * 7` unchanged),
  mismatched-length and all-zero `ValueError` paths, and all four `emd_reduction` cases from the
  spec (typical, perfect match, nothing-to-improve, regression).
- Verified: `.venv/bin/pytest -q` → 65 passed; `.venv/bin/ruff check src tests` → clean;
  `ruff format` → no changes needed.

## 2026-10-08 — TASK-9: Implement fixed-domain L* histogram

Added `src/lumamatch/histogram.py`: `l_histogram(l_star, bins=256)` bins L*
values over a fixed `[0, 100]` domain (`np.clip` then `np.histogram`), always
returning edges from `bin_edges` so every histogram in the pipeline shares
identical bin boundaries. Also added `bin_centers`, `bin_width`, and a
`to_pmf` normalization helper shared by the upcoming EMD and LUT modules.
Covered with `tests/test_histogram.py` (clipping, exact-boundary values,
dtype, `ValueError` cases, helpers).

## 2026-10-08 — TASK-8: Implement save_rgb preserving source format

Added `save_rgb(path, rgb, quality=95) -> None` to `src/lumamatch/io_image.py`, writing the
format implied by the output extension.
- `_validate_output` reuses `SUPPORTED_EXTENSIONS` for the ValueError path and checks
  `path.parent.is_dir()`, raising `FileNotFoundError` for a missing output directory.
- `_save_kwargs(suffix, quality)` is a small pure function: JPEG gets
  `{'quality', 'subsampling': 0, 'optimize': True}` (4:4:4 to avoid chroma-driven L* drift),
  HEIC gets `{'quality'}`, PNG gets `{'optimize': True}` only (lossless, no quality knob).
- `Image.fromarray(rgb, mode='RGB').save(path, **kwargs)` deliberately omits `exif=`/
  `icc_profile=` so no source metadata survives — this is a documented privacy default, not an
  oversight (to be called out in the TASK-26 README).
- Input validation rejects non-uint8 dtype and non-(H, W, 3) shape with `ValueError` before any
  write is attempted; `OSError` from the Pillow save itself is wrapped as `ValueError`.
- `tests/test_io_save.py`: PNG round-trip is byte-exact via `load_rgb`; JPEG/HEIC are checked
  for readability, correct shape/dtype, and (JPEG) mean abs diff < 8 at quality 95; EXIF
  stripping is verified by writing an Orientation tag into a source JPEG and asserting the
  saved output's `getexif()` is empty; error paths cover unsupported extension, missing parent
  directory, wrong dtype, and wrong shape.
- `ruff check`/`format` clean; full suite (43 tests) green.

## 2026-10-08 — TASK-7: Implement load_rgb for HEIC, JPG, and PNG

Added `src/lumamatch/io_image.py`: single `load_rgb(path) -> np.ndarray` loader normalizing
format differences for the rest of the pipeline.
- `pillow_heif.register_heif_opener()` called once at module import, before any `.heic` open.
- `SUPPORTED_EXTENSIONS = frozenset({'.heic', '.heif', '.jpg', '.jpeg', '.png'})`, module-level
  so the future CLI (TASK-17) can reuse it for argument validation.
- `_validate_source` resolves the path, rejects unsupported extensions with a `ValueError`
  listing the supported set, and raises `FileNotFoundError` for a missing file — both checked
  before any decode attempt.
- `ImageOps.exif_transpose(img) or img` applied first (guards the None-on-no-EXIF case per the
  spec's technical note), then `img.convert('RGB')` only when needed — this single call handles
  L, LA, P, and RGBA uniformly: grayscale expands to 3 equal channels, alpha is dropped (not
  composited onto any background, which would otherwise silently alter L* in transparent regions),
  and palette is resolved to true RGB.
- `UnidentifiedImageError`/`OSError` from `Image.open`/decode are caught and re-raised as
  `ValueError(f'could not decode {path}: {exc}')` so no PIL-specific exception type leaks to
  callers.
- `tests/test_io_load.py`: parametrized shape/dtype check across RGB/L/RGBA/P source images in
  PNG, JPG, and HEIC containers; explicit grayscale channel-equality and alpha-drop assertions;
  `.bmp` extension, missing file, and corrupt-bytes-in-a-`.png` error-path tests.
- Verified: `.venv/bin/pytest -q` → 35 passed; `.venv/bin/ruff check src tests` → clean;
  `ruff format` → no changes needed.

## 2026-10-08 — TASK-6: Verify color conversion against known anchors and round-trip

Added `tests/test_color_reference.py` as the authoritative external-validation module for the
color math, separate from the self-consistency round-trip tests in TASK-4/TASK-5.
- 6 parametrized anchors (black, white, mid grey 128, pure red/green/blue) assert `srgb_to_lab`
  against standard sRGB/D65 CIELab reference values, each within `abs=0.05` — proving correctness
  against external truth, not just that both conversion directions agree with each other.
- Strided RGB cube round-trip: `np.meshgrid` over `arange(0, 256, 17)` (16 values per channel,
  4096 combinations, includes both 0 and 255 exactly) reshaped to (64, 64, 3), asserted byte-exact
  through `lab_to_srgb(srgb_to_lab(cube))`.
- Grey-level L* monotonicity: all 256 (i,i,i) greys strictly increasing in L* (`np.diff(l) > 0`).
- a*/b* invariance: overwriting only the L* channel of a random image's Lab array with arbitrary
  values leaves a*/b* bit-identical, locking in the "pipeline only touches lightness" invariant.
- Verified: `.venv/bin/pytest -q` → 24 passed; `.venv/bin/ruff check src tests` → clean;
  `ruff format` → no changes needed. Color math is now externally validated, not just
  self-consistent.

## 2026-10-08 — TASK-5: Implement lab_to_srgb conversion with gamut clipping report

Added `lab_to_srgb` to `src/lumamatch/color.py`, the exact inverse of TASK-4's `srgb_to_lab`.
- `XYZ_TO_SRGB = np.linalg.inv(SRGB_TO_XYZ)` derived once at module level, so the two matrices can't drift apart.
- `_lab_f_inv`, `_xyz_to_linear_rgb`, `_linear_to_srgb` (forward transfer function, `np.abs` under the power to avoid NaN on negative out-of-gamut values) compose in `lab_to_srgb`.
- Gamut clipping is detected *before* clipping: `out_of_range` per channel, `np.any(..., axis=-1)` per pixel, `clipped_fraction` is that boolean mask's mean (0.0 for a zero-size array). Quantization uses `np.floor(srgb * 255.0 + 0.5)` (round-half-away-from-zero), not `np.round` (banker's rounding), per the spec note that banker's rounding breaks the byte-exact round-trip.
- `tests/test_color_inverse.py`: 256 greys and 4096 (64x64) seeded random colors round-trip byte-exact; a uniform in-gamut image reports `clipped_fraction == 0.0`; a deliberately out-of-gamut Lab value (`L*=95, a*=80, b*=-80`) reports `clipped_fraction == 1.0`; both `ValueError` cases (non-float64 dtype, wrong shape).
- **Finding:** the round-trip tests do *not* assert `clipped_fraction == 0.0` — float noise at the 0/255 sRGB boundary can push a handful of pixels a hair outside `[0, 1]` even though they are genuinely in-gamut and still round-trip byte-exact after clipping. The spec's "in-gamut image returns 0.0" criterion is tested separately with a safely mid-range uniform image, matching the task spec's own test breakdown (steps 7a–7e).
- Verified: `.venv/bin/pytest -q` → 15 passed; `.venv/bin/ruff check src tests` → clean; `ruff format` → no changes needed.

## 2026-10-08 — TASK-4: Implement srgb_to_lab conversion

Created `src/lumamatch/color.py`: vectorized, hand-rolled 8-bit sRGB → CIELab (D65), float64 throughout.
- `SRGB_TO_XYZ` is the standard Lindbloom/IEC 61966-2-1 matrix. `D65_WHITE` is derived as the matrix's own row-sum (`SRGB_TO_XYZ @ [1,1,1]`) rather than re-entered as an independently-rounded literal — the published 7-decimal matrix's Y row sums to 1.0000001, not exactly 1.0, so dividing by a separately-rounded white point left ~1.7e-5 noise in a\*/b\* at pure white, failing the 1e-6 tolerance. Deriving the white point from the matrix is mathematically the same value and fixes the round-trip.
- `_srgb_to_linear`, `_linear_rgb_to_xyz`, `_lab_f` (via `np.cbrt` to avoid NaN on float noise), composed in `srgb_to_lab`; `rgb` validated for uint8 dtype and (H,W,3) shape, raising `ValueError` otherwise. `lab_l_channel` returns a contiguous L* copy.
- `tests/test_color_forward.py`: black/white/mid-grey anchors, output dtype/shape, L* range over a random 64x64 image, both `ValueError` cases, and `lab_l_channel` contiguity.
- Verified: `.venv/bin/pytest -q` → 9 passed; `.venv/bin/ruff check src tests` and `ruff format` → clean.

## 2026-10-08 — TASK-3: Scaffold lumamatch Python package, requirements, and ruff config

Scaffolded the `lumamatch` package and toolchain:
- `src/lumamatch/__init__.py` with `__version__ = "0.1.0"`.
- `requirements.txt` pinning `numpy>=2.0`, `pillow>=11.0`, `pillow-heif>=1.0`, `pytest>=8.0`, `ruff>=0.6`.
- `ruff.toml` (line-length 100, select E/F/I/UP/B, excludes `.venv` and `src/node_modules`).
- `pytest.ini` (`testpaths = tests`, `pythonpath = src`).
- `tests/__init__.py` and `tests/test_import.py` smoke test.
- `.agent/STRUCTURE.md` documenting the planned `src/lumamatch/` module layout and `tests/`.
- **Environment note:** `.venv/` from TASK-1 was gone in this sandbox invocation (fresh container). Recreated it: `python3 -m venv .venv` failed on missing `ensurepip`, same as TASK-1's finding, so reinstalled `python3.14-venv` via apt, then recreated the venv and reinstalled all requirements successfully.
- Verified: `.venv/bin/pytest` → 1 passed; `.venv/bin/ruff check src tests` → all checks passed; `.venv/bin/ruff format --check src tests` → already formatted.
- Did not touch `src/package.json`, `src/node_modules`, `src/playwright.config.ts`, or `src/vitest.config.ts`. `.gitignore` already had `.venv/` and `__pycache__/` from TASK-1, no change needed.

## 2026-10-08 — TASK-1: Verify project prerequisites and access

Verified inside the sandbox, using the project venv. Results differ from what the PRD recorded on the host:
- **Python:** `Python 3.14.4 (main, Aug 20 2026, 10:41:58) [GCC 15.2.0]` (meets the >= 3.11 requirement). The system `python3` had no `ensurepip`, so I installed `python3.14-venv` via apt and created `.venv/`.
- **Imaging libraries (in `.venv`):** numpy 2.5.3, Pillow 12.3.0, pillow-heif 1.8.0 (libheif 1.23.4, x265 encoder, libde265 decoder). All three import cleanly. The system Python does not have them, so always use `.venv/bin/python`.
- **HEIC encode/decode:** I wrote a 32x32 RGB `.heic` in a temp dir and read it back (format HEIF, size (32, 32), pixel (200, 100, 50) preserved), then deleted the temp dir.
- **pip index:** `pip download pytest ruff` succeeded (pytest 9.1.1, ruff 0.16.10), so TASK-3 can install them.
- **Not applicable:** this project needs no database, no MCP servers, no third-party services or accounts, no login/test users, and no environment variables. No `.env.local` was created, and no secrets were written anywhere.
- **PROMPT.md Node/Playwright gap:** approved to proceed and resolved by TASK-2.
- **Reference docs:** pillow.readthedocs.io is reachable. pillow-heif.readthedocs.io, numpy.org, and brucelindbloom.com return 403 "Approval required" from the sandbox firewall. Pending approvals on the host (`sbx policy approval ls`). This does not block implementation, because the sRGB/D65/CIELab constants are standard.
- Added `.venv/` and `__pycache__/` to `.gitignore`.
- **Blocker:** the project directory is not a git repository, and the rules forbid `git init`, so this task could not be committed.

## 2026-10-08 — TASK-2 (done manually, outside the loop)

Rewrote `.agent/PROMPT.md` for a Python CLI workflow: venv setup replaces `npm run dev`; ruff + pytest replace eslint/prettier/tsc/Playwright; screenshot references removed. Help-tag wording changed from Playwright/dev-server examples to Python ones; tag formats and one-task rule unchanged. Also cleared `.agent/STEERING.md` (default web-app setup does not apply).

<!-- TODO: Add log entries here -->
