# Event Desk

A small FastAPI app for triaging a bar's inbound event inquiries. It has no database
or authentication; triaged records are stored in `inbox.json`.

## Run locally

1. Install dependencies with `python -m pip install -r requirements.txt`.
2. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`.
3. Add game dates to `game_days.csv` using ISO dates, for example `2026-11-14,Home game`.
4. Add the bar's real policies and event details to `business.md`.
5. Start the app with `uvicorn main:app --reload` and open http://127.0.0.1:8000.

The `high_demand_date` flag is computed by the server by matching dates explicitly
mentioned in each message against the `date` column in `game_days.csv`. The model
receives that flag but does not determine it.