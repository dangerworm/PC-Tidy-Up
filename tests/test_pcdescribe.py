from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from pcdescribe import cli
from pcdescribe import describer


def write_duplicates_csv(path: Path, rows: list[tuple[int, Path, int, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["group", "path", "size_bytes", "sha256"])
        for row in rows:
            writer.writerow([row[0], str(row[1]), row[2], row[3]])


class DescribeTests(unittest.TestCase):
    def test_descriptions_created_for_unique_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            file_a = base / "docs" / "report.txt"
            file_b = base / "docs" / "report copy.txt"
            file_c = base / "photos" / "main" / "image.txt"
            file_d = base / "photos" / "backup" / "image.txt"

            file_a.parent.mkdir(parents=True, exist_ok=True)
            file_a.write_text("Line one\nLine two\nLine three", encoding="utf-8")
            file_b.write_text("Line one\nLine two\nLine three", encoding="utf-8")
            file_c.parent.mkdir(parents=True, exist_ok=True)
            file_c.write_text("Picture description\nSubject details", encoding="utf-8")
            file_d.parent.mkdir(parents=True, exist_ok=True)
            file_d.write_text("Picture description\nSubject details", encoding="utf-8")

            sha_a = describer.sha256_digest(file_a)
            sha_c = describer.sha256_digest(file_c)

            dupes_csv = base / "exact_duplicates.csv"
            write_duplicates_csv(
                dupes_csv,
                [
                    (1, file_a, file_a.stat().st_size, sha_a),
                    (1, file_b, file_b.stat().st_size, sha_a),
                    (2, file_c, file_c.stat().st_size, sha_c),
                    (2, file_d, file_d.stat().st_size, sha_c),
                ],
            )

            output_csv = base / "descriptions.csv"
            exit_code = cli.main(
                [
                    "--dupes",
                    str(dupes_csv),
                    "--out",
                    str(output_csv),
                    "--noise-words",
                    "backup",
                ]
            )
            self.assertEqual(exit_code, 0)
            self.assertTrue(output_csv.exists())

            with output_csv.open("r", encoding="utf-8", newline="") as handle:
                reader = list(csv.DictReader(handle))

            self.assertEqual(len(reader), 2)
            records = {row["sha256"]: row for row in reader}

            self.assertEqual(records[sha_a]["representative_path"], str(file_a))
            self.assertEqual(records[sha_a]["source_paths_count"], "2")
            self.assertIn("Line one", records[sha_a]["description"])
            self.assertIn("filemeta", records[sha_a]["extraction_method"])

            # Backup path should not be chosen when a cleaner option exists
            self.assertEqual(records[sha_c]["representative_path"], str(file_c))
            self.assertEqual(records[sha_c]["source_paths_count"], "2")

    def test_source_prefix_is_used_for_relative_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / "docs").mkdir(parents=True, exist_ok=True)
            (base / "photos").mkdir(parents=True, exist_ok=True)

            relative_text = Path("docs/report.txt")
            relative_image = Path("photos/image.txt")

            (base / relative_text).write_text("Important doc line", encoding="utf-8")
            (base / relative_image).write_text("Image placeholder", encoding="utf-8")

            sha_text = describer.sha256_digest(base / relative_text)
            sha_image = describer.sha256_digest(base / relative_image)

            dupes_csv = base / "exact_duplicates.csv"
            write_duplicates_csv(
                dupes_csv,
                [
                    (1, relative_text, (base / relative_text).stat().st_size, sha_text),
                    (2, relative_image, (base / relative_image).stat().st_size, sha_image),
                ],
            )

            output_csv = base / "descriptions.csv"
            exit_code = cli.main(
                [
                    "--source",
                    str(base),
                    "--dupes",
                    str(dupes_csv),
                    "--out",
                    str(output_csv),
                ]
            )

            self.assertEqual(exit_code, 0)
            with output_csv.open("r", encoding="utf-8", newline="") as handle:
                reader = {row["sha256"]: row for row in csv.DictReader(handle)}

            self.assertEqual(reader[sha_text]["representative_path"], str(base / relative_text))
            self.assertEqual(reader[sha_text]["extraction_method"], "filemeta")


if __name__ == "__main__":
    unittest.main()
