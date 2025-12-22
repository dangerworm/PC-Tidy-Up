from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from . import analyze
from .reporting import (
    write_errors,
    write_exact_duplicates,
    write_folder_candidates,
    write_largest_files,
    write_largest_folders,
    write_near_duplicates,
    write_summary,
)
from .scan import scan_tree


class ArgumentError(Exception):
    pass


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only file analysis tool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser("scan", help="Scan a directory and write CSV reports")
    scan_parser.add_argument("source", type=Path, help="Directory to scan")
    scan_parser.add_argument("--output", type=Path, default=Path("reports"), help="Directory for CSV reports")
    scan_parser.add_argument("--progress-every", type=int, default=500, help="Print progress every N files")

    return parser.parse_args(argv)


def run_scan(args: argparse.Namespace) -> int:
    try:
        print(f"Scanning {args.source} ...", file=sys.stderr)
        scan = scan_tree(args.source, progress_every=args.progress_every)
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    output_dir: Path = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    scan_duration = (scan.completed_at - scan.started_at).total_seconds()
    print(
        f"Scan complete: {len(scan.files)} files across {scan.total_directories} folders in {scan_duration:.1f}s",
        file=sys.stderr,
    )

    def progress_bar(completed: int, total: int, width: int = 20) -> str:
        if total <= 0:
            return "-" * width
        filled = min(width, int(width * completed / total))
        return "#" * filled + "-" * (width - filled)

    def progress_printer(stage: str):
        def printer(done: int, total: int) -> None:
            percent = (done / total * 100) if total else 0
            bar = progress_bar(done, total)
            print(f"[{stage}] {bar} {done}/{total} ({percent:.1f}%)", file=sys.stderr)

        return printer

    print("Analyzing duplicates (hashing exact matches)...", file=sys.stderr)
    exact_start = time.perf_counter()
    exact_dupes = analyze.find_exact_duplicates(scan.files, progress=progress_printer("exact"))
    print(f"Exact duplicate analysis finished in {time.perf_counter() - exact_start:.1f}s", file=sys.stderr)

    print("Analyzing near-duplicates (comparing names and sizes)...", file=sys.stderr)
    near_start = time.perf_counter()
    near_dupes = analyze.find_near_duplicates(scan.files, progress=progress_printer("near"))
    print(f"Near-duplicate analysis finished in {time.perf_counter() - near_start:.1f}s", file=sys.stderr)

    print("Evaluating folder merge candidates...", file=sys.stderr)
    folder_candidates = analyze.folder_merge_candidates(scan.files)
    largest_file_rows = analyze.largest_files(scan.files)
    largest_folder_rows = analyze.largest_folders(scan.directory_sizes)

    print("Writing reports...", file=sys.stderr)
    write_summary(output_dir, scan)
    write_errors(output_dir, scan.errors)
    write_exact_duplicates(output_dir, exact_dupes)
    write_near_duplicates(output_dir, near_dupes)
    write_folder_candidates(output_dir, folder_candidates)
    write_largest_files(output_dir, largest_file_rows)
    write_largest_folders(output_dir, largest_folder_rows)

    print(f"Reports written to {output_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.command == "scan":
        return run_scan(args)
    raise ArgumentError(f"Unknown command: {args.command}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
