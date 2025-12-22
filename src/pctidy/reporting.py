from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable, Sequence

from .analyze import ExactDuplicate, FolderMergeCandidate, NearDuplicate
from .scan import ScanResult, summarize


def ensure_output_dir(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)


def write_summary(output_dir: Path, scan: ScanResult) -> None:
    ensure_output_dir(output_dir)
    summary = summarize(scan)
    path = output_dir / "summary.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)


def write_errors(output_dir: Path, errors: Sequence[tuple]) -> None:
    ensure_output_dir(output_dir)
    path = output_dir / "errors.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["path", "error"])
        for path_value, message in errors:
            writer.writerow([str(path_value), message])


def write_exact_duplicates(output_dir: Path, rows: Iterable[ExactDuplicate]) -> None:
    ensure_output_dir(output_dir)
    path = output_dir / "exact_duplicates.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["group", "path", "size_bytes", "sha256"])
        for row in rows:
            writer.writerow([row.group, str(row.path), row.size, row.digest])


def write_near_duplicates(output_dir: Path, rows: Iterable[NearDuplicate]) -> None:
    ensure_output_dir(output_dir)
    path = output_dir / "near_duplicates.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["group", "path", "reference", "size_bytes", "name_similarity"])
        for row in rows:
            writer.writerow([row.group, str(row.path), str(row.reference), row.size, row.similarity])


def write_folder_candidates(output_dir: Path, rows: Iterable[FolderMergeCandidate]) -> None:
    ensure_output_dir(output_dir)
    path = output_dir / "folder_merge_candidates.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["folder_a", "folder_b", "overlap", "jaccard_similarity"])
        for row in rows:
            writer.writerow([str(row.folder_a), str(row.folder_b), row.overlap, row.jaccard])


def write_largest_files(output_dir: Path, rows: Iterable[tuple]) -> None:
    ensure_output_dir(output_dir)
    path = output_dir / "largest_files.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["path", "size_bytes"])
        for row in rows:
            writer.writerow([str(row[0]), row[1]])


def write_largest_folders(output_dir: Path, rows: Iterable[tuple]) -> None:
    ensure_output_dir(output_dir)
    path = output_dir / "largest_folders.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["folder", "size_bytes"])
        for row in rows:
            writer.writerow([str(row[0]), row[1]])
