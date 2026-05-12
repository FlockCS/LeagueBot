from unittest.mock import patch
from src.handler import handler


class TestHandler:
    @patch("src.handler.send_to_discord")
    @patch("src.handler.build_leaderboard")
    def test_sends_when_data_exists(self, mock_build, mock_send):
        mock_build.return_value = [("Alice", 5.0)]
        result = handler({}, None)
        mock_send.assert_called_once_with([("Alice", 5.0)])
        assert result["statusCode"] == 200

    @patch("src.handler.send_to_discord")
    @patch("src.handler.build_leaderboard")
    def test_skips_send_when_empty(self, mock_build, mock_send):
        mock_build.return_value = []
        result = handler({}, None)
        mock_send.assert_not_called()
        assert result["statusCode"] == 200
