import logging
import sys

from config import DB_CONFIG, LAST_SPEAKER_ID, OUTPUT_CSV, SELECTORS, SELECTORS_ALT, TARGET_URL
from db import fetch_existing_speakers, insert_speakers, reconcile_speakers
from exporter import dedup_records, write_csv
from scraper import fetch_page, parse_speakers
from validator import validate_records

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    soup = fetch_page(TARGET_URL)
    records = parse_speakers(soup, [SELECTORS, SELECTORS_ALT], base_url=TARGET_URL)

    errors = validate_records(records)
    if errors:
        for e in errors:
            logger.error("Row %d — %s: %s", e.row, e.field, e.reason)
        sys.exit(1)

    existing = fetch_existing_speakers(DB_CONFIG)
    records = dedup_records(reconcile_speakers(records, existing, DB_CONFIG))
    insert_speakers(DB_CONFIG, records, start_id=LAST_SPEAKER_ID + 1)

    write_csv(records, OUTPUT_CSV)
    logger.info("Done. %d new speaker(s) → %s", len(records), OUTPUT_CSV)


if __name__ == "__main__":
    main()
