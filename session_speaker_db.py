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
class SessionSpeakerPair:
    session_id: int
    speaker_id: str  # VARCHAR in sessionspeaker, matches speaker.id type


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


def fetch_title_to_session_id(cfg: DbConfig) -> dict[str, int]:
    """Return a casefolded title → session id (INT) map.

    session.id is VARCHAR but contains numeric strings. Converted to int
    here because sessionspeaker.sessionid is INT.
    When a title appears more than once, the highest id wins.
    """
    with _connection(cfg) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title FROM session ORDER BY id")
        result: dict[str, int] = {}
        for row_id, title in cursor.fetchall():
            if not title:
                continue
            key = " ".join(str(title).split()).casefold()
            result[key] = int(str(row_id))
        return result


def fetch_name_to_speaker_id(cfg: DbConfig) -> dict[str, str]:
    """Return a casefolded name → speaker id (VARCHAR) map.

    When a name appears more than once, the highest id wins.
    """
    with _connection(cfg) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM speaker ORDER BY id")
        result: dict[str, str] = {}
        for row_id, name in cursor.fetchall():
            if not name:
                continue
            key = " ".join(str(name).split()).casefold()
            result[key] = str(row_id)
        return result


def build_pairs(
    sessions: list[dict[str, Any]],
    title_to_session_id: dict[str, int],
    name_to_speaker_id: dict[str, str],
    min_session_id: int,
) -> list[SessionSpeakerPair]:
    """Convert the JSON-derived session list into (session_id, speaker_id) pairs.

    Sessions whose resolved id is below min_session_id are silently ignored.
    Logs and skips any title or speaker name not found in the DB maps.
    """
    pairs: list[SessionSpeakerPair] = []

    for session in sessions:
        title: str = session.get("title", "")
        session_key = " ".join(title.split()).casefold()
        session_id = title_to_session_id.get(session_key)
        if session_id is None:
            logger.warning("Session not found in DB, skipping: %r", title)
            continue
        if session_id < min_session_id:
            continue

        speakers: list[dict[str, str]] = session.get("speakers", [])
        for speaker in speakers:
            name: str = speaker.get("name", "")
            speaker_key = " ".join(name.split()).casefold()
            speaker_id = name_to_speaker_id.get(speaker_key)
            if speaker_id is None:
                logger.warning("Speaker not found in DB, skipping: %r", name)
                continue

            pairs.append(SessionSpeakerPair(session_id=session_id, speaker_id=speaker_id))

    return pairs


def _fetch_existing_pairs(cfg: DbConfig, min_session_id: int) -> dict[tuple[int, str], int]:
    """Return a (session_id, speaker_id) → row_id map for rows where sessionid >= min_session_id.

    Rows below the threshold are never fetched — invisible to reconciliation.
    """
    with _connection(cfg) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, sessionid, speakerid FROM sessionspeaker WHERE sessionid >= %s",
            (min_session_id,),
        )
        return {
            (cast(int, session_id), str(speaker_id)): cast(int, row_id)
            for row_id, session_id, speaker_id in cursor.fetchall()
        }


def _insert_pair(cfg: DbConfig, pair: SessionSpeakerPair) -> None:
    # id is auto-increment — omitted from INSERT, DB assigns it
    with _connection(cfg) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO sessionspeaker (sessionid, speakerid) VALUES (%s, %s)",
            (pair.session_id, pair.speaker_id),
        )
        conn.commit()


def _delete_pair(cfg: DbConfig, row_id: int, session_id: int, speaker_id: str) -> None:
    with _connection(cfg) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessionspeaker WHERE id = %s", (row_id,))
        conn.commit()
    logger.info(
        "Deleted stale row from sessionspeaker (id=%d, sessionid=%d, speakerid=%s)",
        row_id, session_id, speaker_id,
    )


def reconcile_session_speakers(
    pairs: list[SessionSpeakerPair],
    cfg: DbConfig,
    min_session_id: int,
) -> None:
    """Sync sessionspeaker rows for sessionid >= min_session_id to match pairs.

    - (session_id, speaker_id) in DB but not in pairs → delete row, log deletion
    - (session_id, speaker_id) in pairs but not in DB → insert row
    - (session_id, speaker_id) present in both → skip
    Rows with sessionid < min_session_id are never touched.
    """
    existing = _fetch_existing_pairs(cfg, min_session_id)
    desired: set[tuple[int, str]] = {(p.session_id, p.speaker_id) for p in pairs}

    for (session_id, speaker_id), row_id in existing.items():
        if (session_id, speaker_id) not in desired:
            _delete_pair(cfg, row_id, session_id, speaker_id)

    existing_keys: set[tuple[int, str]] = set(existing.keys())
    for pair in pairs:
        key = (pair.session_id, pair.speaker_id)
        if key not in existing_keys:
            _insert_pair(cfg, pair)
            logger.info(
                "Inserted into sessionspeaker (sessionid=%d, speakerid=%s)",
                pair.session_id, pair.speaker_id,
            )
