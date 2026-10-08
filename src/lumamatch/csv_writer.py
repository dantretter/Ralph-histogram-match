"""Histogram CSV writer.

The CSV is the tool's auditable artifact: a `# key=value` metadata comment
block records what was run and what the EMD figures were, followed by one
row per bin giving its L* range and the three raw pixel counts. Raw counts
(not normalized) are lossless; the metadata block carries the totals so
downstream normalization is always possible.
"""

import csv
from pathlib import Path

from lumamatch.histogram import bin_centers
from lumamatch.result import MatchResult

CSV_HEADER = [
    "bin_index",
    "l_star_lower",
    "l_star_center",
    "l_star_upper",
    "image1_count",
    "image2_count",
    "image2_matched_count",
]


def write_histogram_csv(path: Path | str, result: MatchResult) -> None:
    """Write `result`'s three histograms to `path` as a commented CSV.

    Args:
        path: destination file path.
        result: the match result to serialize.
    """
    lowers = result.edges[:-1]
    uppers = result.edges[1:]
    centers = bin_centers(result.edges)

    with open(path, "w", newline="", encoding="utf-8") as fh:
        fh.write(f"# image1={result.reference_path}\n")
        fh.write(f"# image2={result.target_path}\n")
        fh.write(f"# image1_pixels={result.reference_pixels}\n")
        fh.write(f"# image2_pixels={result.target_pixels}\n")
        fh.write(f"# bins={result.bins}\n")
        fh.write(f"# emd_before={result.emd_before:.6f}\n")
        fh.write(f"# emd_after={result.emd_after:.6f}\n")
        fh.write(f"# clipped_fraction={result.clipped_fraction:.8f}\n")

        writer = csv.writer(fh)
        writer.writerow(CSV_HEADER)
        for i in range(result.bins):
            writer.writerow(
                [
                    i,
                    f"{lowers[i]:.6f}",
                    f"{centers[i]:.6f}",
                    f"{uppers[i]:.6f}",
                    int(result.hist_reference[i]),
                    int(result.hist_target[i]),
                    int(result.hist_target_matched[i]),
                ]
            )


def read_histogram_csv(path: Path | str) -> tuple[dict[str, str], list[list[str]]]:
    """Parse a file written by `write_histogram_csv`.

    Args:
        path: path to the CSV file.

    Returns:
        A tuple of (metadata dict parsed from the `# key=value` lines, list
        of data rows as strings, header excluded).
    """
    metadata: dict[str, str] = {}
    data_lines = []

    with open(path, newline="", encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#"):
                key, _, value = line[1:].strip().partition("=")
                metadata[key] = value
            else:
                data_lines.append(line)

    rows = list(csv.reader(data_lines))
    return metadata, rows[1:]
