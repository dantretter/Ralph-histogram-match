"""Command-line argument parsing, reporting, and entry point.

`main(argv)` returns an exit code rather than calling `sys.exit`, so the CLI
is fully testable in-process. This is the tool's only UI: success is a
compact report on stdout, failure is a single-line `error: ...` on stderr
with no traceback.
"""

import argparse
import sys
from pathlib import Path

import lumamatch
from lumamatch.histogram import DEFAULT_BINS
from lumamatch.io_image import SUPPORTED_EXTENSIONS
from lumamatch.paths import CSV_SUFFIX, MATCHED_SUFFIX
from lumamatch.pipeline import match_luminance
from lumamatch.result import MatchResult

DEFAULT_QUALITY = 95
_LABEL_WIDTH = 11


def _positive_bins(value: str) -> int:
    """Argparse type for `--bins`: an integer >= 2."""
    try:
        bins = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer value: '{value}'") from exc
    if bins < 2:
        raise argparse.ArgumentTypeError(f"bins must be >= 2, got {bins}")
    return bins


def _quality(value: str) -> int:
    """Argparse type for `--quality`: an integer in [1, 100]."""
    try:
        quality = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid integer value: '{value}'") from exc
    if not (1 <= quality <= 100):
        raise argparse.ArgumentTypeError(f"quality must be between 1 and 100, got {quality}")
    return quality


def build_parser() -> argparse.ArgumentParser:
    """Build the `lumamatch` argument parser."""
    formats = ", ".join(sorted(SUPPORTED_EXTENSIONS))
    parser = argparse.ArgumentParser(
        prog="lumamatch",
        description=(
            "Match the target image's L* (lightness) histogram to the "
            "reference image's, via monotonic tone mapping."
        ),
        epilog=(
            f"Supported formats: {formats}. "
            f"Outputs are written beside the target image as "
            f"<name>{MATCHED_SUFFIX}<ext> and <name>{CSV_SUFFIX}.csv."
        ),
    )
    parser.add_argument(
        "reference",
        type=Path,
        help="reference: the image whose tonality is the target to match",
    )
    parser.add_argument(
        "target",
        type=Path,
        help="target: the image that will be modified",
    )
    parser.add_argument(
        "--bins",
        type=_positive_bins,
        default=DEFAULT_BINS,
        help=f"number of L* histogram bins (default: {DEFAULT_BINS})",
    )
    parser.add_argument(
        "--quality",
        type=_quality,
        default=DEFAULT_QUALITY,
        help=f"JPEG/HEIC save quality, 1-100 (default: {DEFAULT_QUALITY})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing outputs",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="suppress all non-error output",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=lumamatch.__version__,
    )
    return parser


def format_report(result: MatchResult) -> str:
    """Render `result` as the multi-line success report printed to stdout."""
    ref_h, ref_w = result.reference_shape
    tgt_h, tgt_w = result.target_shape

    def label(text: str) -> str:
        return f"{text:<{_LABEL_WIDTH}}"

    lines = [
        f"{label('reference:')}{result.reference_path.name} "
        f"({ref_w}x{ref_h}, {result.reference_pixels} px)",
        f"{label('target:')}{result.target_path.name} ({tgt_w}x{tgt_h}, {result.target_pixels} px)",
        f"{label('bins:')}{result.bins}",
        f"{label('EMD:')}{result.emd_before:.3f} -> {result.emd_after:.3f} L* "
        f"({result.emd_reduction * 100:.2f}% reduction)",
        f"{label('clipped:')}{result.clipped_fraction * 100:.2f}% of pixels",
        "",
        f"wrote {result.image_out}",
        f"wrote {result.csv_out}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, run the pipeline, and return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = match_luminance(
            reference_path=args.reference,
            target_path=args.target,
            bins=args.bins,
            force=args.force,
            quality=args.quality,
        )
    except (FileNotFoundError, ValueError, FileExistsError, PermissionError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"error: unexpected failure: {exc}", file=sys.stderr)
        return 1

    # --quiet suppresses the success report only; errors above always print.
    if not args.quiet:
        print(format_report(result))

    return 0
