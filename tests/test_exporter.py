import csv
from pathlib import Path

from exporter import write_csv

_COLUMNS = ["id", "name", "email", "description", "photoUrl", "Bio"]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


class TestWriteCsv:
    def test_creates_file_with_correct_headers(self, tmp_path: Path):
        out = tmp_path / "out.csv"
        write_csv([], str(out))

        with open(out, encoding="utf-8") as fh:
            headers = fh.readline().strip().split(",")

        assert headers == _COLUMNS

    def test_writes_all_fields(self, tmp_path: Path):
        record = {
            "id": "abc123",
            "name": "Alice",
            "email": "alice@example.com",
            "description": "CTO",
            "photoUrl": "https://example.com/alice.jpg",
            "Bio": "Long bio here.",
        }
        out = tmp_path / "speakers.csv"
        write_csv([record], str(out))

        rows = _read_csv(out)
        assert len(rows) == 1
        assert rows[0] == record

    def test_truncates_long_name_field(self, tmp_path: Path):
        out = tmp_path / "out.csv"
        long_name = "A" * 300
        write_csv([{"id": "x", "name": long_name, "email": "", "description": "", "photoUrl": "", "Bio": ""}], str(out))

        rows = _read_csv(out)
        assert len(rows[0]["name"]) == 191

    def test_truncates_long_bio_field(self, tmp_path: Path):
        out = tmp_path / "out.csv"
        long_bio = "B" * 6000
        write_csv([{"id": "x", "name": "N", "email": "", "description": "", "photoUrl": "", "Bio": long_bio}], str(out))

        rows = _read_csv(out)
        assert len(rows[0]["Bio"]) == 5000

    def test_missing_fields_default_to_empty_string(self, tmp_path: Path):
        out = tmp_path / "out.csv"
        write_csv([{"name": "Bob"}], str(out))

        rows = _read_csv(out)
        assert rows[0]["email"] == ""
        assert rows[0]["Bio"] == ""
        assert rows[0]["id"] == ""

    def test_creates_parent_directories(self, tmp_path: Path):
        nested = tmp_path / "a" / "b" / "c" / "out.csv"
        write_csv([], str(nested))
        assert nested.exists()

    def test_overwrites_existing_file(self, tmp_path: Path):
        out = tmp_path / "out.csv"
        write_csv([{"id": "1", "name": "First", "email": "", "description": "", "photoUrl": "", "Bio": ""}], str(out))
        write_csv([{"id": "2", "name": "Second", "email": "", "description": "", "photoUrl": "", "Bio": ""}], str(out))

        rows = _read_csv(out)
        assert len(rows) == 1
        assert rows[0]["name"] == "Second"

    def test_writes_multiple_records_in_order(self, tmp_path: Path):
        out = tmp_path / "out.csv"
        records = [
            {"id": str(i), "name": f"Speaker {i}", "email": "", "description": "", "photoUrl": "", "Bio": ""}
            for i in range(5)
        ]
        write_csv(records, str(out))

        rows = _read_csv(out)
        assert [r["name"] for r in rows] == [f"Speaker {i}" for i in range(5)]

    def test_deduplicates_by_photo_url(self, tmp_path: Path):
        out = tmp_path / "out.csv"
        records = [
            {"id": "1", "name": "Alice", "email": "", "description": "", "photoUrl": "https://example.com/alice.jpg", "Bio": ""},
            {"id": "2", "name": "Alice Duplicate", "email": "", "description": "", "photoUrl": "https://example.com/alice.jpg", "Bio": ""},
            {"id": "3", "name": "Bob", "email": "", "description": "", "photoUrl": "https://example.com/bob.jpg", "Bio": ""},
        ]
        write_csv(records, str(out))

        rows = _read_csv(out)
        assert len(rows) == 2
        assert rows[0]["name"] == "Alice"
        assert rows[1]["name"] == "Bob"

    def test_keeps_records_without_photo_url(self, tmp_path: Path):
        out = tmp_path / "out.csv"
        records = [
            {"id": "1", "name": "Alice", "email": "", "description": "", "photoUrl": "", "Bio": ""},
            {"id": "2", "name": "Bob", "email": "", "description": "", "photoUrl": "", "Bio": ""},
        ]
        write_csv(records, str(out))

        rows = _read_csv(out)
        assert len(rows) == 2
