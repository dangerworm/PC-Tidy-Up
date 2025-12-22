from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pctidy import analyze
from pctidy.reporting import (
    write_errors,
    write_exact_duplicates,
    write_folder_candidates,
    write_largest_files,
    write_largest_folders,
    write_near_duplicates,
    write_summary,
)
from pctidy.scan import scan_tree


def create_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


class ScanAndReportTests(unittest.TestCase):
    def test_scan_tree_collects_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            file_path = base / "folder" / "example.txt"
            create_file(file_path, b"content")

            result = scan_tree(base, progress_every=1)

            self.assertEqual(len(result.files), 1)
            record = result.files[0]
            self.assertEqual(record.relative_path, Path("folder/example.txt"))
            self.assertEqual(record.size, len(b"content"))
            self.assertIs(record.modified_time.tzinfo, timezone.utc)

    def test_analysis_and_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            create_file(base / "A" / "report.txt", b"alpha")
            create_file(base / "A" / "report (copy).txt", b"alpha")
            create_file(base / "A" / "notes.txt", b"beta")
            create_file(base / "A" / "other.bin", b"beta")
            create_file(base / "B" / "report.txt", b"alpha")
            create_file(base / "B" / "notes.txt", b"beta")
            create_file(base / "B" / "other.bin", b"beta")

            scan = scan_tree(base, progress_every=10)

            exact = analyze.find_exact_duplicates(scan.files)
            near = analyze.find_near_duplicates(scan.files)
            folders = analyze.folder_merge_candidates(scan.files)
            largest_files = analyze.largest_files(scan.files, limit=2)
            largest_folders = analyze.largest_folders(scan.directory_sizes, limit=2)

            self.assertTrue(any(item.path == Path("A/report (copy).txt") for item in exact))
            self.assertTrue(any(item.reference == Path("A/report.txt") for item in near))
            self.assertTrue(
                any(candidate.folder_a == Path("A") and candidate.folder_b == Path("B") for candidate in folders)
            )
            self.assertEqual(len(largest_files), 2)
            self.assertGreaterEqual(len(largest_folders), 1)

            output = base / "reports"
            write_summary(output, scan)
            write_errors(output, scan.errors)
            write_exact_duplicates(output, exact)
            write_near_duplicates(output, near)
            write_folder_candidates(output, folders)
            write_largest_files(output, largest_files)
            write_largest_folders(output, largest_folders)

            for filename in [
                "summary.csv",
                "errors.csv",
                "exact_duplicates.csv",
                "near_duplicates.csv",
                "folder_merge_candidates.csv",
                "largest_files.csv",
                "largest_folders.csv",
            ]:
                self.assertTrue((output / filename).exists())


if __name__ == "__main__":
    unittest.main()
