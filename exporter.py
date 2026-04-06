import csv
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_LIMITS: dict[str, int] = {
    "id": 191,
    "name": 191,
    "email": 191,
    "description": 191,
    "photoUrl": 191,
    "Bio": 5000,
}

# Column order must match the DB schema; derived from _LIMITS to avoid two lists to maintain.
_COLUMNS: list[str] = list(_LIMITS.keys())


def _truncate(record: dict[str, str]) -> dict[str, str]:
    return {col: record.get(col, "")[:_LIMITS[col]] for col in _COLUMNS}


def _dedup(records: list[dict[str, str]]) -> list[dict[str, str]]:
    # First occurrence of each photoUrl wins; records with no photo are kept as-is.
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for r in records:
        url = r.get("photoUrl", "")
        if url and url in seen:
            continue
        if url:
            seen.add(url)
        out.append(r)
    return out


def write_csv(records: list[dict[str, str]], path: str) -> None:
    """Write *records* to a CSV at *path*, creating parent directories as needed."""
    unique = _dedup(records)
    if len(unique) < len(records):
        logger.info("Dropped %d duplicate(s) by photoUrl", len(records) - len(unique))

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_COLUMNS)
        writer.writeheader()
        writer.writerows(_truncate(r) for r in unique)

    logger.info("Wrote %d records to %s", len(unique), path)
