# Web Scraper Script

Scrapes speaker data from a conference agenda page and exports it to CSV for database import.

## What it does

Fetches the WSO2Con 2026 North America agenda page, extracts speaker cards (name, designation, photo URL, bio), deduplicates by photo URL, and writes the result to `output/speakers.csv`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
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

## Output format

| Column | Max length |
|--------|-----------|
| id | 191 |
| name | 191 |
| email | 191 |
| description | 191 |
| photoUrl | 191 |
| Bio | 5000 |

`id` is a random UUID hex generated per run. `email` is always empty (not available on the page).

## Tests

```bash
pytest
```
