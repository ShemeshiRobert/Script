import logging
from typing import Any

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def parse_session_speakers(soup: BeautifulSoup) -> list[dict[str, Any]]:
    """Extract session titles with their associated speaker names from modal elements.

    Returns a list of dicts matching the JSON output schema:
        [{"title": "...", "speakers": [{"name": "..."}, ...]}, ...]

    Skips modals with no title or no speakers. Deduplicates speaker names within
    a session — first occurrence wins if the same name appears twice in a modal.
    """
    sessions: list[dict[str, Any]] = []
    for modal in soup.select("div.modal"):
        block = modal.select_one(".cBlockAbstract")
        if not block:
            continue
        h3 = block.select_one("h3")
        if not h3:
            continue
        title = " ".join(h3.get_text().split())
        if not title:
            continue

        seen_names: set[str] = set()
        speakers: list[dict[str, str]] = []

        # Structure A: regular speaker cards (div.row); Structure B: panel moderators (div.cSpeaker)
        for card_sel, name_sel in (
            ("div.row", "div.col-md-5.col-lg-5.cSpeakerSide.ps-0.pe-0 h4"),
            ("div.cSpeaker", "h5"),
        ):
            for card in modal.select(card_sel):
                tag = card.select_one(name_sel)
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
