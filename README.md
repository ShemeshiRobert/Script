# Speaker Scraper

Scrapes speaker data from a conference agenda page, validates it, syncs with a MySQL database, and exports to CSV.

## What it does

Fetches the WSO2Con 2026 North America agenda page, extracts speaker cards, validates the records, reconciles them against the database (updating changed fields, skipping duplicates), inserts new speakers with sequential IDs, and writes the final output to `output/speakers.csv`.

Pipeline stages:

1. **Scrape** — HTTP fetch + HTML parse → list of speaker records (name, designation, photo URL, bio)
2. **Validate** — rejects the run if any record is missing required fields
3. **Reconcile** — compares against existing DB rows by name (case-insensitive); updates changed photo/bio, drops exact duplicates
4. **Insert** — new speakers get sequential integer IDs starting from `LAST_SPEAKER_ID + 1`
5. **Export** — deduplicates by photo URL and writes CSV with field length limits

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your values:

```
DB_HOST=
DB_NAME=
DB_USER=
DB_PASSWORD=
LAST_SPEAKER_ID=
```

## Usage

```bash
python main.py
```

Output lands at `output/speakers.csv`.

## Configuration

Edit [config.py](config.py) to point at a different page or change the output path:

- `TARGET_URL` — the page to scrape
- `OUTPUT_CSV` — where to write results
- `SELECTORS` — CSS selectors for card, photo, name, designation, and bio elements

Database credentials and `LAST_SPEAKER_ID` are read from environment variables and validated at startup.

## Output format

| Column | Max length |
|--------|-----------|
| id | 191 |
| name | 191 |
| email | 191 |
| description | 191 |
| photoUrl | 191 |
| Bio | 5000 |

`id` is the sequential integer assigned during DB insert. `email` is always empty (not available on the page).

## Tests

```bash
pytest                        # unit tests only
pytest -m integration         # also hits the live URL
```
