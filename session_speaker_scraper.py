import logging
from typing import Any

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def parse_session_speakers(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """Extract session titles with their associated speaker names from sessionBlock elements.

    Returns a list of dicts matching the JSON output schema:
        [{"title": "...", "speakers": [{"name": "..."}, ...]}, ...]

    Skips blocks with no title or no speakers. Deduplicates speaker names within
    a block — first occurrence wins if the same name appears twice.
    """
    all_blocks = soup.select("[class*='SessionBlock']")
    logger.info("Found %d element(s) matching [class*='SessionBlock']", len(all_blocks))

    sessions: list[dict[str, Any]] = []
    for block in all_blocks:
        h3 = block.select_one("h3")
        if not h3:
            continue
        # <br> tags produce a \n when get_text uses a separator; take the last
        # non-empty segment so subtitles/session-type prefixes above the <br> are dropped.
        parts = [p.strip() for p in h3.get_text(separator="\n").split("\n") if p.strip()]
        title = parts[-1] if parts else ""
        if not title:
            continue

        seen_names: set[str] = set()
        speakers: list[dict[str, str]] = []

        speaker_cards = block.select("[class*='cSpeaker']")
        logger.debug("Block %r — %d cSpeaker card(s) found", title, len(speaker_cards))
        for card in speaker_cards:
            tag = card.select_one("h5")
            if not tag:
                continue
            name = " ".join(tag.get_text().split())
            if name and name not in seen_names:
                seen_names.add(name)
                speakers.append({"name": name})

        if not speakers:
            continue
        sessions.append({"title": title, "speakers": speakers})

    logger.info("Parsed %d session(s) with speakers", len(sessions))
    return sessions
