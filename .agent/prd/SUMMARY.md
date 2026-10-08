# Project Summary — `lumamatch`

## Overview

`lumamatch` is a Python command-line tool that makes one image's tonality match another's. Given two RGB images (HEIC, JPG, or PNG), it converts both to CIELab, computes their L\* (lightness) histograms, derives the **monotonic** tone curve that minimizes the Earth Mover's Distance between the second image's histogram and the first's, applies it to the second image, and writes the result plus a CSV of all three histograms beside the second image.

The tone curve is computed by CDF-based histogram specification — in one dimension this is provably the EMD-optimal monotone transport, so no search or optimizer is required. Monotonicity is a hard guarantee: if pixel A is darker than pixel B in the original, it is never lighter in the output.

## Main Features

- **Multi-format I/O** — reads and writes HEIC/HEIF, JPG, and PNG; output preserves the input format.
- **Hand-rolled sRGB ↔ CIELab conversion** — D65 white point, proper sRGB gamma, float64 throughout, bit-exact round-trip.
- **256-bin L\* histograms** over a fixed `[0, 100]` domain, so any two are directly comparable.
- **Monotonic tone mapping** via CDF matching, enforced non-decreasing, applied as an interpolated float LUT so the result has no banding.
- **Explicit EMD reporting** — 1-D Wasserstein-1 distance before and after, in L\* units, printed and stored in the CSV.
- **Gamut-aware output** — out-of-sRGB pixels are clipped and the clipped fraction is reported, never silently swallowed.
- **CSV artifact** — one row per bin with all three histograms as raw pixel counts, plus a metadata header, ready to plot.
- **Safe by default** — refuses to overwrite existing outputs without `--force`; a\*/b\* are never modified; source metadata is not copied.

## Key Flows

**Match two images**
`lumamatch reference.heic subject.jpg` → prints dimensions, `EMD 8.412 → 0.117 L* (98.6% reduction)`, clipped-pixel percentage → writes `subject_matched.jpg` and `subject_histograms.csv` beside `subject.jpg`.

**Guarded re-run**
Re-running the same command exits 2 *before writing anything*: `error: subject_matched.jpg already exists (use --force to overwrite)`.

**Automated verification**
`pytest` builds a synthetic reference image, distorts it with 6 seeded random monotonic L\* curves to manufacture "image 2", runs the full pipeline on each, and asserts the reference is recovered.

## Key Requirements

1. Support HEIC, JPG, and PNG for both read and write.
2. Convert to CIELab and compute 256-bin L\* histograms over `[0, 100]`.
3. Tone mapping must be strictly non-decreasing — pixel ordering is preserved.
4. Minimize Earth Mover's Distance between image 1's histogram and the modified image 2's.
5. Modify L\* only; a\*/b\* pass through untouched.
6. Save both outputs in the same folder as image 2, using `<stem>_matched<ext>` and `<stem>_histograms.csv`.
7. The third histogram in the CSV must be measured from the final saved 8-bit image, not a float intermediate.
8. Pass criterion: ≥95% EMD reduction and mean |ΔL\*| < 1.0 across ~6 random monotonic curves.
9. CLI-only; no GUI, no network access, no credentials or environment variables.
10. `pytest` green and `ruff check` clean before any task is considered done.
