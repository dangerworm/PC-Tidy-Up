from __future__ import annotations

import csv
import hashlib
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Sequence


@dataclass
class DuplicateGroup:
    sha256: str
    paths: list[Path]

    @property
    def source_paths_count(self) -> int:
        return len(self.paths)


@dataclass
class DescriptionRow:
    sha256: str
    representative_path: Path
    extension: str
    file_type: str
    key_metadata: str
    extraction_method: str
    description: str
    error: str
    source_paths_count: int


DEFAULT_PREFER = []
MARKITDOWN_IGNORELIST = [".xls"]
NOISE_WORDS = ["old computer", "prior", "backup", "copy", "onedrive", "deletions"]

ARCHIVE_EXTENSIONS = {
    ".zip",
    ".cab",
}
AUDIO_EXTENSIONS = {
    ".mp3",
    ".m4a",
    ".m4p",
    ".mid",
    ".wma",
}
BINARY_EXTENSIONS = {
    ".dll",
    ".ocx",
    ".so",
    ".o",
    ".a",
}
CAD_GIS_EXTENSIONS = {
    ".atc",
    ".dwg",
    ".dwt",
    ".dwf",
    ".dxf",
    ".shp",
    ".shx",
    ".sat",
    ".pc3",
    ".pat",
    ".ctb",
    ".stb",
}
DATABASE_EXTENSIONS = {
    ".db",
    ".mdb",
    ".dbx",
    ".data",
    ".dat",
}
DOCUMENT_EXTENSIONS = {
    ".odt",
    ".pub",
    ".chm",
    ".hlp",
    ".mht",
    ".htt",
    ".man",
    ".lrf",
}
EMAIL_EXTENSIONS = {
    ".eml",
}
EXCEL_EXTENSIONS = {
    ".xlsx",
    ".xls",
    ".xlsm",
    ".xlt",
    ".xla",
    ".ods",
    ".wks",
    ".wdb",
}
FONT_EXTENSIONS = {
    ".ttf",
    ".fon",
    ".pfb",
    ".pfm",
}
IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg",
    ".png",
    ".tif", ".tiff",
    ".bmp",
    ".gif",
    ".webp",
    ".dib",
    ".tga",
    ".ico",
    ".icns",
}
INSTALLER_EXTENSIONS = {
    ".exe",
    ".msi",
}
METADATA_EXTENSIONS = {".psd"}
PDF_EXTENSIONS = {
    ".pdf",
}
POWERPOINT_EXTENSIONS = {
    ".pptx",
    ".ppt",
}
TEMP_EXTENSIONS = {
    ".tmp",
    ".bak",
    ".old",
    ".download",
    ".loaded_0",
    ".local",
}
TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".log",
    ".json",
    ".xml",
    ".csv",
    ".ini",
    ".cfg",
    ".config",
    ".inf",
    ".manifest",
    ".map",
    ".mappings",
    ".rul",
    ".prj",
    ".prp",
    ".prv",
    ".resx",
    ".udl",
    ".ics",
    ".url",
    ".plist",
    ".php",
    ".js",
    ".css",
    ".html",
    ".htm",
    ".xsl",
    ".xmx",
    ".aspx",
}
VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".flv",
    ".dvb",
    ".svf",
    ".swf",
}
WORD_EXTENSIONS = {
    ".docx",
    ".doc",
    ".rtf",
}
UNKNOWN_EXTENSIONS = set()

def load_duplicate_groups(dupes_csv: Path, *, source_root: Path | None = None) -> list[DuplicateGroup]:
    with dupes_csv.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if "sha256" not in reader.fieldnames or "path" not in reader.fieldnames:
            raise ValueError("exact_duplicates.csv must contain sha256 and path columns")
        groups: dict[str, list[Path]] = {}
        for row in reader:
            sha = row.get("sha256")
            path_value = row.get("path")
            if not sha or not path_value:
                continue
            sha = sha.strip().lower()
            path_obj = Path(path_value)
            if source_root and not path_obj.is_absolute():
                path_obj = source_root / path_obj
            groups.setdefault(sha, []).append(path_obj)
    return [DuplicateGroup(sha256=key, paths=sorted(paths, key=lambda p: str(p))) for key, paths in groups.items()]

def classify_file(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in ARCHIVE_EXTENSIONS: return "archive"
    if ext in AUDIO_EXTENSIONS: return "audio"
    if ext in BINARY_EXTENSIONS: return "binary"
    if ext in CAD_GIS_EXTENSIONS: return "cad_gis"
    if ext in DATABASE_EXTENSIONS: return "database"
    if ext in DOCUMENT_EXTENSIONS: return "document"
    if ext in EMAIL_EXTENSIONS: return "email"
    if ext in EXCEL_EXTENSIONS: return "excel"
    if ext in FONT_EXTENSIONS: return "font"
    if ext in IMAGE_EXTENSIONS: return "image"
    if ext in INSTALLER_EXTENSIONS: return "installer"
    if ext in PDF_EXTENSIONS: return "pdf"
    if ext in POWERPOINT_EXTENSIONS: return "powerpoint"
    if ext in TEMP_EXTENSIONS: return "temporary"
    if ext in TEXT_EXTENSIONS: return "text"
    if ext in VIDEO_EXTENSIONS: return "video"
    if ext in WORD_EXTENSIONS: return "word"
    return "unknown"


def formatted_timestamp(ts: float) -> str:
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    except (OverflowError, OSError):
        return ""


def file_metadata(path: Path) -> tuple[str, list[str]]:
    tokens = ["filemeta"]
    key_parts: list[str] = []
    try:
        stat = path.stat()
    except OSError as exc:
        return "", [f"stat:{exc}"]
    key_parts.append(f"size={stat.st_size}")
    modified = formatted_timestamp(stat.st_mtime)
    if modified:
        key_parts.append(f"modified={modified}")
    return ", ".join(key_parts), tokens


def run_markitdown(path: Path) -> str | None:
    try:
        from markitdown import MarkItDown  # type: ignore
    except Exception:
        return None
    
    try:
        markdowner = MarkItDown()
        result = None
        try:
            result = markdowner.convert(path)
        except:
            pass

        if not result:
            return None

        if len(result.text_content) > 50:
            return result.text_content[:50]
        
        return result.text_content
    except Exception:
        return None

def read_text_file(path: Path, limit: int = 20000) -> str | None:
    try:
        data = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None
    return data[:limit]


def extract_docx(path: Path) -> tuple[str | None, list[str]]:
    errors: list[str] = []
    try:
        import docx  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        errors.append(f"docx-import:{exc}")
        return None, errors
    try:
        document = docx.Document(path)
        props = document.core_properties
        bits = []
        if props.author:
            bits.append(f"author={props.author}")
        if props.title:
            bits.append(f"title={props.title}")
        if props.created:
            bits.append(f"created={props.created.isoformat()}")
        paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
        description = "\n".join(paragraphs[:5]) if paragraphs else None
        return description, bits
    except Exception as exc:  # pragma: no cover - optional dependency
        errors.append(f"docx-read:{exc}")
        return None, errors


def extract_xlsx(path: Path) -> tuple[str | None, list[str]]:
    errors: list[str] = []
    try:
        import openpyxl  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        errors.append(f"xlsx-import:{exc}")
        return None, errors
    try:
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        sheet_names = workbook.sheetnames
        metadata = [f"sheets={sheet_names}"] if sheet_names else []
        first_value = None
        for sheet in workbook:
            for row in sheet.iter_rows(values_only=True):
                for cell in row:
                    if cell not in (None, ""):
                        first_value = str(cell)
                        break
                if first_value:
                    break
            if first_value:
                break
        description = first_value or None
        return description, metadata
    except Exception as exc:  # pragma: no cover - optional dependency
        errors.append(f"xlsx-read:{exc}")
        return None, errors


def extract_pdf(path: Path) -> tuple[str | None, list[str]]:
    errors: list[str] = []
    try:
        import pypdf  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        errors.append(f"pdf-import:{exc}")
        return None, errors
    try:
        reader = pypdf.PdfReader(str(path))
        metadata_bits = []
        if reader.metadata:
            if reader.metadata.title:
                metadata_bits.append(f"title={reader.metadata.title}")
            if reader.metadata.author:
                metadata_bits.append(f"author={reader.metadata.author}")
        metadata_bits.append(f"pages={len(reader.pages)}")
        first_page_text = reader.pages[0].extract_text() if reader.pages else None
        return first_page_text, metadata_bits
    except Exception as exc:  # pragma: no cover - optional dependency
        errors.append(f"pdf-read:{exc}")
        return None, errors


def extract_image_exif(path: Path) -> tuple[str | None, list[str]]:
    errors: list[str] = []
    try:
        from PIL import Image  # type: ignore
        import piexif  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        errors.append(f"exif-import:{exc}")
        return None, errors
    try:
        with Image.open(path) as img:
            data = img._getexif() or {}
            parts = [f"dimensions={img.width}x{img.height}"]
            if data:
                exif_data = piexif.load(img.info.get("exif", b""))
                date_taken = exif_data.get("Exif", {}).get(piexif.ExifIFD.DateTimeOriginal)
                if date_taken:
                    parts.append(f"date_taken={date_taken.decode(errors='ignore')}")
                model = exif_data.get("0th", {}).get(piexif.ImageIFD.Model)
                if model:
                    parts.append(f"camera={model.decode(errors='ignore')}")
            return None, parts
    except Exception as exc:  # pragma: no cover - optional dependency
        errors.append(f"exif-read:{exc}")
        return None, errors


def select_meaningful_lines(text: str | None, min_lines: int, max_lines: int) -> list[str]:
    if not text:
        return []
    lines = []
    for raw in text.splitlines():
        cleaned = raw.strip()
        if not cleaned or len(cleaned) < 3:
            continue
        if re.fullmatch(r"[\W_]+", cleaned):
            continue
        if re.match(r"page\s+\d+", cleaned, flags=re.IGNORECASE):
            continue
        lines.append(cleaned)
        if len(lines) >= max_lines:
            break
    return lines if len(lines) >= min_lines or not lines else lines


def maybe_ocr(path: Path, enabled: bool, always: bool) -> tuple[str | None, list[str]]:
    if not enabled:
        return None, []
    heuristics = {"scan", "screenshot", "invoice", "letter"}
    name = path.name.lower()
    if not always and not any(token in name for token in heuristics):
        return None, []
    try:
        import pytesseract  # type: ignore
        from PIL import Image  # type: ignore
    except Exception as exc:  # pragma: no cover - optional dependency
        return None, [f"ocr-import:{exc}"]
    try:
        with Image.open(path) as img:
            return pytesseract.image_to_string(img), []
    except Exception as exc:  # pragma: no cover - optional dependency
        return None, [f"ocr-read:{exc}"]


def describe_file(
    sha256: str,
    path: Path,
    *,
    min_lines: int = 2,
    max_lines: int = 5,
    use_ocr: bool = False,
    ocr_always: bool = False,
) -> DescriptionRow:
    extraction_tokens: list[str] = []
    metadata, meta_tokens = file_metadata(path)
    extraction_tokens.extend(meta_tokens)
    error_messages: list[str] = []

    extension = path.suffix.lower()
    file_type = classify_file(path)
    description_lines: list[str] = []

    if file_type == "video":
        return DescriptionRow(
            sha256=sha256,
            representative_path=path,
            extension=extension,
            file_type=file_type,
            key_metadata=metadata,
            extraction_method="|".join(dict.fromkeys(extraction_tokens)),
            description="",
            error="",
            source_paths_count=1,
        )

    markitdown_text = None

    if not extension in MARKITDOWN_IGNORELIST:
        try:
            markitdown_text = run_markitdown(path)
        except Exception as exc:  # pragma: no cover - defensive
            error_messages.append(f"markitdown:{exc}")

        markitdown_lines = select_meaningful_lines(markitdown_text, min_lines, max_lines)
        if markitdown_lines:
            description_lines = markitdown_lines
            extraction_tokens.append("markitdown")

    if not description_lines:
        if file_type == "archive":
            lines = "Zipped/packaged files"

        elif file_type == "audio":
            lines = "Audio file"

        elif file_type == "binary":
            lines = "Audio file"

        elif file_type == "cad_gis":
            lines = "CAD-related file"

        elif file_type == "database":
            lines = "Database file"

        elif file_type == "document":
            lines = "Non-processable document"

        elif file_type == "email":
            lines = "Email"

        elif file_type == "excel":
            lines, errors = extract_xlsx(path)
            if errors:
                error_messages.extend(errors)

        elif file_type == "font":
            lines = "Font file"

        elif file_type == "image":
            _, errors = extract_image_exif(path)
            if errors:
                extraction_tokens.append("exif")
                metadata = ", ".join([metadata] + errors if metadata else errors)
            lines, ocr_errors = maybe_ocr(path, enabled=use_ocr or ocr_always, always=ocr_always)
            if ocr_errors:
                error_messages.extend(ocr_errors)
        
        elif file_type == "installer":
            lines = "Executable file"

        elif file_type == "pdf":
            lines, errors = extract_pdf(path)
            if errors:
                error_messages.extend(errors)

        elif file_type == "powerpoint":
            lines = "Powerpoint"
        
        elif file_type == "temporary":
            lines = "Temp file"

        elif file_type == "text":
            lines = read_text_file(path)
            if len(lines) > 50:
                lines = lines[:50]

        elif file_type == "word":
            lines, errors = extract_docx(path)
            if errors:
                error_messages.extend(errors)

        else:
            lines = "Unknown file type"

        description_lines = select_meaningful_lines(lines, min_lines, max_lines)
        if description_lines:
            extraction_tokens.append(file_type)

    if not extraction_tokens:
        extraction_tokens.append("none")

    return DescriptionRow(
        sha256=sha256,
        representative_path=path,
        extension=extension,
        file_type=file_type,
        key_metadata=metadata,
        extraction_method="|".join(dict.fromkeys(extraction_tokens)),
        description="\n".join(description_lines),
        error=";".join(error_messages),
        source_paths_count=1,
    )


def process_duplicates(
    *,
    sha256: str,
    file_path: Path,
    min_lines: int,
    max_lines: int,
    use_ocr: bool,
    ocr_always: bool,
) -> Iterator[DescriptionRow]:
    yield describe_file(
        sha256,
        file_path,
        min_lines=min_lines,
        max_lines=max_lines,
        use_ocr=use_ocr,
        ocr_always=ocr_always,
    )

def write_descriptions(path: Path, rows: Iterable[DescriptionRow]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "sha256",
                "representative_path",
                "extension",
                "file_type",
                "key_metadata",
                "extraction_method",
                "description",
                "error",
                "source_paths_count",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.sha256,
                    str(row.representative_path),
                    row.extension,
                    row.file_type,
                    row.key_metadata,
                    row.extraction_method,
                    row.description,
                    row.error,
                    row.source_paths_count,
                ]
            )


def sha256_digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def determine_lines_config(min_lines: int | None, max_lines: int | None) -> tuple[int, int]:
    min_value = 2 if min_lines is None else min_lines
    max_value = 5 if max_lines is None else max_lines
    if min_value < 1:
        min_value = 1
    if max_value < min_value:
        max_value = min_value
    return min_value, max_value


def print_progress(current: int, total: int, failures: int, filename: str) -> None:
    percent = (current / total * 100) if total else 0
    print(f"[{current}/{total}] {percent:.1f}% done (failures: {failures}) {filename}", file=sys.stderr)
