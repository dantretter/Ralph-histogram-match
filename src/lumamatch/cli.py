"""Command-line argument parsing and entry point.

`main(argv)` returns an exit code rather than calling `sys.exit`, so the CLI
is fully testable in-process. Human-readable reporting and error formatting
are implemented in TASK-18; this module only handles parsing, validation,
and the exit-code contract.
"""

import argparse
from pathlib import Path

import lumamatch
from lumamatch.histogram import DEFAULT_BINS
from lumamatch.io_image import SUPPORTED_EXTENSIONS
from lumamatch.paths import CSV_SUFFIX, MATCHED_SUFFIX
from lumamatch.pipeline import match_luminance

DEFAULT_QUALITY = 95


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


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, run the pipeline, and return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        match_luminance(
            reference_path=args.reference,
            target_path=args.target,
            bins=args.bins,
            force=args.force,
            quality=args.quality,
        )
    except Exception:
        return 2

    return 0
