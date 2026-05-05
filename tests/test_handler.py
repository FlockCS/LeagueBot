import os
from unittest.mock import patch
from handler import handler

ENV_PATCH = {"RIOT_API_KEY": "test", "DISCORD_WEBHOOK_URL": "test"}


class TestHandler:
    @patch.dict(os.environ, ENV_PATCH)
    @patch("handler.send_to_discord")
    @patch("handler.build_leaderboard")
    def test_sends_when_data_exists(self, mock_build, mock_send):
        mock_build.return_value = [("Alice", 5.0)]
        result = handler({}, None)
        mock_send.assert_called_once_with([("Alice", 5.0)])
        assert result["statusCode"] == 200

    @patch.dict(os.environ, ENV_PATCH)
    @patch("handler.send_to_discord")
    @patch("handler.build_leaderboard")
    def test_skips_send_when_empty(self, mock_build, mock_send):
        mock_build.return_value = []
        result = handler({}, None)
        mock_send.assert_not_called()
        assert result["statusCode"] == 200
