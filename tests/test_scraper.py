import textwrap
from unittest.mock import MagicMock, patch

import pytest
import requests
from bs4 import BeautifulSoup

from scraper import _collapse, fetch_page, parse_speakers  # type: ignore[reportPrivateUsage]

SELECTORS = {
    "card": "div.row",
    "photo": "div.col-md-2.col-lg-2.cSpeakerSide.pe-0 img",
    "name": "div.col-md-5.col-lg-5.cSpeakerSide.ps-0.pe-0 h4",
    "designation": "div.col-md-5.col-lg-5.cSpeakerSide.ps-0.pe-0 h6",
    "bio": "div.cModelBio",
}


def _make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(textwrap.dedent(html), "html.parser")


def _speaker_row(
    *,
    img_src: str = "/img/alice.jpg",
    name: str = "Alice Smith",
    designation: str = "CTO, Acme Corp",
    bio: str = "",
) -> str:
    bio_div = f'<div class="cModelBio">{bio}</div>' if bio else ""
    return f"""\
        <div class="row">
            <div class="col-md-2 col-lg-2 cSpeakerSide pe-0">
                <img src="{img_src}">
            </div>
            <div class="col-md-5 col-lg-5 cSpeakerSide ps-0 pe-0">
                <h4>{name}</h4>
                <h6>{designation}</h6>
            </div>
            {bio_div}
        </div>
    """


# --- _collapse ---

def test_collapse_normalizes_internal_whitespace():
    assert _collapse("  hello   world  ") == "hello world"


def test_collapse_handles_newlines_and_tabs():
    assert _collapse("Jane\n  Doe\t") == "Jane Doe"


def test_collapse_empty_string():
    assert _collapse("") == ""


# --- parse_speakers ---

class TestParseSpeakers:
    def test_extracts_all_fields(self):
        soup = _make_soup(_speaker_row(bio="Alice has 20 years of experience."))
        records = parse_speakers(soup, SELECTORS, base_url="https://example.com")

        assert len(records) == 1
        r = records[0]
        assert r["name"] == "Alice Smith"
        assert r["description"] == "CTO, Acme Corp"
        assert r["Bio"] == "Alice has 20 years of experience."
        assert r["photoUrl"] == "https://example.com/img/alice.jpg"
        assert r["email"] == ""
        assert len(r["id"]) == 32  # uuid4 hex

    def test_each_record_gets_unique_id(self):
        html = (
            _speaker_row(img_src="/a.jpg", name="Alice", designation="Dev")
            + _speaker_row(img_src="/b.jpg", name="Bob", designation="PM")
        )
        records = parse_speakers(_make_soup(html), SELECTORS)
        assert records[0]["id"] != records[1]["id"]

    def test_skips_card_with_no_name_and_no_photo(self):
        # A bare div.row with no matching inner divs is a layout artefact, not a speaker.
        soup = _make_soup('<div class="row"><h6>Some text</h6></div>')
        assert parse_speakers(soup, SELECTORS) == []

    def test_keeps_card_with_name_but_no_photo(self):
        soup = _make_soup("""\
            <div class="row">
                <div class="col-md-5 col-lg-5 cSpeakerSide ps-0 pe-0"><h4>Bob</h4></div>
            </div>
        """)
        records = parse_speakers(soup, SELECTORS)
        assert len(records) == 1
        assert records[0]["photoUrl"] == ""

    def test_keeps_card_with_photo_but_no_name(self):
        soup = _make_soup("""\
            <div class="row">
                <div class="col-md-2 col-lg-2 cSpeakerSide pe-0"><img src="/x.jpg"></div>
            </div>
        """)
        records = parse_speakers(soup, SELECTORS)
        assert len(records) == 1
        assert records[0]["name"] == ""

    def test_resolves_relative_photo_url(self):
        soup = _make_soup(_speaker_row(img_src="/images/speaker.png", name="Carol"))
        records = parse_speakers(soup, SELECTORS, base_url="https://conf.example.org")
        assert records[0]["photoUrl"] == "https://conf.example.org/images/speaker.png"

    def test_leaves_absolute_photo_url_unchanged(self):
        soup = _make_soup(
            _speaker_row(img_src="https://cdn.example.com/speaker.jpg", name="Dave")
        )
        records = parse_speakers(soup, SELECTORS, base_url="https://conf.example.org")
        assert records[0]["photoUrl"] == "https://cdn.example.com/speaker.jpg"

    def test_collapses_whitespace_in_name(self):
        soup = _make_soup(_speaker_row(name="  Eve   Jones  "))
        assert parse_speakers(soup, SELECTORS)[0]["name"] == "Eve Jones"

    def test_empty_page_returns_empty_list(self):
        soup = _make_soup("<html><body></body></html>")
        assert parse_speakers(soup, SELECTORS) == []

    def test_missing_optional_bio_and_designation(self):
        soup = _make_soup("""\
            <div class="row">
                <div class="col-md-2 col-lg-2 cSpeakerSide pe-0"><img src="/f.jpg"></div>
                <div class="col-md-5 col-lg-5 cSpeakerSide ps-0 pe-0"><h4>Frank</h4></div>
            </div>
        """)
        r = parse_speakers(soup, SELECTORS)[0]
        assert r["description"] == ""
        assert r["Bio"] == ""


# --- fetch_page ---

class TestFetchPage:
    def test_returns_beautifulsoup_on_success(self):
        mock_response = MagicMock()
        mock_response.text = "<html><body><p>Hello</p></body></html>"
        mock_response.raise_for_status = MagicMock()

        with patch("scraper.requests.get", return_value=mock_response):
            soup = fetch_page("https://example.com")

        assert soup.find("p").text == "Hello"  # type: ignore[union-attr]

    def test_raises_on_http_error(self):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404")

        with patch("scraper.requests.get", return_value=mock_response):
            with pytest.raises(requests.HTTPError):
                fetch_page("https://example.com/missing")
