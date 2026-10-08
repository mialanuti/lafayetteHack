import json
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import main


class DateMatchingTests(unittest.TestCase):
    def test_matches_iso_numeric_and_month_name_dates(self):
        found = main.dates_mentioned(
            "Party on 2026-11-14, with a backup on 11/15/2026 or Nov 16.", 2026
        )

        self.assertEqual(
            found,
            {date(2026, 11, 14), date(2026, 11, 15), date(2026, 11, 16)},
        )

    def test_iso_date_does_not_create_a_second_date_in_received_year(self):
        found = main.dates_mentioned("The date is 2025-06-14.", 2026)

        self.assertEqual(found, {date(2025, 6, 14)})

    def test_reads_game_dates_from_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "game_days.csv"
            csv_path.write_text("date,event\n2026-11-14,Home game\n", encoding="utf-8")
            with patch.object(main, "GAME_DAYS_PATH", csv_path):
                self.assertEqual(main.game_dates(), {date(2026, 11, 14)})


class TriageTests(unittest.TestCase):
    def test_invalid_model_result_escalates_with_required_reason(self):
        result = main.invalid_result()

        self.assertEqual(result.decision, main.Decision.escalate_to_owner)
        self.assertEqual(result.reason, "model output invalid")

    def test_server_matches_game_date_and_persists_triage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            game_days = root / "game_days.csv"
            inbox = root / "inbox.json"
            game_days.write_text("date,event\n2026-11-14,Home game\n", encoding="utf-8")
            inbox.write_text("[]", encoding="utf-8")
            model_result = main.TriageResult(
                category=main.Category.party_group,
                details=main.InquiryDetails(
                    date="2026-11-14", headcount=12, ask="Reserve a table"
                ),
                decision=main.Decision.escalate_to_owner,
                reason="Game-day booking needs owner review.",
                draft_reply="Thanks for reaching out.",
            )
            with (
                patch.object(main, "GAME_DAYS_PATH", game_days),
                patch.object(main, "INBOX_PATH", inbox),
                patch.object(main, "call_model", return_value=model_result) as call_model,
            ):
                record = main.triage(
                    main.TriageRequest(
                        message="Can we reserve a table on Nov 14, 2026 for 12?",
                        received_date=date(2026, 10, 8),
                    )
                )

            self.assertTrue(record.high_demand_date)
            self.assertTrue(call_model.call_args.args[2])
            self.assertEqual(json.loads(inbox.read_text(encoding="utf-8"))[0]["id"], record.id)

    def test_malformed_model_json_returns_escalation_fallback(self):
        completion = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="not json"))]
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=lambda **_kwargs: completion)
            )
        )
        with (
            patch.object(main, "OpenAI", return_value=client),
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}),
        ):
            result = main.call_model("Can I book a party?", date(2026, 10, 8), False)

        self.assertEqual(result.decision, main.Decision.escalate_to_owner)
        self.assertEqual(result.reason, "model output invalid")

    def test_empty_model_response_returns_escalation_fallback(self):
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=lambda **_kwargs: SimpleNamespace(choices=[]))
            )
        )
        with (
            patch.object(main, "OpenAI", return_value=client),
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}),
        ):
            result = main.call_model("Can I book a party?", date(2026, 10, 8), False)

        self.assertEqual(result.decision, main.Decision.escalate_to_owner)
        self.assertEqual(result.reason, "model output invalid")


if __name__ == "__main__":
    unittest.main()