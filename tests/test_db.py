from collections.abc import Sequence
from unittest.mock import MagicMock, patch

from config import DbConfig
from db import DbSpeaker, fetch_existing_speakers, insert_speakers, reconcile_speakers, update_speaker

_CFG = DbConfig(host="localhost", database="test_db", user="user", password="pass")


def _record(
    name: str = "Alice Smith",
    photo_url: str = "https://example.com/alice.jpg",
    bio: str = "Engineer",
) -> dict[str, str]:
    return {"id": "abc", "name": name, "email": "", "description": "Dev", "photoUrl": photo_url, "Bio": bio}


def _db_speaker(
    name: str = "Alice Smith",
    photo_url: str = "https://example.com/alice.jpg",
    bio: str = "Engineer",
    description: str = "Dev",
) -> DbSpeaker:
    return DbSpeaker(name=name, photo_url=photo_url, bio=bio, description=description)


def _mock_connection(rows: Sequence[tuple[str | None, ...]]):
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = rows

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.__enter__ = MagicMock(return_value=mock_conn)
    mock_conn.__exit__ = MagicMock(return_value=False)

    return mock_conn


# --- reconcile_speakers (pure logic path; update_speaker patched) ---

class TestReconcileSpeakers:
    def test_new_speaker_passes_through(self):
        record = _record()
        result = reconcile_speakers([record], existing={}, cfg=_CFG)
        assert result == [record]

    def test_exact_match_excluded_from_csv(self):
        existing = {"alice smith": _db_speaker()}
        result = reconcile_speakers([_record()], existing, _CFG)
        assert result == []

    def test_url_mismatch_triggers_update_and_excluded_from_csv(self):
        existing = {"alice smith": _db_speaker(photo_url="https://example.com/old.jpg")}
        record = _record(photo_url="https://example.com/new.jpg")

        with patch("db.update_speaker") as mock_update:
            result = reconcile_speakers([record], existing, _CFG)

        assert result == []
        mock_update.assert_called_once_with(_CFG, "Alice Smith", "https://example.com/new.jpg", "Engineer", "Dev")

    def test_bio_mismatch_triggers_update_and_excluded_from_csv(self):
        existing = {"alice smith": _db_speaker(bio="Old bio")}
        record = _record(bio="New bio")

        with patch("db.update_speaker") as mock_update:
            result = reconcile_speakers([record], existing, _CFG)

        assert result == []
        mock_update.assert_called_once_with(_CFG, "Alice Smith", "https://example.com/alice.jpg", "New bio", "Dev")

    def test_description_mismatch_triggers_update_and_excluded_from_csv(self):
        existing = {"alice smith": _db_speaker(description="Old title")}
        record = _record()  # _record has description="Dev"

        with patch("db.update_speaker") as mock_update:
            result = reconcile_speakers([record], existing, _CFG)

        assert result == []
        mock_update.assert_called_once_with(_CFG, "Alice Smith", "https://example.com/alice.jpg", "Engineer", "Dev")

    def test_case_insensitive_name_match(self):
        # DB stores "Dr. Rania Khalaf"; scraper returns "dr. rania khalaf"
        existing = {"dr. rania khalaf": _db_speaker(name="Dr. Rania Khalaf")}
        record = _record(name="dr. rania khalaf")
        result = reconcile_speakers([record], existing, _CFG)
        assert result == []

    def test_update_uses_original_db_name_as_where_target(self):
        # Scraped name has different casing; UPDATE must target the stored DB name.
        existing = {"dr. rania khalaf": _db_speaker(name="Dr. Rania Khalaf", photo_url="https://old.com/a.jpg")}
        record = _record(name="dr. rania khalaf", photo_url="https://new.com/a.jpg")

        with patch("db.update_speaker") as mock_update:
            reconcile_speakers([record], existing, _CFG)

        # db_name arg must be the original stored value, not the scraped variant
        assert mock_update.call_args[0][1] == "Dr. Rania Khalaf"

    def test_all_fields_in_sync_excluded_from_csv(self):
        # description must also match for a speaker to be considered in sync
        existing = {"alice smith": _db_speaker(description="Dev")}
        result = reconcile_speakers([_record()], existing, _CFG)
        assert result == []

    def test_mixed_new_and_existing_speakers(self):
        existing = {"alice smith": _db_speaker()}
        alice = _record(name="Alice Smith")
        bob = _record(name="Bob Jones", photo_url="https://example.com/bob.jpg")
        result = reconcile_speakers([alice, bob], existing, _CFG)
        assert result == [bob]

    def test_empty_records(self):
        assert reconcile_speakers([], {}, _CFG) == []


# --- fetch_existing_speakers ---

class TestFetchExistingSpeakers:
    def test_returns_normalized_key_dict(self):
        rows = [("Dr. Rania Khalaf", "https://example.com/r.jpg", "Bio text", "Engineer")]
        mock_conn = _mock_connection(rows)

        with patch("db.mysql.connector.connect", return_value=mock_conn):
            result = fetch_existing_speakers(_CFG)

        assert "dr. rania khalaf" in result
        speaker = result["dr. rania khalaf"]
        assert speaker.name == "Dr. Rania Khalaf"
        assert speaker.photo_url == "https://example.com/r.jpg"
        assert speaker.bio == "Bio text"
        assert speaker.description == "Engineer"

    def test_null_photo_url_becomes_empty_string(self):
        rows = [("Alice", None, "Some bio", "Dev")]
        mock_conn = _mock_connection(rows)

        with patch("db.mysql.connector.connect", return_value=mock_conn):
            result = fetch_existing_speakers(_CFG)

        assert result["alice"].photo_url == ""

    def test_null_bio_becomes_empty_string(self):
        rows = [("Alice", "https://example.com/a.jpg", None, "Dev")]
        mock_conn = _mock_connection(rows)

        with patch("db.mysql.connector.connect", return_value=mock_conn):
            result = fetch_existing_speakers(_CFG)

        assert result["alice"].bio == ""

    def test_null_description_becomes_empty_string(self):
        rows = [("Alice", "https://example.com/a.jpg", "Bio", None)]
        mock_conn = _mock_connection(rows)

        with patch("db.mysql.connector.connect", return_value=mock_conn):
            result = fetch_existing_speakers(_CFG)

        assert result["alice"].description == ""

    def test_null_name_row_excluded(self):
        rows = [(None, "https://example.com/a.jpg", "Bio", "Dev")]
        mock_conn = _mock_connection(rows)

        with patch("db.mysql.connector.connect", return_value=mock_conn):
            result = fetch_existing_speakers(_CFG)

        assert result == {}

    def test_empty_table_returns_empty_dict(self):
        mock_conn = _mock_connection([])

        with patch("db.mysql.connector.connect", return_value=mock_conn):
            result = fetch_existing_speakers(_CFG)

        assert result == {}


# --- update_speaker ---

class TestUpdateSpeaker:
    def test_executes_correct_sql_and_commits(self):
        mock_conn = _mock_connection([])

        with patch("db.mysql.connector.connect", return_value=mock_conn):
            update_speaker(_CFG, "Dr. Rania Khalaf", "https://new.com/r.jpg", "Updated bio", "Lead Engineer")

        cursor = mock_conn.cursor.return_value
        cursor.execute.assert_called_once_with(
            "UPDATE speaker SET photoUrl = %s, Bio = %s, description = %s WHERE name = %s",
            ("https://new.com/r.jpg", "Updated bio", "Lead Engineer", "Dr. Rania Khalaf"),
        )
        mock_conn.commit.assert_called_once()


# --- insert_speakers ---

class TestInsertSpeakers:
    def test_inserts_all_rows_with_sequential_ids(self):
        mock_conn = _mock_connection([])
        records = [
            _record(name="Alice Smith", photo_url="https://example.com/a.jpg", bio="Bio A"),
            _record(name="Bob Jones", photo_url="https://example.com/b.jpg", bio="Bio B"),
        ]

        with patch("db.mysql.connector.connect", return_value=mock_conn):
            insert_speakers(_CFG, records, start_id=381)

        cursor = mock_conn.cursor.return_value
        cursor.executemany.assert_called_once_with(
            "INSERT INTO speaker (id, name, email, description, photoUrl, Bio) VALUES (%s, %s, %s, %s, %s, %s)",
            [
                (381, "Alice Smith", "", "Dev", "https://example.com/a.jpg", "Bio A"),
                (382, "Bob Jones", "", "Dev", "https://example.com/b.jpg", "Bio B"),
            ],
        )
        mock_conn.commit.assert_called_once()

    def test_id_field_is_included(self):
        mock_conn = _mock_connection([])

        with patch("db.mysql.connector.connect", return_value=mock_conn):
            insert_speakers(_CFG, [_record()], start_id=381)

        cursor = mock_conn.cursor.return_value
        sql = cursor.executemany.call_args[0][0]
        assert sql.startswith("INSERT INTO speaker (id,")

    def test_scraper_uuid_is_not_used(self):
        # The record's 'id' key holds a scraper-generated uuid — it must not appear in any row tuple.
        mock_conn = _mock_connection([])
        record = _record()
        scraper_uuid = record["id"]

        with patch("db.mysql.connector.connect", return_value=mock_conn):
            insert_speakers(_CFG, [record], start_id=381)

        cursor = mock_conn.cursor.return_value
        row = cursor.executemany.call_args[0][1][0]
        assert scraper_uuid not in row

    def test_empty_records_skips_db(self):
        mock_conn = _mock_connection([])

        with patch("db.mysql.connector.connect", return_value=mock_conn):
            insert_speakers(_CFG, [], start_id=381)

        mock_conn.cursor.assert_not_called()
