import csv
from pathlib import Path

import pytest

from config import OUTPUT_CSV, SELECTORS, TARGET_URL
from exporter import write_csv
from scraper import fetch_page, parse_speakers


@pytest.mark.integration
def test_full_pipeline_writes_csv():
    soup = fetch_page(TARGET_URL)
    records = parse_speakers(soup, SELECTORS, base_url=TARGET_URL)

    assert len(records) > 0, "No speakers parsed — selectors may be broken"

    write_csv(records, OUTPUT_CSV)

    out = Path(OUTPUT_CSV)
    assert out.exists()

    with out.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    assert len(rows) == len(records)

    first = rows[0]
    assert first["name"], "First record missing name"
    assert first["photoUrl"], "First record missing photoUrl"
    assert first["id"], "First record missing id"
