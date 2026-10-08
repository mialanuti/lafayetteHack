# Event Desk

A small FastAPI app for triaging a bar's inbound event inquiries. It has no database
or authentication; triaged records are stored in `inbox.json`.

## Run locally

1. Install dependencies with `python -m pip install -r requirements.txt`.
2. Copy `.env.example` to `.env` and set `GEMINI_API_KEY`. Gemini is selected automatically when it is the only configured provider; you can also set `AI_PROVIDER=gemini` and `GEMINI_MODEL=gemini-3.8-flash` explicitly. OpenAI remains available with `AI_PROVIDER=openai` and `OPENAI_API_KEY`.
3. Refresh UNC football and basketball home games with `python sync_game_days.py`.
4. Add the bar's real policies and event details to `business.md`.
5. Start the app with `uvicorn main:app --reload` and open http://127.0.0.1:8000.

The `high_demand_date` flag is computed by the server by matching dates explicitly
mentioned in each message against the `date` column in `game_days.csv`. The model
receives that flag but does not determine it.

The sync script reads UNC's public schedule tables, keeps only home games in Chapel
Hill, and writes upcoming dates to `game_days.csv`. It uses only Python's standard
library and needs no API key. The GitHub Actions workflow refreshes the file daily
and can also be run manually from the Actions tab. Scheduled runs require the
workflow to be on the repository's default branch with Actions enabled and write
access to repository contents.