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


def load_local_page(path: str) -> BeautifulSoup:
    """Read a local HTML file and return a parsed BeautifulSoup tree.

    Raises FileNotFoundError if path does not exist.
    """
    with open(path, encoding="utf-8") as f:
        return BeautifulSoup(f.read(), "html.parser")


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
    # bio selector is optional — some card structures have no bio block
    bio_sel = selectors.get("bio", "")
    bio_tag = card.select_one(bio_sel) if bio_sel else None

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


def parse_speakers(
    soup: BeautifulSoup,
    selector_sets: list[dict[str, str]],
    base_url: str = "",
) -> list[dict[str, str]]:
    """Extract speaker records from *soup* using each set of CSS selectors.

    Runs all selector sets in order and deduplicates by name — if the same
    speaker appears under multiple card structures, the first occurrence wins.
    """
    seen: set[str] = set()
    results: list[dict[str, str]] = []
    for selectors in selector_sets:
        cards = soup.select(selectors["card"])
        logger.info("Found %d cards with selector %r", len(cards), selectors["card"])
        for card in cards:
            r = _card_to_record(card, selectors, base_url)
            if r and r["name"] not in seen:
                seen.add(r["name"])
                results.append(r)
    return results
