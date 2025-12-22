# pcdescribe tool

This document describes the **second script** in the PC-Tidy-Up repository. This will be a companion Python CLI script in this repo called pcdescribe.
Its purpose is to **describe files once per unique content hash**, producing a single CSV that can be joined back to duplicate data in Excel.

## Purpose

- Produce ONE CSV file (descriptions.csv) describing each unique file content exactly once.
- Use exact_duplicates.csv as input; it contains at least columns: sha256, path.
- Group by sha256; choose one representative path per sha256 and process only that file.
- Output must be one row per sha256, with columns:
  sha256, representative_path, extension, file_type, key_metadata,
  extraction_method, description, error, source_paths_count

## Rules

- Read-only: DO NOT modify, move, delete, or rename any files.
- For each sha group, pick representative_path (prefer shortest path; optionally avoid noise words old/backup/copy/prior/onedrive/deletions).
- Extract description as 2–5 meaningful lines using text extraction.
- Primary extraction: MarkItDown where applicable.
- Also extract metadata using type-specific libraries:
  - docx: python-docx (author/title/created + first paragraph)
  - xlsx: openpyxl (sheet names + first non-empty cell)
  - pptx: python-pptx (slide titles + first bullets) [if easy]
  - pdf: pypdf (title/author/pages + first page text)
  - images: Pillow + piexif (date_taken/camera/dimensions)
  - text: first non-empty lines (stdlib)
- Optional OCR (OFF by default):
  - If --ocr flag, run pytesseract on images likely to contain text (filename contains scan/screenshot/invoice/letter).
- extraction_method: pipe-separated tokens of successful methods (markitdown|exif|ocr|docx|xlsx|pdf|filemeta).
- key_metadata: a single compact string, e.g. "author=..., created=..., sheets=[...], date_taken=..., camera=..., pages=..."
- description: join selected lines with newline characters; keep it short.
- If extraction fails, set error but continue.

## CLI
python pcdescribe --dupes exact_duplicates.csv --out descriptions.csv [--ocr]

## Implementation
- Use pathlib, csv, dataclasses.
- Be robust to errors and long paths on Windows.
- Print progress: total unique sha, current index, failures count.
- Keep runtime reasonable for ~60GB dataset.

# Design Overview

## What This New Script Does

### Input

- `exact_duplicates.csv` (from the first tool), containing at least:
  - `sha256`
  - `path`
  - *(optional)* size, group id, etc.

---

### Output

A single CSV (e.g. `descriptions.csv`), **one row per unique `sha256`**, with the following columns:

- `sha256` *(primary key)*
- `representative_path` – one “chosen” path for that hash
- `extension`
- `file_type`  
  *(word / excel / ppt / pdf / image / video / text / unknown)*
- `key_metadata`  
  *(author / sheets / date_taken / etc., compact string)*
- `extraction_method`  
  *(pipe-separated list such as `markitdown|exif` or `docx|exif`)*
- `description`  
  *(2–5 meaningful lines; empty if not possible)*
- `error` *(if any)*
- `source_paths_count`  
  *(number of duplicate paths mapping to this hash)*

This allows `sha256` to be used as a **join key in Excel**, linking descriptions back to all duplicate rows.

---

## Dedupe Strategy Using `exact_duplicates.csv`

1. Read `exact_duplicates.csv`
2. Group rows by `sha256`
3. For each SHA group:
   - Choose a `representative_path`:
     - Prefer the **shortest path**, **or**
     - Prefer a path *not* containing:
       - `old computer`
       - `prior`
       - `backup`
       - `copy`
       *(optional scoring)*
   - Process **only the representative file**
   - Record `source_paths_count`

This guarantees **one description per unique file content**.

---

## Extraction Strategy (Phase 1)

### Primary Extractor: MarkItDown (Best Effort)

Attempt **MarkItDown** first for:

- `.docx`
- `.pptx`
- `.xlsx`
- `.pdf`
- `.txt`
- `.md`
- `.html`
- etc.

**Result:**
- Markdown / plaintext output

The `description` is created by selecting **2–5 meaningful lines** from the extracted text.

---

## Metadata Extractors

Used in parallel or as fallback:

- **Word (`.docx`)**  
  - Author / title / created  
  - First paragraph  
  *(python-docx)*

- **Excel (`.xlsx`)**  
  - Sheet names  
  - First non-empty cell or A1  
  *(openpyxl)*

- **PowerPoint (`.pptx`)**  
  - Slide titles and first bullets  
  *(python-pptx; optional but cheap)*

- **PDF (`.pdf`)**  
  - Title / author / page count  
  - First page text  
  *(pypdf)*

- **Images**  
  - EXIF date taken  
  - Camera model  
  - Dimensions  
  *(Pillow + piexif)*

- **Text files**  
  - First non-empty lines  
  *(stdlib)*

---

## Optional OCR (Off by Default)

OCR is **opt-in** and only applies to images.

- Engine: **Tesseract via pytesseract**
- OCR runs only if:
  - Filename suggests text  
    *(scan, screenshot, invoice, letter)*  
  **OR**
  - EXIF is missing and resolution appears document-like *(optional heuristic)*

OCR process:
1. Extract ~10 lines of text
2. Apply the same **“meaningful lines”** filter

---

## “2–5 Meaningful Lines” Rule (Important)

Given extracted text (from MarkItDown or OCR):

1. Split into lines
2. Trim whitespace
3. Drop lines that are:
   - Empty
   - Just punctuation
   - Super short junk (e.g. `< 3 chars`)
   - Boilerplate like `Page 1` *(simple regex)*
4. Take:
   - **Up to 5 lines**
   - **At least 2 lines**, if available
5. Join with `\n` in the CSV  
   *(Excel will render line breaks in a cell)*

If nothing usable remains:
- `description = ""`
- `error` remains empty unless extraction failed

---

## File Type Classification (Simple)

Based on file extension:

- **Word**: `.docx`
- **Excel**: `.xlsx`, `.xlsm`
- **PowerPoint**: `.pptx`
- **PDF**: `.pdf`
- **Image**:  
  `.jpg .jpeg .png .tif .tiff .bmp .gif .webp`  
  *(optional HEIC later)*
- **Text**:  
  `.txt .md .csv .log .json .xml`
- **Video**:  
  `.mp4 .mov .avi .mkv`
- **Unknown**: everything else

### Video Handling
For video files:
- `key_metadata = "size=..., modified=..."`
- `description = ""`
- `extraction_method = "filemeta"`

---

## Extraction Precedence

For each file:

1. Always collect basic file stats  
   *(size, mtime → key_metadata)*
2. Try **MarkItDown** → description
3. If MarkItDown fails or yields nothing meaningful:
   - Use type-specific extractor (docx / xlsx / pptx / pdf / text)
4. For images:
   - EXIF always (if present)
   - OCR only if `--ocr` flag is set and heuristics match

### Extraction Method Tokens

`extraction_method` records all successful steps:

- `markitdown`
- `docx`
- `xlsx`
- `pptx`
- `pdf`
- `exif`
- `ocr`
- `filemeta`
- `none`

---

## CLI Interface (Prescriptive)

```bash
python describe_files.py --dupes exact_duplicates.csv --out descriptions.csv
```

### Optional Flags

- `--ocr`  
  Enable OCR

- `--ocr-always`  
  Force OCR on all images *(not recommended)*

- `--max-lines 5`  
  Maximum description lines *(default: 5)*

- `--min-lines 2`  
  Minimum description lines *(default: 2)*

- `--prefer-path-keywords "Documents,Pictures"`  
  Bias representative path selection *(optional)*

- `--noise-words "old,backup,copy,prior,onedrive,deletions"`  
  Path scoring noise words *(optional)*

---

## Libraries

Required:
- `markitdown` *(Microsoft MarkItDown)*
- `python-docx`
- `openpyxl`
- `pypdf`
- `Pillow`
- `piexif`

Optional OCR:
- `pytesseract`
- Locally installed **Tesseract OCR**

---
