from datetime import date
from unittest.mock import patch, MagicMock
from src.discord import send_to_discord, send_steam_to_discord
from src.steam_leaderboard import SteamLeaderboard


class TestSendToDiscord:
    @patch("src.discord.requests.post")
    def test_posts_top_3(self, mock_post):
        mock_post.return_value = MagicMock(raise_for_status=lambda: None)
        results = [
            ("Alice", 5.0),
            ("Bob", 3.5),
            ("Charlie", 2.0),
            ("Dave", 1.0),
        ]
        send_to_discord(results)

        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]["content"]
        assert "Alice" in payload
        assert "Bob" in payload
        assert "Charlie" in payload
        assert "Dave" not in payload

    @patch("src.discord.requests.post")
    def test_formats_hours(self, mock_post):
        mock_post.return_value = MagicMock(raise_for_status=lambda: None)
        send_to_discord([("Alice", 3.456), ("Bob", 1.0), ("Charlie", 0.5)])

        payload = mock_post.call_args[1]["json"]["content"]
        assert "3.5 hrs" in payload
        assert "1.0 hrs" in payload
        assert "0.5 hrs" in payload


class TestSendSteamToDiscord:
    @patch("src.discord.requests.post")
    def test_weekday_with_no_daily_skips_post(self, mock_post):
        # Wednesday with nothing to report — no message.
        lb = SteamLeaderboard(today=date(2026, 5, 13))
        send_steam_to_discord(lb)
        mock_post.assert_not_called()

    @patch("src.discord.requests.post")
    def test_sunday_with_no_weekly_skips_post(self, mock_post):
        # Sunday with no weekly tally — no message.
        lb = SteamLeaderboard(today=date(2026, 5, 17))
        send_steam_to_discord(lb)
        mock_post.assert_not_called()

    @patch("src.discord.requests.post")
    def test_weekday_renders_daily_with_top_games(self, mock_post):
        mock_post.return_value = MagicMock(raise_for_status=lambda: None)
        daily = [
            ("Donkey", 5.0, [("Counter-Strike 2", 4.0), ("Dota 2", 1.0)]),
            ("Pranav", 2.0, [("Apex Legends", 2.0)]),
        ]
        lb = SteamLeaderboard(today=date(2026, 5, 13), daily_results=daily)
        send_steam_to_discord(lb)

        payload = mock_post.call_args[1]["json"]["content"]
        assert "Top Steam Players Today" in payload
        assert "Donkey" in payload
        assert "Counter-Strike 2" in payload
        assert "Dota 2" in payload
        assert "Pranav" in payload
        assert "5.0 hrs" in payload

    @patch("src.discord.requests.post")
    def test_weekday_ignores_weekly_results(self, mock_post):
        # Mon-Sat post shouldn't include the weekly section even if it's populated.
        mock_post.return_value = MagicMock(raise_for_status=lambda: None)
        daily = [("Donkey", 5.0, [("CS2", 5.0)])]
        weekly = [("Donkey", 20.0, [("CS2", 20.0)])]
        lb = SteamLeaderboard(today=date(2026, 5, 13), daily_results=daily, weekly_results=weekly)
        send_steam_to_discord(lb)

        payload = mock_post.call_args[1]["json"]["content"]
        assert "Weekly Recap" not in payload
        assert "20.0 hrs" not in payload

    @patch("src.discord.requests.post")
    def test_sunday_renders_weekly_recap_with_top_games(self, mock_post):
        mock_post.return_value = MagicMock(raise_for_status=lambda: None)
        weekly = [
            ("Donkey", 20.0, [("Counter-Strike 2", 15.0), ("Dota 2", 5.0)]),
            ("Pranav", 10.0, [("Apex Legends", 10.0)]),
        ]
        lb = SteamLeaderboard(today=date(2026, 5, 17), weekly_results=weekly)
        send_steam_to_discord(lb)

        payload = mock_post.call_args[1]["json"]["content"]
        assert "Steam Weekly Recap" in payload
        assert "Donkey" in payload
        assert "20.0 hrs" in payload
        assert "Counter-Strike 2" in payload
        assert "Dota 2" in payload
        assert "Pranav" in payload

    @patch("src.discord.requests.post")
    def test_sunday_ignores_daily_results(self, mock_post):
        # Sunday post is weekly-only — daily section never appears.
        mock_post.return_value = MagicMock(raise_for_status=lambda: None)
        daily = [("Donkey", 5.0, [("CS2", 5.0)])]
        weekly = [("Donkey", 20.0, [("CS2", 20.0)])]
        lb = SteamLeaderboard(today=date(2026, 5, 17), daily_results=daily, weekly_results=weekly)
        send_steam_to_discord(lb)

        payload = mock_post.call_args[1]["json"]["content"]
        assert "Top Steam Players Today" not in payload
