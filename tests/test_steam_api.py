from unittest.mock import patch, MagicMock
from src.steam_api import get_player_status, get_owned_games


class TestGetPlayerStatus:
    @patch("src.steam_api.requests.get")
    def test_success(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"response": {"players": [{"personaname": "Donkey", "gameextrainfo": "Counter-Strike 2"}]}},
        )
        result = get_player_status("76561198000000000")
        assert result == {"name": "Donkey", "game": "Counter-Strike 2"}

    @patch("src.steam_api.requests.get")
    def test_not_in_game_returns_none_for_game(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"response": {"players": [{"personaname": "Donkey"}]}},
        )
        result = get_player_status("76561198000000000")
        assert result["name"] == "Donkey"
        assert result["game"] is None

    @patch("src.steam_api.requests.get")
    def test_http_failure_returns_none(self, mock_get):
        mock_get.return_value = MagicMock(status_code=500)
        assert get_player_status("76561198000000000") is None

    @patch("src.steam_api.requests.get")
    def test_empty_players_returns_none(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"response": {"players": []}},
        )
        assert get_player_status("76561198000000000") is None


class TestGetOwnedGames:
    @patch("src.steam_api.requests.get")
    def test_success_and_filters_zero_playtime(self, mock_get):
        # Games with 0 playtime should be excluded to keep DynamoDB items small.
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"response": {"games": [
                {"name": "Counter-Strike 2", "playtime_forever": 1234},
                {"name": "Unplayed Game",    "playtime_forever": 0},
                {"name": "Dota 2",           "playtime_forever": 500},
            ]}},
        )
        result = get_owned_games("76561198000000000")
        assert result == {"Counter-Strike 2": 1234, "Dota 2": 500}
        assert "Unplayed Game" not in result

    @patch("src.steam_api.requests.get")
    def test_private_profile_returns_none(self, mock_get):
        # Private Steam profiles return an empty response dict — no "games" key.
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"response": {}},
        )
        assert get_owned_games("76561198000000000") is None

    @patch("src.steam_api.requests.get")
    def test_http_failure_returns_none(self, mock_get):
        mock_get.return_value = MagicMock(status_code=403)
        assert get_owned_games("76561198000000000") is None
