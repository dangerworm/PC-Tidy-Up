from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from .describer import (
    DEFAULT_PREFER,
    NOISE_WORDS,
    determine_lines_config,
    load_duplicate_groups,
    print_progress,
    process_duplicates,
    write_descriptions,
)


class ArgumentError(Exception):
    pass


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Describe unique files from duplicate list")
    parser.add_argument("--source", type=Path, help="Root directory that contains the duplicate paths")
    parser.add_argument("--dupes", type=Path, required=True, help="Path to exact_duplicates.csv")
    parser.add_argument("--out", type=Path, required=True, help="Output CSV for descriptions")
    parser.add_argument("--ocr", action="store_true", help="Enable OCR for likely images")
    parser.add_argument("--ocr-always", action="store_true", help="Force OCR for all images")
    parser.add_argument("--max-lines", type=int, default=5, help="Maximum description lines")
    parser.add_argument("--min-lines", type=int, default=2, help="Minimum description lines")
    parser.add_argument(
        "--prefer-path-keywords",
        type=str,
        default=",".join(DEFAULT_PREFER),
        help="Comma separated keywords to prefer for representative paths",
    )
    parser.add_argument(
        "--noise-words",
        type=str,
        default=",".join(NOISE_WORDS),
        help="Comma separated keywords to avoid for representative paths",
    )
    return parser.parse_args(argv)

def choose_representative_file(paths: Sequence[Path], noise_words: Sequence[str], prefer_keywords: Sequence[str]) -> Path:
    return min(paths, key=lambda p: (score_path(p, noise_words, prefer_keywords), len(str(p)), str(p)))

def score_path(path: Path, noise_words: Sequence[str], prefer_keywords: Sequence[str]) -> int:
    path_str = str(path).lower()
    score = len(path_str)
    for word in noise_words:
        if word and word.lower() in path_str:
            score += 25
    for word in prefer_keywords:
        if word and word.lower() in path_str:
            score -= 5
    return score

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    min_lines, max_lines = determine_lines_config(args.min_lines, args.max_lines)

    if args.source and not args.source.exists():
        print(f"Error: source directory {args.source} does not exist", file=sys.stderr)
        return 2
    if args.source and not args.source.is_dir():
        print(f"Error: source path {args.source} is not a directory", file=sys.stderr)
        return 2

    try:
        groups = load_duplicate_groups(args.dupes, source_root=args.source)
    except FileNotFoundError:
        print(f"Error: {args.dupes} not found", file=sys.stderr)
        return 2
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    noise_words = [word.strip() for word in args.noise_words.split(",") if word.strip()]
    prefer_keywords = [word.strip() for word in args.prefer_path_keywords.split(",") if word.strip()]

    total = len(groups)
    failures = 0
    rows = []
    for idx, group in enumerate(groups, start=1):
        try:
            file_path = choose_representative_file(
                group.paths, 
                noise_words, 
                prefer_keywords
            )

            row = next(
                process_duplicates(
                    sha256=group.sha256,
                    file_path=file_path,
                    min_lines=min_lines,
                    max_lines=max_lines,
                    use_ocr=args.ocr,
                    ocr_always=args.ocr_always,
                )
            )
            row.source_paths_count = group.source_paths_count

        except Exception as exc:  # pragma: no cover - defensive
            failures += 1
            print(f"Failed processing {group.sha256}: {exc}", file=sys.stderr)
            continue
        rows.append(row)
        print_progress(idx, total, failures, group.paths[0])

    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_descriptions(args.out, rows)
    print(f"Wrote descriptions for {len(rows)} unique hashes to {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
