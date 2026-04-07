import logging
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, cast

import mysql.connector
from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection

from config import DbConfig

logger = logging.getLogger(__name__)


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


def fetch_existing_photo_urls(cfg: DbConfig) -> set[str]:
    """Return the set of all photoUrls currently in the speaker table."""
    with _connection(cfg) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT photoUrl FROM speaker")
        # cast because the default (non-dict) cursor returns tuples; Pylance sees a broader union
        rows = cast(list[tuple[Any, ...]], cursor.fetchall())
        return {str(row[0]) for row in rows if row[0]}


def filter_new_speakers(
    records: list[dict[str, str]],
    existing_photo_urls: set[str],
) -> list[dict[str, str]]:
    """Remove records whose photoUrl already exists in the DB.

    Pure function — takes the URL set as an argument so it's testable without a live DB.
    """
    kept = [r for r in records if r.get("photoUrl", "") not in existing_photo_urls]
    skipped = len(records) - len(kept)
    if skipped:
        logger.info("Skipped %d speaker(s) already in DB", skipped)
    return kept
