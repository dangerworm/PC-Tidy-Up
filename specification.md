# Drive Tidy Reporter – Full Specification

## Overview

**Drive Tidy Reporter** is a read‑only Python CLI tool for Windows 10 that analyses a directory tree (e.g. a family archive copied across multiple computers over time) and produces **Excel‑friendly CSV reports** to help humans manually organise files.

The tool:
- Never modifies, moves, or deletes user files
- Produces transparent, auditable reports
- Is conservative and human‑centred
- Is designed for review and decision‑making in spreadsheets

This project explicitly avoids automation of destructive actions.

---

## Goals

- Help users understand what is on a drive
- Identify exact and near duplicates
- Identify folders that are likely copies of each other
- Surface meaningful metadata to aid human judgement
- Reduce emotional and cognitive load when organising large personal archives
- File metadata extraction for all MS Office files (docx, xlsx, pptx)
- File metadata extraction for PDFs, images, and other files
- OCR scanning of PDF documents to give an idea of content

---

## Non‑Goals

- No automatic file deletion
- No automatic file moves or renaming
- No cloud integration (Google Drive, OneDrive, etc.)
- No GUI or web interface

---

## Target Environment

- Windows 10
- Python 3.11+
- Typical home PC (60GB dataset)
- Files stored locally (not live‑linked to cloud providers)

---

## Primary User Personas

### Retired Professional (Spreadsheet‑First)

- Comfortable with Excel
- Wants evidence before taking action
- Distrusts automation
- Values clarity, provenance, and reversibility

### Technically Literate Family Member

- Runs the tool
- Interprets results
- Helps guide decisions

---

## User Stories

### US‑01: Inventory Visibility

**As a user**, I want to know what files and folders exist and how large they are, **so that** I can prioritise what to clean up.

### US‑02: Duplicate Confidence

**As a user**, I want to see exact duplicates clearly identified with contextual information, **so that** I can confidently remove copies by hand.

### US‑03: Contextual Recognition

**As a user**, I want to see document metadata (titles, first lines, authors), **so that** I can recognise files without opening them.

### US‑04: Folder Merge Insight

**As a user**, I want to know which folders are probably copies of the same thing, **so that** I can merge them safely.

### US‑05: Trust & Safety

**As a user**, I want assurance that nothing is being changed automatically, **so that** I can review everything at my own pace.

---

## CLI Interface

### Invocation

```powershell
python tidy_report.py <root_path> --out <output_directory>
```

### Behaviour

- Scans the directory tree rooted at `<root_path>`
- Writes CSV reports to `<output_directory>`
- Prints progress and summary information to stdout

---

## Output Files

All outputs are CSV (UTF‑8, headers included, Excel‑friendly).

### 01_duplicates_exact.csv

Identifies byte‑for‑byte identical files.

**Columns**

- duplicate_group_id
- group_total_files
- group_total_size_mb
- file_path
- file_name
- extension
- size_bytes
- modified_time_iso
- sha256
- suggested_keep (TRUE/FALSE)
- keep_reason
- meta_summary
- meta_author
- meta_created
- meta_first_text
- notes

**Acceptance Criteria**

- Only files with identical SHA256 hashes are grouped
- At least one file per group is marked suggested_keep=TRUE
- Metadata is best‑effort and never required

---

### 02_duplicates_near.csv

Flags files that may be duplicates but are not identical.

**Heuristics**

- Same filename (case‑insensitive)
- Size within 2% or 200KB

**Columns**

- candidate_group_id
- file_path_a
- file_path_b
- file_name
- size_a_bytes
- size_b_bytes
- size_diff_bytes
- mtime_a_iso
- mtime_b_iso
- same_extension
- reason
- meta_summary_a
- meta_summary_b
- notes

**Acceptance Criteria**

- No hashing used to assert identity
- Output capped at 5,000 candidate pairs
- No automated conclusions drawn

---

### 03_folder_merge_candidates.csv

Identifies folders likely representing the same conceptual content.

**Folder Name Normalisation**

- Lowercase
- Remove years (e.g. 2021)
- Remove noise words:
  - old, computer, copy, backup, prior, onedrive, deletion, desktop
- Collapse punctuation and whitespace

**Clustering**

- difflib similarity >= 0.75
- Exact normalised matches always cluster

**Columns**

- cluster_id
- normalized_folder_name
- folder_path
- folder_total_size_mb
- file_count
- duplicate_overlap_pct
- suggested_destination_folder
- destination_reason
- notes

**Acceptance Criteria**

- Clusters must contain at least 2 folders
- Overlap calculation skips files >1GB
- Suggested destination is explainable

---

### 04_top_folders.csv

Top 100 folders by total size.

**Columns**

- folder_path
- total_size_mb
- file_count

---

### 05_top_files.csv

Top 200 files by size.

**Columns**

- file_path
- size_mb
- modified_time_iso
- meta_summary

---

### scan_summary.csv

Overall scan statistics.

**Columns**

- root_scanned
- total_files
- total_folders
- total_size_gb
- scan_started_iso
- scan_finished_iso
- duration_seconds
- errors_count
- notes

---

### scan_errors.csv

Files that could not be read.

**Columns**

- file_path
- error_type
- error_message

---

## Metadata Extraction

Metadata is read‑only, best‑effort, and advisory only.

### Supported Types

| Type | Library | Extracted |
|----|----|----|
| .docx | python‑docx | title, author, first paragraph |
| .xlsx | openpyxl | sheet names, first cell |
| .pdf | pypdf | title, first page text |
| images | Pillow + piexif | date taken, camera |
| text | stdlib | first line |

**Rules**

- Include all files regardless of size
- Failures recorded but never fatal

---

## Performance Requirements

- Reasonable runtime on 60GB dataset
- Hashing only performed for size‑collision groups
- Memory usage must be bounded
- Progress printed periodically

---

## Safety & Trust Guarantees

- Read‑only access only
- No file writes outside output directory
- No registry, network, or cloud access
- All decisions surfaced to humans
- Deterministic, repeatable output

---

## Implementation Notes

### Required Libraries

```text
python-docx
openpyxl
pypdf
Pillow
piexif
tesseract
```

### Suggested Structure

- scan_files()
- compute_hashes()
- find_exact_duplicates()
- find_near_duplicates()
- cluster_folders()
- extract_metadata()
- write_csv_*()

---

## Success Criteria

- Users can identify and remove duplicates manually with confidence
- Users can understand folder history and merge safely
- No data loss possible through tool misuse
- Parents trust the output enough to act on it

---

## License / Ethos

This tool is intended for personal and family use, prioritising:

- Transparency
- Reversibility
- Human judgement
- Respect for personal data
