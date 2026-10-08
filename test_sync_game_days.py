import unittest
from datetime import date

from sync_game_days import parse_schedule, season_for_sport


class ScheduleParsingTests(unittest.TestCase):
    def test_basketball_season_stays_in_prior_year_through_summer(self):
        self.assertEqual(season_for_sport("mens-basketball", date(2027, 1, 9)), 2026)
        self.assertEqual(season_for_sport("womens-basketball", date(2027, 7, 9)), 2026)

    def test_new_basketball_season_starts_in_august(self):
        self.assertEqual(season_for_sport("mens-basketball", date(2027, 8, 1)), 2027)

    def test_football_season_uses_calendar_year(self):
        self.assertEqual(season_for_sport("football", date(2027, 1, 9)), 2027)

    def test_keeps_only_chapel_hill_home_games(self):
        html = """
        <table>
          <tr><th>Date</th><th>Time</th><th>At</th><th>Opponent</th><th>Location</th></tr>
          <tr><td>Oct 24 (Sat)</td><td>TBA</td><td>Home</td><td>Syracuse</td><td>Chapel Hill (Kenan Stadium)</td></tr>
          <tr><td>Oct 31 (Sat)</td><td>TBA</td><td>Away</td><td>Miami</td><td>Chapel Hill</td></tr>
          <tr><td>Nov 7 (Sat)</td><td>TBA</td><td>Neutral</td><td>ACC Championship</td><td>Charlotte, N.C.</td></tr>
        </table>
        """

        self.assertEqual(
            parse_schedule(html, "Football", 2026),
            [(date(2026, 10, 24), "Football vs Syracuse")],
        )

    def test_basketball_january_dates_roll_into_next_year(self):
        html = """
        <table>
          <tr><td>Jan 9 (Sat)</td><td>Noon</td><td>Home</td><td>NC State</td><td>Chapel Hill (Smith Center)</td></tr>
        </table>
        """

        self.assertEqual(
            parse_schedule(html, "Men's basketball", 2026),
            [(date(2027, 1, 9), "Men's basketball vs NC State")],
        )


if __name__ == "__main__":
    unittest.main()