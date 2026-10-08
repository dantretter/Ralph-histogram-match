"""End-to-end orchestration of one match operation.

Wires every component together: load both images, convert to Lab, histogram
both L* channels, build the monotonic LUT, apply it, recombine with
untouched a*/b*, convert back to sRGB, save, and measure the final histogram
from the quantized 8-bit result. No printing or logging happens here; all
user-facing text belongs to the CLI.
"""

from pathlib import Path

from lumamatch.color import lab_to_srgb, srgb_to_lab
from lumamatch.csv_writer import write_histogram_csv
from lumamatch.emd import emd
from lumamatch.histogram import bin_edges, l_histogram
from lumamatch.io_image import load_rgb, save_rgb
from lumamatch.paths import resolve_outputs
from lumamatch.result import MatchResult
from lumamatch.tonemap import apply_lut, build_lut


def match_luminance(
    reference_path: Path | str,
    target_path: Path | str,
    bins: int = 256,
    force: bool = False,
    quality: int = 95,
) -> MatchResult:
    """Match `target_path`'s L* distribution to `reference_path`'s.

    Args:
        reference_path: path to image 1, the distribution to match toward.
        target_path: path to image 2, the image that is modified.
        bins: number of uniform L* histogram bins over [0, 100].
        force: if True, bypass the overwrite guard on existing outputs.
        quality: JPEG/HEIC save quality, ignored for PNG.

    Returns:
        The `MatchResult` describing the operation; the matched image and
        histogram CSV have already been written at this point.
    """
    # Resolved and guarded before anything is decoded, so a rejected run
    # (existing outputs, no --force) has zero side effects.
    image_out, csv_out = resolve_outputs(target_path, force=force)

    reference_path = Path(reference_path)
    target_path = Path(target_path)

    ref_rgb = load_rgb(reference_path)
    tgt_rgb = load_rgb(target_path)
    reference_pixels = ref_rgb.shape[0] * ref_rgb.shape[1]
    target_pixels = tgt_rgb.shape[0] * tgt_rgb.shape[1]

    ref_lab = srgb_to_lab(ref_rgb)
    tgt_lab = srgb_to_lab(tgt_rgb)

    edges = bin_edges(bins)
    hist_ref, _ = l_histogram(ref_lab[..., 0], bins)
    hist_tgt, _ = l_histogram(tgt_lab[..., 0], bins)
    emd_before = emd(hist_tgt, hist_ref, edges)

    lut = build_lut(hist_tgt, hist_ref, edges)
    l_new = apply_lut(tgt_lab[..., 0], lut, edges)

    # Copy rather than mutate in place: keeps the original Lab array
    # available if callers ever need the pre-tone-map a*/b* for comparison.
    out_lab = tgt_lab.copy()
    out_lab[..., 0] = l_new

    out_rgb, clipped_fraction = lab_to_srgb(out_lab)
    save_rgb(image_out, out_rgb, quality=quality)

    # Measured from the in-memory uint8 result (the exact bytes handed to
    # the encoder), not a re-read of the saved file: re-reading a lossy
    # JPEG/HEIC would report codec damage rather than the tone mapping's
    # result, making PNG and JPEG runs inconsistent with each other.
    hist_matched, _ = l_histogram(srgb_to_lab(out_rgb)[..., 0], bins)
    emd_after = emd(hist_matched, hist_ref, edges)

    result = MatchResult(
        reference_path=reference_path,
        target_path=target_path,
        bins=bins,
        edges=edges,
        hist_reference=hist_ref,
        hist_target=hist_tgt,
        hist_target_matched=hist_matched,
        lut=lut,
        emd_before=emd_before,
        emd_after=emd_after,
        clipped_fraction=clipped_fraction,
        reference_pixels=reference_pixels,
        target_pixels=target_pixels,
        image_out=image_out,
        csv_out=csv_out,
    )

    write_histogram_csv(csv_out, result)

    return result
