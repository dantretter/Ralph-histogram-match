# Project Build Log

`Current Status`
=================
**Last Updated:** 2026-10-08
**Tasks Completed:** 5 / 26
**Current Task:** TASK-5 Complete

----------------------------------------------

## Session Log

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
