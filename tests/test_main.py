from unittest.mock import patch
from freezegun import freeze_time
from src.main import get_yesterday_timestamps, build_leaderboard


class TestGetYesterdayTimestamps:
    @freeze_time("2025-07-15 12:00:00", tz_offset=-4)
    def test_returns_correct_window(self):
        start_ts, end_ts, window_start, window_end = get_yesterday_timestamps()
        assert window_start.day == 14
        assert window_end.day == 15
        assert start_ts < end_ts


class TestBuildLeaderboard:
    @patch("src.main.calculate_hours")
    @patch("src.main.get_puuid")
    def test_sorts_by_hours_descending(self, mock_puuid, mock_hours):
        mock_puuid.return_value = "fake-puuid"
        mock_hours.side_effect = [1.0, 3.0, 2.0]

        with patch("src.main.PLAYERS", [("A", "1"), ("B", "2"), ("C", "3")]):
            results = build_leaderboard()

        assert results[0] == ("B", 3.0)
        assert results[1] == ("C", 2.0)
        assert results[2] == ("A", 1.0)

    @patch("src.main.get_puuid")
    def test_skips_failed_puuid(self, mock_puuid):
        mock_puuid.return_value = None

        with patch("src.main.PLAYERS", [("A", "1")]):
            results = build_leaderboard()

        assert results == []
