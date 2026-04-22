import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

SELECTORS: dict[str, str] = {
    "card": "div.row",
    "photo": "div.col-md-2.col-lg-2.cSpeakerSide.pe-0 img",
    "name": "div.col-md-5.col-lg-5.cSpeakerSide.ps-0.pe-0 h4",
    "designation": "div.col-md-5.col-lg-5.cSpeakerSide.ps-0.pe-0 h6",
    "bio": "div.cModelBio",
}

# Panel moderators and some session speakers use a different card structure (div.cSpeaker / h5).
# This selector set runs after SELECTORS; duplicates are dropped by name.
SELECTORS_ALT: dict[str, str] = {
    "card": "div.cSpeaker",
    "photo": "img",
    "name": "h5",
    "designation": "h6",
    "bio": "",
}

TARGET_URL = "https://wso2.com/wso2con/2026/north-america/agenda/"
OUTPUT_CSV = "output/speakers.csv"


@dataclass(frozen=True)
class DbConfig:
    host: str
    database: str
    user: str
    password: str


def _require_env(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


DB_CONFIG = DbConfig(
    host=_require_env("DB_HOST"),
    database=_require_env("DB_NAME"),
    user=_require_env("DB_USER"),
    password=_require_env("DB_PASSWORD"),
)

LAST_SPEAKER_ID = int(_require_env("LAST_SPEAKER_ID"))
LAST_SESSION_ID = int(_require_env("LAST_SESSION_ID"))
SESSIONSPEAKER_START_ID = int(_require_env("SESSIONSPEAKER_START_ID"))

SESSION_OUTPUT_CSV = "output/sessions.csv"

# Used only for lookup-key normalization during reconciliation — not stripped when writing to DB.
# If CSV has 'Nirmal Fernando (Moderator)' and DB has 'Nirmal Fernando', the suffix is added to DB.
MODERATOR_SUFFIX = " (Moderator)"
