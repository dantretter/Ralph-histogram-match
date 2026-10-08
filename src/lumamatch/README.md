# lumamatch

Match one image's tonality to another's: given a **reference** image and a **target**
image, `lumamatch` computes the monotonic tone curve that makes the target's L*
(lightness) histogram match the reference's as closely as possible, and writes the
result beside the target.

## One-time setup (Mac)

1. Install Python 3.14 with Homebrew (skip if `python3.14 --version` already works):

   ```bash
   brew install python@3.14
   ```

2. Create the project's Python environment and install its libraries:

   ```bash
   cd ~/Code/ralph-histogram-match
   python3.14 -m venv .venv-mac
   .venv-mac/bin/pip install -r requirements.txt
   ```

## Running it

Use the `lumamatch` launcher in the repo's top folder. It works from any folder:

```bash
~/Code/ralph-histogram-match/lumamatch reference.jpg photo.jpg
```

- **First image (reference):** the look you want to copy. It is never changed.
- **Second image (target):** the image to adjust. It is never overwritten. Two new files
  appear next to it:
  - `photo_matched.jpg`: the adjusted image (same format as the target)
  - `photo_histograms.csv`: the three L* histograms
- JPG, PNG and HEIC all work.
- **Tip:** type the command up to where an image path goes, then drag the image from
  Finder into the Terminal window to paste its full path.
- Running the same command again stops with "already exists" so earlier results aren't
  overwritten. Add `--force` to overwrite them.

**Shorter command (optional):** add an alias so you can type just `lumamatch`:

```bash
echo 'alias lumamatch=~/Code/ralph-histogram-match/lumamatch' >> ~/.zshrc
```

Open a new Terminal window, then run `lumamatch reference.jpg photo.jpg`.

### Options

Add these after the two image paths:

| Flag | Default | Meaning |
| --- | --- | --- |
| `--bins N` | `256` | Number of uniform L* histogram bins over the fixed `[0, 100]` domain. Must be `>= 2`. |
| `--quality N` | `95` | JPEG/HEIC save quality, `1`-`100`. Ignored for PNG (lossless). |
| `--force` | off | Overwrite existing output files instead of refusing to run. |
| `--quiet` | off | Suppress the success report on stdout. Errors still print to stderr. |
| `--version` | — | Print the installed version and exit. |

## Worked example

Real output from an actual run (synthetic reference image + a seeded random monotonic
distortion used as the subject — see `tests/images.py` and `tests/curves.py`):

```
$ lumamatch reference.png subject.png
reference: reference.png (192x128, 24576 px)
target:    subject.png (192x128, 24576 px)
bins:      256
EMD:       6.966 -> 0.258 L* (96.30% reduction)
clipped:   4.36% of pixels

wrote subject_matched.png
wrote subject_histograms.csv
```

Resulting directory listing:

```
reference.png
subject.png
subject_histograms.csv
subject_matched.png
```

Re-running the identical command without `--force` writes nothing and exits 2:

```
$ lumamatch reference.png subject.png
error: subject_matched.png already exists (use --force to overwrite)
```

## Outputs

Both outputs are written beside the **target** image, named from its stem:

- `<stem>_matched<ext>` — the target image with its L* channel tone-mapped. Same format
  as the target (extension-driven).
- `<stem>_histograms.csv` — the reference, original-target, and matched-target L*
  histograms, one row per bin.

## CSV reference

The file starts with a `# key=value` metadata comment block, then a standard header row
and one data row per bin. Load it with `pandas.read_csv(path, comment="#")` to skip the
metadata block automatically.

### Metadata keys

| Key | Meaning |
| --- | --- |
| `image1` | Path to the reference image as given on the command line. |
| `image2` | Path to the target image as given on the command line. |
| `image1_pixels` | Total pixel count of the reference image (= sum of `image1_count`). |
| `image2_pixels` | Total pixel count of the target image (= sum of `image2_count` and of `image2_matched_count`). |
| `bins` | Number of histogram bins used (matches `--bins`). |
| `emd_before` | Earth Mover's Distance, in L* units, between the original target and reference histograms. |
| `emd_after` | Earth Mover's Distance, in L* units, between the matched target and reference histograms. |
| `clipped_fraction` | Fraction (0-1) of output pixels that had to be clipped back into the sRGB gamut. |

### Columns

| Column | Units | Meaning |
| --- | --- | --- |
| `bin_index` | — | Zero-based bin index, `0` to `bins - 1`. |
| `l_star_lower` | L* | Lower edge of the bin. |
| `l_star_center` | L* | Midpoint of the bin. |
| `l_star_upper` | L* | Upper edge of the bin. |
| `image1_count` | pixels | Raw reference histogram count in this bin. |
| `image2_count` | pixels | Raw original-target histogram count in this bin. |
| `image2_matched_count` | pixels | Raw matched-target histogram count in this bin, measured from the final saved 8-bit image. |

Counts are **raw pixel counts, not normalized**. Use the `*_pixels` metadata totals to
normalize into a PMF if you need one.

Two-line pandas snippet to load and plot all three histograms:

```python
import pandas as pd

df = pd.read_csv("subject_histograms.csv", comment="#")
df.plot(x="l_star_center", y=["image1_count", "image2_count", "image2_matched_count"])
```

## Algorithm

1. Convert both images from sRGB to CIELab (D65 white point), full float64 precision.
2. Histogram each image's L* channel into `--bins` uniform bins over the **fixed**
   `[0, 100]` domain, so reference and target histograms always share identical edges
   and are directly comparable.
3. Compute both histograms' CDFs, `F_ref` and `F_src`.
4. Build the tone curve `T = F_ref^-1 . F_src`: for every source L* value, look up its
   CDF value under the target's own distribution, then invert the reference's CDF to
   find the L* value that would produce that same cumulative probability under the
   reference distribution.
5. Apply `T` to the target's L* channel only (a*/b* pass through untouched), via linear
   interpolation between bin centers so the result has no banding.
6. Convert back to sRGB, clipping any out-of-gamut pixels and tracking the clipped
   fraction.

This is classic **CDF-based histogram specification**, and it matters that it is
*exactly* this, not an approximation of it: in one dimension, the monotone rearrangement
`T = F_ref^-1 . F_src` is the optimal transport map under *any* convex cost, which
includes the Wasserstein-1 cost that Earth Mover's Distance measures here. That means
this closed-form map **is** the EMD minimizer over all monotonic maps between the two
distributions — not a heuristic that approximates it, and not something a search or
iterative optimizer could improve on. No gradient descent, no greedy bin-walk, no
iteration is involved or needed.

EMD is still computed and reported (`emd_before`/`emd_after` in the CLI report and CSV),
but only as a **metric and test gate** — proof that the known-optimal map was actually
applied correctly — not as an objective being searched over. A future contributor who
sees "histogram matching" and reaches for an iterative or search-based "improvement"
would be solving an already-solved problem, and very likely introduce an inexact result
in the process.

## Limitations

- **Gamut clipping.** Changing L* while holding a*/b* fixed can push a color outside the
  sRGB gamut. Those pixels are clipped back into range; the fraction affected is reported
  (`clipped` in the CLI output, `clipped_fraction` in the CSV) rather than silently
  absorbed.
- **Information loss under compressive curves.** If the original distortion compressed a
  tonal range (e.g. crushed shadows into a narrow band), the distinct L* values in that
  range are genuinely gone from the 8-bit source and cannot be recovered by any tone
  curve, including the optimal one.
- **Monotonicity prevents an exact match.** The non-decreasing constraint is a hard
  guarantee (pixel ordering is never reversed), but it also means an exact histogram
  match is generally impossible by design whenever the target's bin populations don't
  already admit a monotonic rearrangement onto the reference's. The EMD after matching is
  typically small but nonzero.
- **Only lightness is matched.** a*/b* (color/chroma) are passed through unmodified, so a
  color cast or saturation difference between the two images is not corrected.
- **sRGB/D65 assumed, no ICC handling.** Input pixels are assumed to already be sRGB
  under a D65 illuminant; embedded ICC profiles are ignored, not converted from.
- **Output metadata is stripped deliberately.** EXIF (including GPS) and ICC profiles
  from either input are not copied to the output — see Security below.
- **Alpha is dropped, not composited.** Images with an alpha channel are flattened to RGB
  on load; transparency is not preserved or blended against a background.
- **8-bit in, 8-bit out.** No HDR or higher-bit-depth support.

## Security

`lumamatch` is a local CLI with no server component, so its only real attack surface is
decoding untrusted image files. The following properties are enforced and covered by
`tests/test_security.py`:

- **No network I/O.** The tool never opens a socket; everything happens on local files.
- **No credentials or environment variables** are read or required.
- **Decompression-bomb guard active.** Pillow's `Image.MAX_IMAGE_PIXELS` limit is never
  raised or disabled. A bomb warning/error is converted into a clean `ValueError` rather
  than a crash or an unbounded allocation.
- **Malformed input fails cleanly.** Corrupt or truncated HEIC/JPG/PNG files raise
  `ValueError` naming the offending path, never a raw PIL exception or a crash.
- **Source metadata is not copied.** EXIF (including GPS) and ICC profiles from either
  input are stripped; only pixel data crosses into the output file.
- **Output is confined to the target's directory.** Outputs are always named
  `<stem>_matched<ext>` / `<stem>_histograms.csv` beside the target image; there is no
  user-supplied output path to redirect elsewhere.

The real residual risk is a decoder CVE (libheif/libjpeg/libpng), which no amount of
application code can mitigate — keep Pillow and `pillow-heif` updated.

## Testing

From the repo root (use `.venv/bin/pytest` inside the Ralph sandbox):

```bash
.venv-mac/bin/pytest
```

The primary correctness gate is `tests/test_roundtrip.py`: it builds a synthetic
reference image, distorts it with 6 **seeded** random strictly-monotonic L* curves to
manufacture a target image, runs the full pipeline, and asserts:

- At least 95% EMD reduction between the pre- and post-match histograms.
- Mean `|ΔL*| < 1.0` between the recovered target and the true reference.
- The LUT stays non-decreasing.

The seeds are fixed, so a failure is always reproducible rather than a flaky one-off.
`tests/test_formats.py` and `tests/test_cli_e2e.py` extend this with format-pair
coverage (HEIC/JPG/PNG) and a real subprocess invocation of `python -m lumamatch`.
