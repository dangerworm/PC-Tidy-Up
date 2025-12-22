# PC Tidy Up

PC Tidy Up is a read-only file analysis and reporting tool that scans a directory tree, extracts metadata, and produces CSV reports designed for careful human review in Excel. The tool never modifies, moves, or deletes user files.

## Features

- Scan a folder tree without changing any files
- Identify exact duplicates by size and SHA-256 hash
- Flag near-duplicate candidates by similar names and sizes
- Suggest folder merge candidates based on overlapping file names
- Report the largest files and folders
- Summarize scan statistics and capture errors in a dedicated report

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

```bash
pctidy scan /path/to/archive --output ./reports
```

The command writes CSV reports into the `--output` directory. The source files are never modified.

## pcdescribe companion tool

Use `pcdescribe` to summarize the contents of exact duplicate groups produced by `pctidy`:

```bash
pcdescribe --source /path/to/archive --dupes ./reports/exact_duplicates.csv --out ./reports/descriptions.csv
```

Pass `--source` when the `path` column in `exact_duplicates.csv` is relative; the value is prefixed to locate files for
metadata and description extraction.

The command picks one representative path per unique SHA-256 hash, extracts concise descriptions and metadata, and writes a
single CSV that can be joined back to the duplicate listings in Excel.
