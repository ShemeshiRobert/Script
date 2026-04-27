import argparse
import logging

from config import DB_CONFIG, SESSIONSPEAKER_MIN_SESSION_ID, TARGET_URL
from scraper import fetch_page, load_local_page
from session_speaker_db import (
    build_pairs,
    fetch_name_to_speaker_id,
    fetch_title_to_session_id,
    reconcile_session_speakers,
)
from session_speaker_exporter import write_session_speakers_json
from session_speaker_scraper import parse_session_speakers

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SESSION_SPEAKERS_JSON = "output/session_speakers.json"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape session-speaker pairs and sync to DB.")
    parser.add_argument(
        "--local",
        metavar="FILE",
        help="Path to a local HTML file to scrape instead of fetching the live URL.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.local:
        logger.info("Loading local HTML from %s", args.local)
        soup = load_local_page(args.local)
    else:
        logger.info("Fetching %s", TARGET_URL)
        soup = fetch_page(TARGET_URL)
    sessions = parse_session_speakers(soup)
    write_session_speakers_json(sessions, SESSION_SPEAKERS_JSON)
    logger.info("Wrote %d session(s) to %s", len(sessions), SESSION_SPEAKERS_JSON)

    if not sessions:
        raise SystemExit("No sessions scraped — selector matched nothing. Aborting before DB changes.")

    title_map = fetch_title_to_session_id(DB_CONFIG)
    speaker_map = fetch_name_to_speaker_id(DB_CONFIG)
    pairs = build_pairs(sessions, title_map, speaker_map, SESSIONSPEAKER_MIN_SESSION_ID)
    logger.info("Built %d pair(s)", len(pairs))

    reconcile_session_speakers(pairs, DB_CONFIG, SESSIONSPEAKER_MIN_SESSION_ID)
    logger.info("Reconciliation complete")


if __name__ == "__main__":
    main()
