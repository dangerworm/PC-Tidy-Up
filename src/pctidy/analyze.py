from __future__ import annotations

import hashlib
import itertools
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Sequence, Tuple
from difflib import SequenceMatcher

from .scan import FileRecord


CHUNK_SIZE = 1024 * 1024
NEAR_DUPLICATE_SIZE_WINDOW = 1024
NEAR_DUPLICATE_SIMILARITY = 0.8
FOLDER_MERGE_MIN_OVERLAP = 3
FOLDER_MERGE_MIN_JACCARD = 0.3
LARGEST_LIMIT = 100


def sha256_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(CHUNK_SIZE)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


@dataclass
class ExactDuplicate:
    group: int
    path: Path
    size: int
    digest: str


@dataclass
class NearDuplicate:
    group: int
    path: Path
    reference: Path
    size: int
    similarity: float


@dataclass
class FolderMergeCandidate:
    folder_a: Path
    folder_b: Path
    overlap: int
    jaccard: float


def find_exact_duplicates(
    files: Sequence[FileRecord], progress: Callable[[int, int], None] | None = None, progress_every: int = 200
) -> List[ExactDuplicate]:
    by_size: Dict[int, List[FileRecord]] = defaultdict(list)
    for record in files:
        by_size[record.size].append(record)

    duplicates: List[ExactDuplicate] = []
    group = 1
    total_candidates = sum(len(records) for records in by_size.values() if len(records) > 1)
    hashed = 0
    for size, records in sorted(by_size.items(), key=lambda item: item[0], reverse=True):
        if len(records) < 2:
            continue
        digest_map: Dict[str, List[FileRecord]] = defaultdict(list)
        for record in records:
            digest = sha256_digest(record.path)
            digest_map[digest].append(record)
            hashed += 1
            if progress and hashed % progress_every == 0:
                progress(hashed, total_candidates)
        for digest, digest_records in sorted(digest_map.items()):
            if len(digest_records) < 2:
                continue
            for record in sorted(digest_records, key=lambda r: str(r.relative_path)):
                duplicates.append(
                    ExactDuplicate(group=group, path=record.relative_path, size=record.size, digest=digest)
                )
            group += 1
    if progress:
        progress(total_candidates, total_candidates)
    return duplicates


def normalize_name(path: Path) -> str:
    return "".join(ch for ch in path.stem.lower() if ch.isalnum())


def find_near_duplicates(
    files: Sequence[FileRecord], progress: Callable[[int, int], None] | None = None, progress_every: int = 500
) -> List[NearDuplicate]:
    candidates: List[NearDuplicate] = []
    sorted_files = sorted(
        files, key=lambda record: (normalize_name(record.relative_path), record.size, str(record.relative_path))
    )
    group = 1
    processed = 0
    total = len(sorted_files)
    for _, group_records in itertools.groupby(sorted_files, key=lambda record: normalize_name(record.relative_path)):
        record_list = list(group_records)
        for i, base in enumerate(record_list):
            for other in record_list[i + 1 :]:
                if abs(base.size - other.size) > NEAR_DUPLICATE_SIZE_WINDOW:
                    continue
                similarity = SequenceMatcher(None, base.relative_path.stem.lower(), other.relative_path.stem.lower()).ratio()
                if similarity >= NEAR_DUPLICATE_SIMILARITY:
                    candidates.append(
                        NearDuplicate(
                            group=group,
                            path=other.relative_path,
                            reference=base.relative_path,
                            size=other.size,
                            similarity=round(similarity, 3),
                        )
                    )
            if any(c.group == group for c in candidates):
                group += 1
            processed += 1
            if progress and processed % progress_every == 0:
                progress(processed, total)
    if progress:
        progress(total, total)
    return candidates


def folder_merge_candidates(files: Sequence[FileRecord]) -> List[FolderMergeCandidate]:
    folder_map: Dict[Path, set[str]] = defaultdict(set)
    for record in files:
        folder_map[record.relative_path.parent].add(record.relative_path.name)

    folders = sorted(folder_map.keys(), key=lambda p: str(p))
    suggestions: List[FolderMergeCandidate] = []

    for i, folder_a in enumerate(folders):
        files_a = folder_map[folder_a]
        for folder_b in folders[i + 1 :]:
            files_b = folder_map[folder_b]
            overlap = len(files_a & files_b)
            if overlap < FOLDER_MERGE_MIN_OVERLAP:
                continue
            union = len(files_a | files_b)
            jaccard = overlap / union if union else 0.0
            if jaccard >= FOLDER_MERGE_MIN_JACCARD:
                suggestions.append(
                    FolderMergeCandidate(
                        folder_a=folder_a,
                        folder_b=folder_b,
                        overlap=overlap,
                        jaccard=round(jaccard, 3),
                    )
                )
    return suggestions


def largest_files(files: Sequence[FileRecord], limit: int = LARGEST_LIMIT) -> List[Tuple[Path, int]]:
    sorted_files = sorted(files, key=lambda record: record.size, reverse=True)
    return [(record.relative_path, record.size) for record in sorted_files[:limit]]


def largest_folders(directory_sizes: Dict[Path, int], limit: int = LARGEST_LIMIT) -> List[Tuple[Path, int]]:
    sorted_dirs = sorted(directory_sizes.items(), key=lambda item: item[1], reverse=True)
    return [(path, size) for path, size in sorted_dirs[:limit]]
