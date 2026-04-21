# Session Scraper

Scrapes session titles and descriptions from a conference agenda page, syncs descriptions with a MySQL database, and exports unmatched sessions to CSV.

## What it does

Fetches the WSO2Con 2026 North America agenda page, extracts session abstracts from modal blocks, reconciles them against the database, and writes unmatched sessions to `output/sessions.csv`.

Pipeline stages:

1. **Scrape** — HTTP fetch + HTML parse → session records extracted from every `.cBlockAbstract` modal block; blocks with no `.PoPAbstract` content are skipped
2. **Export** — writes all scraped sessions to `output/sessions.csv` (id, title, description)
3. **Reconcile** — compares each CSV row against the `session` table by title (case-insensitive, whitespace-normalised); updates the DB description for any match and removes that row from the CSV; when duplicate titles exist in the DB, targets the row with the highest id
4. **Rewrite** — overwrites `output/sessions.csv` with only the rows that had no DB match

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
LAST_SESSION_ID=   # highest session id currently in the DB
```

## Usage

```bash
python session_main.py
```

Output lands at `output/sessions.csv`. Only sessions whose title was not found in the DB are written there.

## Configuration

Edit [config.py](config.py) to change the target URL or output path:

- `TARGET_URL` — the page to scrape (shared with the speaker scraper)
- `SESSION_OUTPUT_CSV` — where to write results (default `output/sessions.csv`)
- `LAST_SESSION_ID` — read from `.env`; the id counter starts at `LAST_SESSION_ID + 1`

Database credentials are read from environment variables and validated at startup.

## Reconciliation behaviour

For each scraped session the script checks whether a session with the same title already exists in the DB (matching is case-insensitive and collapses whitespace):

| Situation | Action |
|---|---|
| Title not in DB | Leave in CSV untouched |
| Title found in DB | Overwrite DB description with scraped value, remove row from CSV, log the change |

When the same title appears more than once in the DB (duplicates), the row with the highest id is the one updated.

## Output format

`output/sessions.csv` — rows remaining after reconciliation:

| Column | Notes |
|--------|-------|
| id | Sequential integer starting from `LAST_SESSION_ID + 1` |
| title | Collapsed whitespace, sourced from the `h3` inside `.cBlockAbstract` |
| description | Raw inner HTML of `.PoPAbstract`, whitespace-trimmed |

If all scraped sessions matched DB records, the file is rewritten with a header row only.

## Logging

Every DB update logs at `INFO`:

```
INFO Updated session description in DB (id=42, title='Building Cloud-Native APIs')
INFO Reconciliation complete. 3 unmatched session(s) remain in output/sessions.csv
```
