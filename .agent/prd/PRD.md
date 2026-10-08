# PRD — `lumamatch`: CIELab Luminance Histogram Matching CLI

## 1. App Overview, Objectives, Success Criteria

**What it is.** A Python CLI that takes two RGB images and rewrites the second one so its L\* (CIELab lightness) histogram matches the first as closely as possible, using a strictly monotonic tone mapping. It writes the modified image plus a CSV of all three histograms next to image 2.

**Objectives.**
1. Produce the EMD-optimal *monotonic* L\* tone mapping from image 2 → image 1.
2. Preserve pixel ordering: if pixel A ≤ pixel B in original L\*, that holds in the output.
3. Leave a\*/b\* untouched — only lightness changes.
4. Emit auditable data (three histograms + EMD figures) so results can be plotted/verified.
5. Prove correctness with an automated round-trip test over random monotonic curves.

**Success criteria.**
- `lumamatch A B` writes `B_matched.<ext>` and `B_histograms.csv` beside `B`.
- Round-trip test: for ≥6 seeded random monotonic curves applied to a reference image, the pipeline recovers the reference with **EMD reduction ≥ 95%** and **mean |ΔL\*| < 1.0**.
- Tone mapping LUT is verified non-decreasing for every run.
- HEIC, JPG, and PNG all read and write successfully.
- `pytest` green; `ruff check` clean.

**Non-goals.**
- No GUI, no web UI, no batch/directory mode.
- No a\*/b\* (chroma/hue) matching. No color-cast correction.
- No ICC profile parsing or non-sRGB working spaces.
- No HDR / >8-bit output, no video, no RAW.
- No spatially-varying (local) tone mapping.
- No accessibility or performance-optimization work (explicitly out of scope per user; images are handled with vectorized NumPy which is sufficient).

## 2. Target Audience

Imaging engineers and photo-quality analysts who need reproducible tone alignment between two captures of the same or similar scene — e.g. normalizing exposure before A/B image-quality comparison. Comfortable with a terminal, expect deterministic numeric output and CSV artifacts they can plot.

## 3. Core Features and Functional Requirements

### TASK-3 — Project scaffold and dependencies
Python package at `src/lumamatch/`, `requirements.txt` (numpy, pillow, pillow-heif, pytest, ruff), `ruff.toml`, `tests/` dir. Package importable as `lumamatch`.

### TASK-4 — sRGB → CIELab conversion (hand-rolled)
`color.py: srgb_to_lab(rgb_u8) -> lab_f64`. 8-bit sRGB → [0,1] → inverse sRGB EOTF (linear segment below 0.04045, else `((c+0.055)/1.055)**2.4`) → linear RGB → XYZ via sRGB/D65 matrix → normalize by D65 white (Xn=0.95047, Yn=1.0, Zn=1.08883) → Lab with `f(t) = t**(1/3)` for `t > (6/29)**3`, else `t*(29/6)**2/3 + 4/29`. Output `L* ∈ [0,100]`, `a*`/`b*` ≈ ±128. Vectorized, float64.

### TASK-5 — CIELab → sRGB conversion (hand-rolled) + gamut clipping
`color.py: lab_to_srgb(lab_f64) -> (rgb_u8, clipped_fraction)`. Exact inverse of TASK-3. After linear→sRGB gamma, clip to [0,1], report fraction of *pixels* with any channel clipped. Round-half-away-from-zero to uint8.

### TASK-6 — Round-trip conversion accuracy and reference anchors
`srgb_to_lab` → `lab_to_srgb` on all 256³-sampled and random RGB values must return the identical uint8 values (max abs diff 0). Lab values for known anchors verified: pure black → L\*=0, pure white → L\*=100 (±1e-6), mid grey 128 → L\* ≈ 53.585.

### TASK-7 / TASK-8 — Image loading and saving
`io_image.py: load_rgb(path) -> np.uint8 (H,W,3)` supporting `.heic/.heif/.jpg/.jpeg/.png`. Register `pillow_heif.register_heif_opener()`. Convert palette/grayscale/RGBA → RGB (drop alpha). `save_rgb(path, rgb_u8, quality)` writes the same format as the source extension. Unsupported extension → clear `ValueError`.

### TASK-9 — L\* histogram computation
`histogram.py: l_histogram(l_star, bins=256) -> (counts_int64, edges)`. Uniform bins over `[0, 100]`. Values exactly 100 land in the last bin. Counts sum to pixel count. Fixed edges regardless of image content so two histograms are always directly comparable.

### TASK-10 — Earth Mover's Distance between two histograms
`emd.py: emd(h1, h2, edges) -> float`. 1-D Wasserstein-1: normalize both to PMFs, `sum(|CDF1 - CDF2|) * bin_width`. Units are L\*. Zero-total histogram → `ValueError`.

### TASK-11 — Monotonic tone mapping via CDF-based histogram specification
`tonemap.py: build_lut(src_hist, ref_hist, edges) -> lut (float64, len == bins)`. Compute source and reference normalized CDFs; for each source bin `i`, find the L\* value where `ref_CDF` reaches `src_CDF[i]` using linear interpolation on the reference CDF (`np.interp` against monotone CDF). This is the EMD-optimal monotone transport in 1-D. Enforce non-decreasing output via `np.maximum.accumulate` and clip to `[0,100]`.

### TASK-12 — Apply LUT to L\* with interpolation
`tonemap.py: apply_lut(l_star, lut, edges) -> l_new`. `np.interp` with x = bin centers, y = lut, so per-pixel output is continuous, not quantized to bin centers. Endpoints extrapolate as clamped. Result monotonic in input and clipped to `[0,100]`.

### TASK-16 — Pipeline orchestration (with TASK-13 MatchResult data model)
`pipeline.py: match_luminance(ref_path, target_path, bins, ...) -> MatchResult` dataclass carrying: three histograms, edges, lut, `emd_before`, `emd_after`, `clipped_fraction`, output paths. Sequence: load both → to Lab → histograms → build LUT → apply to target L\* → recombine with untouched a\*/b\* → to sRGB → third histogram computed from the **final quantized uint8 result** (not the float intermediate), so the CSV reflects what was actually saved.

### TASK-15 — CSV writer
`csv_writer.py: write_histogram_csv(path, result)`. Metadata comment lines first (`# image1=`, `# image2=`, `# image1_pixels=`, `# image2_pixels=`, `# bins=`, `# emd_before=`, `# emd_after=`, `# clipped_fraction=`), then header
`bin_index,l_star_lower,l_star_center,l_star_upper,image1_count,image2_count,image2_matched_count`
and one row per bin. Raw integer pixel counts. Uses `csv` module, `newline=""`.

### TASK-14 — Output path resolution and overwrite guard
`paths.py: resolve_outputs(target_path, force) -> (image_out, csv_out)`. Defaults: `<stem>_matched<ext>` and `<stem>_histograms.csv`, both in the **target image's** directory. If either exists and `force` is False → `FileExistsError` with a message naming the file and suggesting `--force`. Nothing is written unless both paths are clear.

### TASK-17 / TASK-18 — CLI parsing, reporting, and error handling
`cli.py` + `__main__.py`. `lumamatch REFERENCE TARGET [--bins N] [--force] [--quiet]`. Prints: input sizes, bins, EMD before → after, % EMD reduction, clipped-pixel %, and both output paths. Exit 0 on success; exit 2 with a one-line human error (no traceback) on bad path / unsupported format / existing output. `--bins` must be ≥ 2.

### TASK-19 — Random monotonic tone-curve generator (test fixture)
`tests/curves.py: random_monotonic_curve(rng, bins) -> lut`. Sample `bins` positive increments from `rng.uniform(0.05, 1.0)`, cumulative-sum, rescale to span `[0,100]` (with a random offset/compression so not every curve is full-range). Strict monotonicity asserted.

### TASK-20 — Synthetic reference image generator (test fixture)
`tests/images.py: synthetic_reference(rng, size) -> rgb_u8` producing an image with a wide, non-degenerate L\* distribution and real chroma: smooth gradients + colored patches + mild noise. Must not be uniform (histogram spread over most bins).

### TASK-21 — Round-trip matching test (the core correctness gate)
For 6 seeds: build reference → distort via random monotonic L\* curve → save both as PNG in tmp_path → run pipeline → assert `emd_after <= 0.05 * emd_before` **and** `mean(|L_matched - L_ref|) < 1.0`. Also assert the recovered LUT is non-decreasing and output image dimensions match input.

### TASK-22 — Format coverage test
Same match run for `.png`, `.jpg`, `.heic` targets: output file exists, is readable, has the source format, and matches input dimensions. JPEG tolerance loosened for compression.

### TASK-23 — CLI end-to-end test
Invoke via `subprocess` (`python -m lumamatch`): exit 0, both output files created, CSV parses with the expected header and `bins` data rows, counts per column sum to the respective pixel counts. Re-run without `--force` → exit 2 and message mentions `--force`; with `--force` → exit 0.

### TASK-24 — Edge case handling
Explicit, tested behavior for: single-color (degenerate) target image; images of different dimensions (allowed — matching is histogram-only); 1×1 image; grayscale input; RGBA PNG input; `--bins 2`.

### TASK-25 — Harden untrusted image input handling
Keep Pillow's decompression-bomb guard at its default, normalize every decoder failure to `ValueError`, confirm outputs stay inside the target's directory, confirm source EXIF/GPS/ICC never reaches the output, and confirm the tool performs zero network I/O.

### TASK-26 — README / usage documentation
`src/lumamatch/README.md`: install, usage, worked example, CSV column reference, algorithm explanation (why CDF matching is EMD-optimal for monotone maps), known limits (gamut clipping, information loss on flat curve regions).

### TASK-2 — Update `.agent/PROMPT.md` for Python
Replace Node dev-server / Playwright / screenshot steps with venv creation, `pip install -r requirements.txt`, `pytest`, `ruff check --fix`, `ruff format`. Keep one-task-per-invocation loop, promise tags, and logging behavior unchanged.

## 4. Key User Flows

**Primary flow — match two images**
1. User runs `lumamatch reference.heic subject.jpg`.
2. Tool loads both, reports dimensions and bin count.
3. Tool prints `EMD 8.412 → 0.117 L* (98.6% reduction)`, `clipped pixels: 0.02%`.
4. Tool writes `subject_matched.jpg` and `subject_histograms.csv` next to `subject.jpg`, printing both paths.
5. User opens the CSV and plots the three columns to confirm the match visually.

**Error flow — outputs already exist**
1. User re-runs the same command.
2. Tool exits 2 before writing anything: `error: subject_matched.jpg already exists (use --force to overwrite)`.

**Verification flow — developer**
1. `pytest` → round-trip suite generates 6 random monotonic curves, distorts a synthetic reference, and asserts recovery within tolerance.
2. Failure output names the seed so the case is reproducible.

## 5. Technical Stack

| Concern | Choice | Rationale |
|---|---|---|
| Language | Python 3.13 (verified present) | Already installed |
| Arrays | NumPy 2.4.4 | Vectorized Lab math + histograms |
| JPG/PNG I/O | Pillow 12.2.0 | Standard |
| HEIC I/O | pillow-heif 1.3.0 | Read **and write** verified working in this environment |
| Color math | Hand-rolled sRGB↔Lab (user choice) | No scikit-image dependency; math is ~40 lines and fully unit-testable |
| Tone mapping | CDF-based histogram specification | Provably EMD-optimal monotone transport in 1-D; exact and instant |
| Test | pytest | Seeded, headless, CI-friendly |
| Lint/format | ruff | Single tool for both |
| Deps | `pip` + `venv` + `requirements.txt` | Minimal, portable |

**Why CDF matching is the right algorithm.** For 1-D distributions, the optimal transport map under any convex cost — including the Wasserstein-1/EMD cost — is the monotone rearrangement `T = F_ref⁻¹ ∘ F_src`. So the classic histogram-specification LUT *is* the EMD minimizer over the class of monotonic maps; no search or optimizer is needed. EMD is still computed explicitly, but as a **reported metric and test gate**, not as an objective to iterate on. The greedy dark→light approach sketched in the original requirements is a discrete approximation of exactly this; the CDF form is the exact version.

## 6. Prerequisites and Access

| Prerequisite | Status |
|---|---|
| Database access | **Not applicable** — no database in this project |
| Required MCP servers | **None** — no external services; pure local computation |
| Third-party service accounts / API keys | **None** |
| Environment variables | **None required.** No `.env.local` was created because zero environment variables were discovered. No secrets, tokens, connection strings, or credentials are involved anywhere in this project |
| Login / test users | **Not applicable** — CLI tool, no auth, no users |
| Python 3.13.12 | ✅ verified (`conda-forge`, `/opt/homebrew/Caskroom/miniforge/base`) |
| NumPy 2.4.4, Pillow 12.2.0, pillow-heif 1.3.0 | ✅ verified importable |
| HEIC read **and** write | ✅ verified — test HEIC written and re-read successfully |
| pip network access | ✅ verified — `pip download pytest` succeeded, so `pytest`/`ruff` are installable |
| pytest, ruff | ❌ not yet installed — installed in TASK-2 via `requirements.txt` |
| Service documentation links | Pillow: https://pillow.readthedocs.io/ · pillow-heif: https://pillow-heif.readthedocs.io/ · NumPy: https://numpy.org/doc/stable/ · CIELab/sRGB reference: http://www.brucelindbloom.com/ |

**Open prerequisite gaps and decisions.**
1. *`.agent/PROMPT.md` assumes a Node/Next.js project* (`npm run dev` on :3000, Playwright smoke tests, UI screenshots) — invalid for a Python CLI and would stall or waste Ralph loop iterations. **User decision: PROCEED, with PROMPT.md rewritten for Python** — captured as TASK-2, which is done immediately after TASK-1.
2. *No `.env.local`* — intentional, not a gap. Nothing in this project consumes environment variables. TASK-1 records this rather than creating an empty placeholder file.
3. *`src/` contains a Node/Vitest scaffold* (`package.json`, `node_modules`, `playwright.config.ts`). **Decision: leave it in place, untouched.** The Python package lives beside it at `src/lumamatch/`; the two do not interact.

## 7. Conceptual Data Model

No persistence layer. In-memory structures only.

```
RgbImage        : np.ndarray  uint8   (H, W, 3), sRGB
LabImage        : np.ndarray  float64 (H, W, 3), L*∈[0,100], a*,b*∈≈[-128,128]
Histogram       : np.ndarray  int64   (bins,)  raw pixel counts
BinEdges        : np.ndarray  float64 (bins+1,) uniform over [0,100]
ToneLut         : np.ndarray  float64 (bins,)  non-decreasing, ∈[0,100]

MatchResult (dataclass, frozen)
  reference_path       : Path
  target_path          : Path
  bins                 : int
  edges                : BinEdges
  hist_reference       : Histogram
  hist_target          : Histogram
  hist_target_matched  : Histogram   # from final uint8 output
  lut                  : ToneLut
  emd_before           : float       # L* units
  emd_after            : float
  clipped_fraction     : float       # 0..1
  reference_pixels     : int
  target_pixels        : int
  image_out            : Path
  csv_out              : Path
```

**CSV schema** (`<target_stem>_histograms.csv`): 8 metadata comment lines, then
`bin_index:int, l_star_lower:float, l_star_center:float, l_star_upper:float, image1_count:int, image2_count:int, image2_matched_count:int` — exactly `bins` data rows.

## 8. UI Design Principles

Terminal output only; no graphical UI, so no wireframes and no accessibility work in scope (per user).

- One line per fact; no progress bars or spinners.
- Numbers carry units (`L*`, `%`) and fixed precision (3 decimals for EMD, 2 for percentages).
- Errors go to stderr, single line, no traceback, actionable (`use --force to overwrite`).
- `--quiet` suppresses everything but errors, so the tool composes in scripts.
- Output paths are always printed last and in full, so they can be copied.

## 9. Security Considerations

- **No secrets anywhere.** No credentials, keys, tokens, or env vars exist in this project. Nothing to leak.
- **No network I/O at runtime.** The tool only touches local files.
- **Path safety.** Output paths derive from the resolved target path; the overwrite guard prevents silent destruction of prior results or, via the `_matched` suffix, of the user's original photos. The tool never writes outside the target image's directory.
- **Untrusted image input.** Decoding attacker-supplied HEIC/JPG/PNG is the main attack surface (decoder CVEs). Mitigation: keep Pillow and pillow-heif current; Pillow's decompression-bomb guard stays enabled (do not raise `Image.MAX_IMAGE_PIXELS`).
- **Metadata.** EXIF/GPS is *not* copied to the output by default; the modified image is stripped of source metadata. Noted in the README as a deliberate privacy-safe default.

## 10. Development Phases

| Phase | Tasks | Outcome |
|---|---|---|
| 0 — Gate | TASK-1, TASK-2 | Prereqs confirmed; Ralph loop configured for Python |
| 1 — Foundations | TASK-3 → TASK-8 | Package installs; Lab math round-trips exactly; all 3 formats load/save |
| 2 — Core math | TASK-9 → TASK-12 | Histograms, EMD, monotonic LUT, interpolated application |
| 3 — Product | TASK-13 → TASK-18 | Pipeline, CSV, overwrite guard, CLI |
| 4 — Proof | TASK-19 → TASK-25 | Random-curve round-trip suite, format coverage, CLI e2e, edge cases |
| 5 — Docs | TASK-26 | README with algorithm rationale and CSV reference |

## 11. Assumptions and Dependencies

**Assumptions.**
1. Inputs are 8-bit sRGB with a D65 white point; no ICC profile is read or honored.
2. Only L\* is modified; a\*/b\* pass through unchanged, so hue/chroma are preserved but perceived saturation may shift where L\* changes a lot.
3. Images need not be the same scene or the same dimensions — matching is purely distributional.
4. A monotonic mapping is a hard constraint, so an exact histogram match is generally impossible; EMD near zero is the goal, not zero.
5. Information destroyed by a near-flat region of the original curve is unrecoverable; those test cases will show larger residual error, which is expected and why tolerance is relative (≥95% EMD reduction) rather than absolute.
6. Round-half-away-from-zero uint8 quantization contributes ≈0.2 L\* of unavoidable noise — well inside the 1.0 tolerance.
7. Images fit comfortably in RAM as float64 (≈24 bytes/pixel); no tiling. A 50 MP image needs ~1.2 GB, acceptable for the target user.
8. HEIC output uses pillow-heif's default encoder settings; no HDR/10-bit path.

**Dependencies.**
- Runtime: `numpy`, `pillow`, `pillow-heif`.
- Dev: `pytest`, `ruff`.
- Environment: Python ≥ 3.11 (targeting the installed 3.13.12); libheif via the pillow-heif wheel.
- Process: `.agent/PROMPT.md` must be updated (TASK-2) before Ralph loop iterations run cleanly.
