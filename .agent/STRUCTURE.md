# Project Structure

## `src/lumamatch/` — the `lumamatch` package

| File | Status | Purpose |
| --- | --- | --- |
| `__init__.py` | created | Package version (`__version__`). |
| `color.py` | created | sRGB ↔ CIELab conversion: `srgb_to_lab`, `lab_l_channel`, `lab_to_srgb` (with gamut clip reporting). |
| `io_image.py` | created | `load_rgb` and `save_rgb` for HEIC, JPG, PNG; `save_rgb` strips EXIF/ICC metadata. |
| `histogram.py` | created | Fixed-domain 256-bin L* histogram: `l_histogram`, `bin_edges`, `bin_centers`, `bin_width`, `to_pmf`. |
| `emd.py` | created | 1-D Earth Mover's Distance between histograms: `emd`, `emd_reduction`. |
| `tonemap.py` | created | Monotonic tone LUT via CDF histogram specification: `build_lut`, `apply_lut`, `assert_monotonic`. |
| `result.py` | created | `MatchResult` frozen dataclass: hand-off object between pipeline, CSV writer, and CLI reporter; validates shapes/sums (including `reference_shape`/`target_shape` against pixel counts) and freezes arrays read-only. |
| `paths.py` | created | `resolve_outputs`: derives `<stem>_matched<suffix>` and `<stem>_histograms.csv` beside the target image; all-or-nothing overwrite guard. |
| `pipeline.py` | created | `match_luminance` end-to-end orchestration: load, convert, histogram, LUT, apply, save, re-measure, write CSV. |
| `csv_writer.py` | created | `write_histogram_csv`/`read_histogram_csv`: commented 3-histogram CSV artifact. |
| `cli.py` | created | `build_parser`, `format_report`, `main(argv) -> int`: argument parsing, the stdout success report, and single-line stderr error handling with a 2/1 exit-code contract. |
| `__main__.py` | created | `python -m lumamatch` entry point; three-line `sys.exit(main())` shim. |

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
| `test_tonemap_apply.py` | created | `apply_lut` shape/dtype, range, monotonicity, equal-input equality, end clamping, anti-banding gradient check, identity-LUT tolerance, `ValueError` on mismatched lengths. |
| `test_result.py` | created | `MatchResult` valid construction, `emd_reduction` property, length/range/sum validation errors, read-only array enforcement. |
| `test_paths.py` | created | `resolve_outputs` naming, suffix-case preservation, all-or-nothing overwrite guard (image/csv/both), force bypass, missing-parent and read-only-parent errors. |
| `test_csv_writer.py` | created | `write_histogram_csv` comment-block/header structure, column sums against `MatchResult` totals, metadata round-trip, numeric formatting (no decimals/scientific notation in counts, full L* domain span). |
| `test_pipeline.py` | created | `match_luminance` integration: EMD reduction on a synthetic pair, both outputs written, output dimensions match target, a*/b* approximately preserved, overwrite guard (zero side effects) and `force=True` bypass. |
| `test_cli_args.py` | created | `build_parser` defaults, `--bins`/`--quality` validation (`SystemExit` code 2), missing positionals, `--force`/`--quiet` flags; `main()` real run returns 0 and writes both outputs. |
| `test_cli_report.py` | created | `format_report`/`main()` success report content and EMD formatting; error path for every exception class (`FileNotFoundError`, unsupported extension, corrupt file, `FileExistsError` mentioning `--force`, unexpected exception); `--quiet` suppresses success output but not errors. |
| `curves.py` | created | Test helper (not a test module itself): `random_monotonic_curve`, `apply_curve_to_image` — manufactures "image 2" by distorting a reference image's L* with a seeded, strictly-monotonic random curve. |
| `test_curves.py` | created | Self-test for `curves.py`: monotonicity/range over 20 seeds, determinism, seed-to-seed variation, `apply_curve_to_image` shape/dtype and a*/b* preservation. |

Further test modules (synthetic reference image fixture, I/O format coverage, CLI
end-to-end) will be added alongside their corresponding implementation tasks.
