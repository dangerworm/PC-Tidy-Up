# Specification

This document summarizes the functional expectations for PC Tidy Up. The implementation prioritizes safety, transparency, and deterministic reporting.

## Philosophy

- **Read-only:** Never modify, move, rename, or delete user files.
- **Transparency:** Every suggestion includes the evidence that triggered it.
- **Human judgment:** Reports highlight risks; humans decide what to do.
- **Deterministic:** The same input produces the same output ordering.

## CLI Behavior

- Command: `pctidy scan <source> --output <dir>`
- Fails fast if the source directory does not exist or the output directory cannot be created.
- Prints periodic progress updates while walking large trees.
- Writes CSV reports to the output directory without altering the source.

## Collected Metadata

For every file that can be inspected:
- Relative path from the scan root
- File size in bytes
- Modified time (UTC ISO 8601)
- Optional SHA-256 hash (for duplicate detection when required)

If a file cannot be read, the error is captured in the errors report and scanning continues.

## Reports

All reports are UTF-8 CSV with headers.

- **summary.csv**
  - Total files and folders scanned
  - Total bytes across files
  - Count of unreadable paths
  - Scan duration and start time

- **errors.csv**
  - Path
  - Error message

- **exact_duplicates.csv**
  - Group identifier
  - Path
  - Size bytes
  - SHA-256 hash

- **near_duplicates.csv**
  - Candidate group identifier
  - Path
  - Size bytes
  - Name similarity score (0–1)
  - Reference path the candidate was compared against

- **folder_merge_candidates.csv**
  - Folder A
  - Folder B
  - Overlapping file count
  - Jaccard similarity of file basenames

- **largest_files.csv**
  - Path
  - Size bytes

- **largest_folders.csv**
  - Folder path
  - Aggregate size bytes

## Heuristics

- **Exact duplicates:** Files grouped by identical size and SHA-256 hash.
- **Near duplicates:** Files within ±1024 bytes of each other whose stem names have a similarity ratio of at least 0.8.
- **Folder merge candidates:** Directories sharing at least 3 common basenames and with a Jaccard similarity of ≥0.3.
- **Largest lists:** Top 100 entries sorted by size descending.

