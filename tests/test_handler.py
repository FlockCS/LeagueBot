from unittest.mock import patch
from freezegun import freeze_time
from src.handler import handler
from src.models import PlayerPlaytime


class TestHandler:
    @freeze_time("2026-05-13 14:00:00")  # Wednesday, 9 AM ET
    @patch("src.handler.send_leaderboard")
    @patch("src.handler.build")
    def test_weekday_posts_daily_only(self, mock_build, mock_send):
        daily = [PlayerPlaytime("1", "Veesh", {"League of Legends": 4.0})]
        weekly = [PlayerPlaytime("1", "Veesh", {"League of Legends": 20.0})]
        mock_build.return_value = (daily, weekly)

        result = handler({}, None)

        # Daily posted, weekly NOT posted on a weekday even though it's populated.
        assert mock_send.call_count == 1
        rows, period, _today = mock_send.call_args[0]
        assert period == "daily"
        assert rows == daily
        assert result["statusCode"] == 200

    @freeze_time("2026-05-17 14:00:00")  # Sunday
    @patch("src.handler.send_leaderboard")
    @patch("src.handler.build")
    def test_sunday_posts_daily_and_weekly(self, mock_build, mock_send):
        daily = [PlayerPlaytime("1", "Veesh", {"League of Legends": 4.0})]
        weekly = [PlayerPlaytime("1", "Veesh", {"League of Legends": 20.0})]
        mock_build.return_value = (daily, weekly)

        handler({}, None)

        assert mock_send.call_count == 2
        periods = [call.args[1] for call in mock_send.call_args_list]
        assert periods == ["daily", "weekly"]

    @freeze_time("2026-05-13 14:00:00")
    @patch("src.handler.send_leaderboard")
    @patch("src.handler.build")
    def test_skips_daily_post_when_empty(self, mock_build, mock_send):
        mock_build.return_value = ([], [])
        handler({}, None)
        mock_send.assert_not_called()

    @freeze_time("2026-05-17 14:00:00")  # Sunday
    @patch("src.handler.send_leaderboard")
    @patch("src.handler.build")
    def test_sunday_with_empty_weekly_skips_weekly(self, mock_build, mock_send):
        daily = [PlayerPlaytime("1", "Veesh", {"League of Legends": 4.0})]
        mock_build.return_value = (daily, [])
        handler({}, None)

        assert mock_send.call_count == 1
        assert mock_send.call_args[0][1] == "daily"
