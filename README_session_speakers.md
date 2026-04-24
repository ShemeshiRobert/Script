# Session-Speaker Scraper

Scrapes session-to-speaker relationships from a conference agenda page and syncs them with a MySQL `sessionspeaker` table.

## What it does

Fetches the WSO2Con 2026 North America agenda page, extracts each session title and its associated speaker names, then reconciles those pairs against the database — inserting missing rows and deleting stale ones.

Pipeline stages:

1. **Scrape** — HTTP fetch + HTML parse → for each `SessionBlock` element, extracts the session title from its `h3` and speaker names from every `cSpeaker` card inside it
2. **Export** — writes all scraped pairs to `output/session_speakers.json`
3. **Reconcile** — resolves titles and names to DB ids, then syncs the `sessionspeaker` table for rows where `sessionid >= SESSIONSPEAKER_MIN_SESSION_ID`

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
LAST_SESSION_ID=
SESSIONSPEAKER_MIN_SESSION_ID=   # rows with sessionid below this are never touched
```

## Usage

```bash
python session_speaker_main.py
```

The script aborts before any DB changes if the scraper matched nothing, so a broken selector won't wipe the table.

## Configuration

- `TARGET_URL` — the page to scrape (shared with other scrapers, defined in `config.py`)
- `SESSIONSPEAKER_MIN_SESSION_ID` — read from `.env`; only `sessionspeaker` rows at or above this session id are in scope

Database credentials are read from environment variables and validated at startup.

## Reconciliation behaviour

After the run, the `sessionspeaker` table for `sessionid >= SESSIONSPEAKER_MIN_SESSION_ID` exactly matches the scraped pairs:

| Situation | Action |
|---|---|
| Pair in scraped JSON but not in DB | Insert row, log at INFO |
| Pair in DB but not in scraped JSON | Delete row, log at INFO |
| Pair present in both | Skip |
| Session title not found in DB | Log WARNING, skip entire session |
| Speaker name not found in DB | Log WARNING, skip that speaker; other speakers in the same session still processed |

Rows where `sessionid < SESSIONSPEAKER_MIN_SESSION_ID` are never read, compared, inserted, or deleted.

When duplicate titles or names exist in the DB, the row with the highest id wins.

## Output format

`output/session_speakers.json`:

```json
{
    "sessions": [
        {
            "title": "Building Cloud-Native APIs",
            "speakers": [
                {"name": "Jane Smith"},
                {"name": "John Doe"}
            ]
        }
    ]
}
```

## Logging

```
INFO Found 42 element(s) matching [class*='SessionBlock']
INFO Parsed 38 session(s) with speakers
INFO Wrote 38 session(s) to output/session_speakers.json
INFO Built 91 pair(s)
INFO Inserted into sessionspeaker (sessionid=335, speakerid=12)
INFO Deleted stale row from sessionspeaker (id=204, sessionid=340, speakerid=7)
INFO Reconciliation complete
```

## Module layout

| File | Role |
|------|------|
| `session_speaker_scraper.py` | Parses session blocks and speaker cards from HTML |
| `session_speaker_exporter.py` | Writes and reads `output/session_speakers.json` |
| `session_speaker_db.py` | DB lookups, pair building, `sessionspeaker` reconciliation |
| `session_speaker_main.py` | Entry point — wires the pipeline together |
