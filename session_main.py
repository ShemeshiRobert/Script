import logging
import sys

from config import LAST_SESSION_ID, SESSION_OUTPUT_CSV, TARGET_URL
from scraper import fetch_page
from session_exporter import write_sessions_csv
from session_scraper import parse_sessions

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    soup = fetch_page(TARGET_URL)
    records = parse_sessions(soup, start_id=LAST_SESSION_ID + 1)
    if not records:
        logger.warning("No session descriptions found — check .PoPAbstract selectors")
        sys.exit(1)
    write_sessions_csv(records, SESSION_OUTPUT_CSV)
    logger.info("Done. %d session(s) → %s", len(records), SESSION_OUTPUT_CSV)


if __name__ == "__main__":
    main()
