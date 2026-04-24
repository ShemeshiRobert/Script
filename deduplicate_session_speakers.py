import logging
from collections import defaultdict
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, cast

import mysql.connector
from mysql.connector.abstracts import MySQLConnectionAbstract
from mysql.connector.pooling import PooledMySQLConnection

from config import DB_CONFIG, DbConfig

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
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


def _fetch_all_pairs(cfg: DbConfig) -> list[tuple[int, int, str]]:
    with _connection(cfg) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, sessionid, speakerid FROM sessionspeaker ORDER BY id")
        rows = cast(list[tuple[Any, ...]], cursor.fetchall())
        return [(cast(int, row[0]), cast(int, row[1]), str(row[2])) for row in rows]


def _delete_row(cfg: DbConfig, row_id: int, session_id: int, speaker_id: str) -> None:
    with _connection(cfg) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessionspeaker WHERE id = %s", (row_id,))
        conn.commit()
    logger.info("Deleted duplicate row (id=%d, sessionid=%d, speakerid=%s)", row_id, session_id, speaker_id)


def deduplicate() -> None:
    rows = _fetch_all_pairs(DB_CONFIG)

    # group row ids by (sessionid, speakerid); rows are ordered by id ascending so we keep the lowest
    groups: dict[tuple[int, str], list[int]] = defaultdict(list)
    for row_id, session_id, speaker_id in rows:
        groups[(session_id, speaker_id)].append(row_id)

    duplicates_found = False
    for (session_id, speaker_id), ids in groups.items():
        if len(ids) <= 1:
            continue
        duplicates_found = True
        keep, *to_delete = ids
        logger.info(
            "Duplicate pair (sessionid=%d, speakerid=%s): keeping id=%d, deleting %s",
            session_id, speaker_id, keep, to_delete,
        )
        for row_id in to_delete:
            _delete_row(cfg=DB_CONFIG, row_id=row_id, session_id=session_id, speaker_id=speaker_id)

    if not duplicates_found:
        logger.info("No duplicates found in sessionspeaker")


if __name__ == "__main__":
    deduplicate()
