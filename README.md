# Speaker Scraper

Scrapes speaker data from a conference agenda page, validates it, syncs with a MySQL database, and exports to CSV.

## What it does

Fetches the WSO2Con 2026 North America agenda page, extracts speaker cards from two different HTML layouts, validates the records, reconciles them against the database, and writes new speakers to `output/speakers.csv`.

Pipeline stages:

1. **Scrape** — HTTP fetch + HTML parse → speaker records extracted using two CSS selector sets (standard cards and moderator/panel cards), deduplicated by name
2. **Validate** — rejects the run if any record is missing `name` or `description`
3. **Reconcile** — compares against existing DB rows by name (case-insensitive, moderator suffix stripped for matching); updates any changed fields including the name itself; when duplicate name rows exist in the DB, targets the one with the highest numeric id
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
LAST_SPEAKER_ID=   # highest speaker id currently in the DB
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
- `SELECTORS` — CSS selectors for the standard speaker card layout (`div.row` / `h4`)
- `SELECTORS_ALT` — CSS selectors for the moderator/panel card layout (`div.cSpeaker` / `h5`); runs after `SELECTORS`, duplicates dropped by name
- `MODERATOR_SUFFIX` — the suffix stripped from names when building DB lookup keys (default `" (Moderator)"`); the suffix is preserved when writing to the DB

Database credentials and `LAST_SPEAKER_ID` are read from environment variables and validated at startup.

## Reconciliation behaviour

For each scraped record the script checks whether a speaker with the same name already exists in the DB (matching is case-insensitive and ignores the moderator suffix):

| Situation | Action |
|---|---|
| Name not in DB | Insert as new speaker, include in CSV |
| Name found, all fields match | Skip — already in sync |
| Name found, any field differs (name, photo, bio, description) | Update the DB row, exclude from CSV |

When the same name appears more than once in the DB (duplicates), the row with the highest numeric id is the one updated.

If a scraped name includes ` (Moderator)` and the DB has the same name without it, the DB row is updated to include the suffix.

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
