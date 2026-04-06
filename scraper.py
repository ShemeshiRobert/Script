import uuid
import logging
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    )
}

logger = logging.getLogger(__name__)


def fetch_page(url: str) -> BeautifulSoup:
    """Fetch *url* and return a parsed BeautifulSoup tree.

    Raises requests.HTTPError on non-2xx responses.
    """
    response = requests.get(url, headers=_HEADERS, timeout=30)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def _collapse(text: str) -> str:
    return " ".join(text.split())


def _card_to_record(card: Tag, selectors: dict[str, str], base_url: str) -> dict[str, str] | None:
    """Build a speaker record from a single card element.

    Returns None for cards that lack both a name and a photo — those are
    layout artefacts (e.g. empty grid slots), not real speakers.
    """
    img_tag = card.select_one(selectors["photo"])
    name_tag = card.select_one(selectors["name"])
    designation_tag = card.select_one(selectors["designation"])
    bio_tag = card.select_one(selectors["bio"])

    name = _collapse(name_tag.get_text()) if name_tag else ""
    # Tag.get() returns str | list[str] | None; src is always a plain string attribute.
    src = img_tag.get("src") if img_tag else None
    photo_url = src if isinstance(src, str) else ""

    if not name and not photo_url:
        return None

    if photo_url and base_url:
        photo_url = urljoin(base_url, photo_url)

    return {
        "id": uuid.uuid4().hex,
        "name": name,
        "email": "",
        "description": _collapse(designation_tag.get_text()) if designation_tag else "",
        "photoUrl": photo_url,
        "Bio": _collapse(bio_tag.get_text()) if bio_tag else "",
    }


def parse_speakers(soup: BeautifulSoup, selectors: dict[str, str], base_url: str = "") -> list[dict[str, str]]:
    """Extract speaker records from *soup* using CSS *selectors*."""
    cards = soup.select(selectors["card"])
    logger.info("Found %d speaker cards", len(cards))
    return [r for card in cards if (r := _card_to_record(card, selectors, base_url))]
