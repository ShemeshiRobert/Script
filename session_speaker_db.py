import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Iterator, cast

import mysql.connector
from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection

from config import DbConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SessionSpeakerTriple:
    id: int
    session_id: int
    speaker_id: int


@contextmanager
def _connection(cfg: DbConfig) -> Iterator[PooledMySQLConnection | MySQLConnectionAbstract]:
    conn = mysql.connector.connect(
        host=cfg.host,
        database=cfg.database,
        user=cfg.user,
        password=cfg.password,
    )
    try:
        yield conn
    finally:
        conn.close()


def _fetch_id_map(cfg: DbConfig, table: str, column: str) -> dict[str, int]:
    """Return a casefolded value → id map from any table/column pair.

    When a value appears more than once, the highest id wins (rows ordered ascending,
    last write per key is always the highest-id row).
    """
    with _connection(cfg) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT id, {column} FROM {table} ORDER BY id")  # noqa: S608
        result: dict[str, int] = {}
        for row_id, value in cursor.fetchall():
            if not value:
                continue
            key = " ".join(str(value).split()).casefold()
            result[key] = cast(int, row_id)
        return result


def fetch_title_to_session_id(cfg: DbConfig) -> dict[str, int]:
    return _fetch_id_map(cfg, "session", "title")


def fetch_name_to_speaker_id(cfg: DbConfig) -> dict[str, int]:
    return _fetch_id_map(cfg, "speaker", "name")


def build_triples(
    sessions: list[dict[str, Any]],
    title_to_session_id: dict[str, int],
    name_to_speaker_id: dict[str, int],
    start_id: int,
) -> list[SessionSpeakerTriple]:
    """Convert the JSON-derived session list into (id, session_id, speaker_id) triples.

    Auto-incrementing id starts at start_id + 1. Logs and skips any title or
    speaker name not found in the DB maps.
    """
    triples: list[SessionSpeakerTriple] = []
    counter = start_id

    for session in sessions:
        title: str = session.get("title", "")
        session_key = " ".join(title.split()).casefold()
        session_id = title_to_session_id.get(session_key)
        if session_id is None:
            logger.warning("Session not found in DB, skipping: %r", title)
            continue

        speakers: list[dict[str, str]] = session.get("speakers", [])
        for speaker in speakers:
            name: str = speaker.get("name", "")
            speaker_key = " ".join(name.split()).casefold()
            speaker_id = name_to_speaker_id.get(speaker_key)
            if speaker_id is None:
                logger.warning("Speaker not found in DB, skipping: %r", name)
                continue

            counter += 1
            triples.append(SessionSpeakerTriple(id=counter, session_id=session_id, speaker_id=speaker_id))

    return triples


def _fetch_existing_pairs(cfg: DbConfig) -> dict[tuple[int, int], int]:
    """Return a (session_id, speaker_id) → row_id map for every row in sessionspeaker."""
    with _connection(cfg) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, sessionid, speakerid FROM sessionspeaker")
        return {
            (cast(int, session_id), cast(int, speaker_id)): cast(int, row_id)
            for row_id, session_id, speaker_id in cursor.fetchall()
        }


def _insert_pair(cfg: DbConfig, triple: SessionSpeakerTriple) -> None:
    with _connection(cfg) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessionspeaker (id, sessionid, speakerid) VALUES (%s, %s, %s)",
            (triple.id, triple.session_id, triple.speaker_id),
        )
        conn.commit()


def _delete_pair(cfg: DbConfig, row_id: int, session_id: int, speaker_id: int) -> None:
    with _connection(cfg) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessionspeaker WHERE id = %s", (row_id,))
        conn.commit()
    logger.info(
        "Deleted stale row from sessionspeaker (id=%d, sessionid=%d, speakerid=%d)",
        row_id, session_id, speaker_id,
    )


def reconcile_session_speakers(
    triples: list[SessionSpeakerTriple],
    cfg: DbConfig,
) -> None:
    """Sync the sessionspeaker table to exactly match the JSON-derived triples.

    - (session_id, speaker_id) in DB but not in triples → delete row, log deletion
    - (session_id, speaker_id) in triples but not in DB → insert row
    - (session_id, speaker_id) present in both → skip
    """
    existing = _fetch_existing_pairs(cfg)
    desired: set[tuple[int, int]] = {(t.session_id, t.speaker_id) for t in triples}

    for (session_id, speaker_id), row_id in existing.items():
        if (session_id, speaker_id) not in desired:
            _delete_pair(cfg, row_id, session_id, speaker_id)

    existing_pairs: set[tuple[int, int]] = set(existing.keys())
    for triple in triples:
        pair = (triple.session_id, triple.speaker_id)
        if pair not in existing_pairs:
            _insert_pair(cfg, triple)
            logger.info(
                "Inserted into sessionspeaker (id=%d, sessionid=%d, speakerid=%d)",
                triple.id, triple.session_id, triple.speaker_id,
            )
