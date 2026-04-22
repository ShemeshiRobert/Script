import json
from pathlib import Path
from typing import Any


def write_session_speakers_json(sessions: list[dict[str, Any]], path: str) -> None:
    """Write the session-speaker list to a JSON file.

    Creates parent directories if they don't exist. Overwrites any existing file.
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"sessions": sessions}, f, indent=4, ensure_ascii=False)


def load_session_speakers_json(path: str) -> list[dict[str, Any]]:
    """Load and return the sessions list from a JSON file written by write_session_speakers_json."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)["sessions"]
