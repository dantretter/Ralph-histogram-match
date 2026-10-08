# Project Structure

## `src/lumamatch/` — the `lumamatch` package

| File | Status | Purpose |
| --- | --- | --- |
| `__init__.py` | created | Package version (`__version__`). |
| `color.py` | partial | sRGB → CIELab conversion (`srgb_to_lab`, `lab_l_channel`); `lab_to_srgb` still planned. |
| `io_image.py` | planned | `load_rgb` / `save_rgb` for HEIC, JPG, PNG. |
| `histogram.py` | planned | Fixed-domain 256-bin L* histogram. |
| `emd.py` | planned | 1-D Earth Mover's Distance between histograms. |
| `tonemap.py` | planned | Monotonic tone LUT via CDF histogram specification, plus LUT application. |
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

Further test modules (color conversion anchors, histogram/EMD, tone mapping round-trip, I/O
format coverage, CLI end-to-end) will be added alongside their corresponding implementation
tasks.
