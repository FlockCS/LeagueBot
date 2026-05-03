from unittest.mock import patch, MagicMock
from src.discord import send_to_discord


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
