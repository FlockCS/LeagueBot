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
        # Return is (playtime_by_appid, names_by_appid) — keyed by appid so diffs
        # survive game renames on the Steam store.
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"response": {"games": [
                {"appid": 730,  "name": "Counter-Strike 2", "playtime_forever": 1234},
                {"appid": 9999, "name": "Unplayed Game",    "playtime_forever": 0},
                {"appid": 570,  "name": "Dota 2",           "playtime_forever": 500},
            ]}},
        )
        playtime, names = get_owned_games("76561198000000000")
        assert playtime == {"730": 1234, "570": 500}
        assert names == {"730": "Counter-Strike 2", "570": "Dota 2"}
        assert "9999" not in playtime

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
