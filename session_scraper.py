from bs4 import BeautifulSoup


def parse_sessions(soup: BeautifulSoup, start_id: int) -> list[dict[str, str | int]]:
    """Extract id + title + description from every .cBlockAbstract in the page."""
    records: list[dict[str, str | int]] = []
    for i, block in enumerate(soup.select(".cBlockAbstract")):
        abstract = block.select_one(".PoPAbstract")
        if not abstract:
            continue
        description = abstract.decode_contents().strip()
        if not description:
            continue
        h3 = block.select_one("h3")
        title = " ".join(h3.get_text().split()) if h3 else ""
        records.append({"id": start_id + i, "title": title, "description": description})
    return records
