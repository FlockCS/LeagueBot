from datetime import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch, MagicMock
from src.discord import send_leaderboard
from src.models import PlayerPlaytime

_ET = ZoneInfo("America/New_York")
WED = datetime(2026, 5, 13, 10, 0, tzinfo=_ET)   # Wednesday 10 AM ET
SUN = datetime(2026, 5, 17, 10, 0, tzinfo=_ET)   # Sunday 10 AM ET


class TestSendLeaderboard:
    @patch("src.discord.requests.post")
    def test_daily_renders_top_3_with_per_game_breakdown(self, mock_post):
        mock_post.return_value = MagicMock(raise_for_status=lambda: None)
        rows = [
            PlayerPlaytime("1", "Veesh", {"League of Legends": 4.0, "Counter-Strike 2": 2.2}),
            PlayerPlaytime("2", "Manish", {"Dota 2": 3.1}),
            PlayerPlaytime("3", "Chris", {"Apex Legends": 1.0}),
            PlayerPlaytime("4", "Will", {"CS2": 0.5}),
        ]
        send_leaderboard(rows, "daily", WED)

        payload = mock_post.call_args[1]["json"]["content"]
        assert "Top Gamers Today" in payload
        assert "Veesh — 6.2 hrs" in payload          # merged League + Steam total
        assert "League of Legends — 4.0 hrs" in payload
        assert "Counter-Strike 2 — 2.2 hrs" in payload
        assert "Manish" in payload
        assert "Chris" in payload
        assert "Will" not in payload                 # only top 3 shown

    @patch("src.discord.requests.post")
    def test_weekly_uses_weekly_header_and_window(self, mock_post):
        mock_post.return_value = MagicMock(raise_for_status=lambda: None)
        rows = [PlayerPlaytime("1", "Veesh", {"League of Legends": 20.0})]
        send_leaderboard(rows, "weekly", SUN)  # Sunday

        payload = mock_post.call_args[1]["json"]["content"]
        assert "Weekly Recap" in payload
        assert "Top Gamers Today" not in payload
        assert "20.0 hrs" in payload

    @patch("src.discord.requests.post")
    def test_games_sorted_most_played_first(self, mock_post):
        mock_post.return_value = MagicMock(raise_for_status=lambda: None)
        rows = [PlayerPlaytime("1", "Veesh", {"Small": 1.0, "Big": 5.0})]
        send_leaderboard(rows, "daily", WED)

        payload = mock_post.call_args[1]["json"]["content"]
        assert payload.index("Big") < payload.index("Small")

    @patch("src.discord.requests.post")
    def test_empty_rows_skips_post(self, mock_post):
        send_leaderboard([], "daily", WED)
        mock_post.assert_not_called()
