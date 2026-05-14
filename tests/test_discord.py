from datetime import date
from unittest.mock import patch, MagicMock
from src.discord import send_to_discord, send_steam_to_discord


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
    def test_skips_post_when_both_empty(self, mock_post):
        send_steam_to_discord([], [], date(2026, 5, 14), date(2026, 5, 13))
        mock_post.assert_not_called()

    @patch("src.discord.requests.post")
    def test_renders_daily_with_top_games(self, mock_post):
        mock_post.return_value = MagicMock(raise_for_status=lambda: None)
        daily = [
            ("Donkey", 5.0, [("Counter-Strike 2", 4.0), ("Dota 2", 1.0)]),
            ("Pranav", 2.0, [("Apex Legends", 2.0)]),
        ]
        send_steam_to_discord(daily, [], date(2026, 5, 14), date(2026, 5, 13))

        payload = mock_post.call_args[1]["json"]["content"]
        assert "Donkey" in payload
        assert "Counter-Strike 2" in payload
        assert "Dota 2" in payload
        assert "Pranav" in payload
        assert "5.0 hrs" in payload

    @patch("src.discord.requests.post")
    def test_renders_weekly_section_when_present(self, mock_post):
        mock_post.return_value = MagicMock(raise_for_status=lambda: None)
        daily = [("Donkey", 5.0, [("CS2", 5.0)])]
        weekly = [("Donkey", 20.0), ("Pranav", 10.0)]
        send_steam_to_discord(daily, weekly, date(2026, 5, 14), date(2026, 5, 13))

        payload = mock_post.call_args[1]["json"]["content"]
        assert "This Week So Far" in payload
        assert "20.0 hrs" in payload

    @patch("src.discord.requests.post")
    def test_omits_weekly_section_when_empty(self, mock_post):
        mock_post.return_value = MagicMock(raise_for_status=lambda: None)
        daily = [("Donkey", 5.0, [("CS2", 5.0)])]
        send_steam_to_discord(daily, [], date(2026, 5, 14), date(2026, 5, 13))

        payload = mock_post.call_args[1]["json"]["content"]
        assert "This Week So Far" not in payload
