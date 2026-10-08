import argparse
import csv
import re
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = ROOT / "game_days.csv"
SPORTS = (
    ("football", "Football"),
    ("mens-basketball", "Men's basketball"),
    ("womens-basketball", "Women's basketball"),
)
SCHEDULE_BASE_URL = "https://goheels.com/sports/{sport}/schedule/text/{season}"


class ScheduleTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self.current_row: list[str] | None = None
        self.current_cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr":
            self.current_row = []
        elif tag in {"td", "th"} and self.current_row is not None:
            self.current_cell = []

    def handle_data(self, data: str) -> None:
        if self.current_cell is not None:
            self.current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self.current_cell is not None:
            cell_text = " ".join("".join(self.current_cell).split())
            if self.current_row is not None:
                self.current_row.append(cell_text)
            self.current_cell = None
        elif tag == "tr" and self.current_row is not None:
            if self.current_row:
                self.rows.append(self.current_row)
            self.current_row = None


def parse_schedule(
    html: str,
    sport: str,
    season_start_year: int,
) -> list[tuple[date, str]]:
    parser = ScheduleTableParser()
    parser.feed(html)
    games = []

    for row in parser.rows:
        if len(row) < 5 or row[2].strip().lower() != "home":
            continue
        if "chapel hill" not in row[4].lower():
            continue

        date_match = re.match(r"([A-Za-z]{3})\s+(\d{1,2})\b", row[0].strip())
        if date_match is None:
            continue
        month = datetime.strptime(date_match.group(1), "%b").month
        year = season_start_year
        if sport != "football" and month <= 3:
            year += 1
        game_date = datetime.strptime(
            f"{date_match.group(1)} {date_match.group(2)} {year}", "%b %d %Y"
        ).date()
        games.append((game_date, f"{sport} vs {row[3].strip()}"))

    return games


def fetch_schedule(sport: str, season: int) -> str:
    url = SCHEDULE_BASE_URL.format(sport=sport, season=season)
    request = Request(url, headers={"User-Agent": "EventDeskGameDaySync/1.0"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def season_for_sport(sport: str, today: date) -> int:
    if sport == "football" or today.month >= 8:
        return today.year
    return today.year - 1


def collect_upcoming_games(today: date) -> list[tuple[date, str]]:
    games = []
    for sport_slug, sport_name in SPORTS:
        season = season_for_sport(sport_slug, today)
        html = fetch_schedule(sport_slug, season)
        sport_games = parse_schedule(html, sport_name, season)
        if not sport_games:
            raise RuntimeError(f"No Chapel Hill home games found for {sport_name}")
        games.extend(game for game in sport_games if game[0] >= today)
    return sorted(games)


def write_csv(games: list[tuple[date, str]], output_path: Path = OUTPUT_PATH) -> None:
    temporary_path = output_path.with_suffix(".csv.tmp")
    with temporary_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.writer(output_file)
        writer.writerow(("date", "event"))
        writer.writerows((game_date.isoformat(), event) for game_date, event in games)
    temporary_path.replace(output_path)


def main() -> None:
    argument_parser = argparse.ArgumentParser(description="Refresh UNC Chapel Hill home game dates.")
    argument_parser.add_argument(
        "--today",
        type=date.fromisoformat,
        default=date.today(),
        help="Local date for filtering past games (YYYY-MM-DD).",
    )
    args = argument_parser.parse_args()

    games = collect_upcoming_games(args.today)
    write_csv(games)
    print(f"Wrote {len(games)} upcoming UNC home games to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()