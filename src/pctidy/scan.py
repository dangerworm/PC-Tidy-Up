from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass
class FileRecord:
    path: Path
    relative_path: Path
    size: int
    modified_time: datetime


@dataclass
class ScanResult:
    files: List[FileRecord]
    directory_sizes: Dict[Path, int]
    errors: List[Tuple[Path, str]]
    started_at: datetime
    completed_at: datetime
    total_directories: int


def scan_tree(root: Path, progress_every: int = 500) -> ScanResult:
    if not root.exists():
        raise FileNotFoundError(f"Source directory does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Source path is not a directory: {root}")

    files: List[FileRecord] = []
    errors: List[Tuple[Path, str]] = []
    started_at = datetime.now(timezone.utc)
    total_directories = 0

    for current_dir, _dirnames, filenames in os.walk(root):
        total_directories += 1
        for filename in filenames:
            full_path = Path(current_dir) / filename
            try:
                stat = full_path.stat()
                files.append(
                    FileRecord(
                        path=full_path,
                        relative_path=full_path.relative_to(root),
                        size=stat.st_size,
                        modified_time=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
                    )
                )
            except OSError as exc:  # pragma: no cover - defensive safety
                errors.append((full_path, str(exc)))

            if files and len(files) % progress_every == 0:
                print(f"Scanned {len(files)} files...", file=sys.stderr)

    directory_sizes: Dict[Path, int] = {}
    for record in files:
        accumulate_size(directory_sizes, record.relative_path.parent, record.size)

    completed_at = datetime.now(timezone.utc)
    return ScanResult(
        files=files,
        directory_sizes=directory_sizes,
        errors=errors,
        started_at=started_at,
        completed_at=completed_at,
        total_directories=total_directories,
    )


def accumulate_size(directory_sizes: Dict[Path, int], directory: Path, size: int) -> None:
    # Propagate the file size to the directory and its ancestors, staying within the scan root.
    current = directory
    while True:
        directory_sizes[current] = directory_sizes.get(current, 0) + size
        if current in (Path("."), Path("")):
            break
        parent = current.parent
        if parent == current:
            break
        current = parent


def format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def summarize(scan: ScanResult) -> Dict[str, str | int | float]:
    total_bytes = sum(record.size for record in scan.files)
    duration = (scan.completed_at - scan.started_at).total_seconds()
    return {
        "total_files": len(scan.files),
        "total_directories": scan.total_directories,
        "total_bytes": total_bytes,
        "errors": len(scan.errors),
        "started_at": format_time(scan.started_at),
        "completed_at": format_time(scan.completed_at),
        "duration_seconds": round(duration, 3),
    }
