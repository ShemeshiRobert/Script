import csv
from pathlib import Path

_SESSION_FIELDS = ["id", "title", "description"]


def write_sessions_csv(records: list[dict[str, str | int]], path: str) -> None:
    """Write session records to a CSV at *path*, creating parent directories as needed."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_SESSION_FIELDS)
        writer.writeheader()
        writer.writerows(records)
