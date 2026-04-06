import logging

from config import OUTPUT_CSV, SELECTORS, TARGET_URL
from exporter import write_csv
from scraper import fetch_page, parse_speakers

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    soup = fetch_page(TARGET_URL)
    records = parse_speakers(soup, SELECTORS, base_url=TARGET_URL)
    write_csv(records, OUTPUT_CSV)
    logger.info("Done. %d speakers → %s", len(records), OUTPUT_CSV)


if __name__ == "__main__":
    main()
