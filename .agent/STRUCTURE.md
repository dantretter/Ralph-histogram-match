# Project Structure

## `src/lumamatch/` — the `lumamatch` package

| File | Status | Purpose |
| --- | --- | --- |
| `__init__.py` | created | Package version (`__version__`). |
| `color.py` | created | sRGB ↔ CIELab conversion: `srgb_to_lab`, `lab_l_channel`, `lab_to_srgb` (with gamut clip reporting). |
| `io_image.py` | created | `load_rgb` and `save_rgb` for HEIC, JPG, PNG; `save_rgb` strips EXIF/ICC metadata. |
| `histogram.py` | created | Fixed-domain 256-bin L* histogram: `l_histogram`, `bin_edges`, `bin_centers`, `bin_width`, `to_pmf`. |
| `emd.py` | created | 1-D Earth Mover's Distance between histograms: `emd`, `emd_reduction`. |
| `tonemap.py` | created | Monotonic tone LUT via CDF histogram specification: `build_lut`, `assert_monotonic`. LUT application is TASK-12. |
| `pipeline.py` | planned | `match_luminance` end-to-end orchestration. |
| `csv_writer.py` | planned | Histogram CSV writer. |
| `paths.py` | planned | Output path resolution and overwrite guard. |
| `cli.py` | planned | Argument parsing, entry point, reporting/error handling. |
| `__main__.py` | planned | `python -m lumamatch` entry point. |

Note: `src/` also contains an unrelated Node/Playwright scaffold (`package.json`,
`package-lock.json`, `playwright.config.ts`, `vitest.config.ts`) that predates this project and
must not be modified.

## `tests/`

| File | Status | Purpose |
| --- | --- | --- |
| `__init__.py` | created | Makes `tests` a package. |
| `test_import.py` | created | Smoke test: `lumamatch` imports and exposes `__version__`. |
| `test_color_forward.py` | created | `srgb_to_lab`/`lab_l_channel` anchors, range, dtype/shape, and `ValueError` cases. |
| `test_color_inverse.py` | created | `lab_to_srgb` byte-exact round-trip (greys + random), gamut clipping report, `ValueError` cases. |
| `test_color_reference.py` | created | External Lab anchor checks (black/white/grey/red/green/blue), strided RGB-cube round-trip, grey L* monotonicity, a*/b* invariance under L* replacement. |
| `test_io_load.py` | created | `load_rgb` mode coverage (RGB/L/RGBA/P across PNG/JPG/HEIC), alpha drop, unsupported extension, missing file, corrupt file. |
| `test_io_save.py` | created | `save_rgb` PNG exactness, JPEG/HEIC readability, EXIF stripping, unsupported extension, missing directory, bad dtype/shape. |
| `test_histogram.py` | created | `l_histogram` fixed-domain binning, clipping, edges/dtype, `ValueError` cases, `bin_centers`/`bin_width`/`to_pmf`. |
| `test_emd.py` | created | `emd` known-distance, identity, symmetry, scale invariance, `ValueError` cases; `emd_reduction` typical/zero/regression cases. |
| `test_tonemap_lut.py` | created | `build_lut` identity case, monotonicity/finiteness over 50 seeded random histogram pairs, range bounds, degenerate source/reference spikes, `ValueError` cases, `assert_monotonic` direct checks. |

Further test modules (tone mapping round-trip, I/O format coverage, CLI
end-to-end) will be added alongside their corresponding implementation tasks.
