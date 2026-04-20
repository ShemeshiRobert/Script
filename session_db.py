import logging
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, cast

import mysql.connector
from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection

from config import DbConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DbSession:
    id: int
    title: str
    description: str


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


def _normalize_title(title: str) -> str:
    return " ".join(title.strip().split()).casefold()


def fetch_existing_sessions(cfg: DbConfig) -> dict[str, DbSession]:
    """Return a normalized-title → DbSession mapping for all rows in the session table.

    If the same title appears more than once, the row with the highest id wins —
    that is the row targeted by any subsequent update.
    """
    with _connection(cfg) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, description FROM session")
        rows = cast(list[tuple[Any, ...]], cursor.fetchall())
        result: dict[str, DbSession] = {}
        for row in rows:
            if not row[1]:
                continue
            key = _normalize_title(str(row[1]))
            session = DbSession(
                id=int(row[0]),
                title=str(row[1]),
                description=str(row[2] or ""),
            )
            existing = result.get(key)
            if existing is None or session.id > existing.id:
                result[key] = session
        return result


def update_session_description(cfg: DbConfig, db_id: int, description: str) -> None:
    """Overwrite description for a session row, targeted by id."""
    with _connection(cfg) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE session SET description = %s WHERE id = %s",
            (description, db_id),
        )
        conn.commit()


def reconcile_sessions(
    records: list[dict[str, str | int]],
    existing: dict[str, DbSession],
    cfg: DbConfig,
) -> list[dict[str, str | int]]:
    """Update matched DB rows and return only unmatched CSV records.

    Matched rows are updated in the DB and excluded from the returned list.
    Unmatched rows pass through unchanged.
    """
    unmatched: list[dict[str, str | int]] = []
    for r in records:
        key = _normalize_title(str(r.get("title", "")))
        db_row = existing.get(key)
        if db_row is None:
            unmatched.append(r)
            continue
        new_desc = str(r.get("description", ""))
        update_session_description(cfg, db_row.id, new_desc)
        logger.info("Updated session description in DB (id=%d, title=%r)", db_row.id, db_row.title)
    return unmatched
