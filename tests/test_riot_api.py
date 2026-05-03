from unittest.mock import patch, MagicMock
from src.riot_api import get_puuid, get_match_ids, get_match_duration, calculate_hours


class TestGetPuuid:
    @patch("src.riot_api.requests.get")
    def test_success(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"puuid": "abc-123"},
        )
        assert get_puuid("Manny", "MANG") == "abc-123"

    @patch("src.riot_api.requests.get")
    def test_failure_returns_none(self, mock_get):
        mock_get.return_value = MagicMock(status_code=403)
        assert get_puuid("Manny", "MANG") is None


class TestGetMatchIds:
    @patch("src.riot_api.requests.get")
    def test_returns_match_list(self, mock_get):
        mock_get.return_value = MagicMock(
            json=lambda: ["NA1_1234", "NA1_5678"],
            raise_for_status=lambda: None,
        )
        result = get_match_ids("abc-123", 1000, 2000)
        assert result == ["NA1_1234", "NA1_5678"]


class TestGetMatchDuration:
    @patch("src.riot_api.requests.get")
    def test_returns_duration(self, mock_get):
        mock_get.return_value = MagicMock(
            json=lambda: {"info": {"gameDuration": 1800}},
            raise_for_status=lambda: None,
        )
        assert get_match_duration("NA1_1234") == 1800


class TestCalculateHours:
    @patch("src.riot_api.get_match_duration")
    @patch("src.riot_api.get_match_ids")
    def test_sums_durations(self, mock_ids, mock_duration):
        mock_ids.return_value = ["NA1_1", "NA1_2"]
        mock_duration.side_effect = [3600, 1800]
        assert calculate_hours("abc-123", 1000, 2000) == 1.5

    @patch("src.riot_api.get_match_ids")
    def test_no_matches_returns_zero(self, mock_ids):
        mock_ids.return_value = []
        assert calculate_hours("abc-123", 1000, 2000) == 0

    @patch("src.riot_api.get_match_ids")
    def test_fetch_error_returns_zero(self, mock_ids):
        mock_ids.side_effect = Exception("rate limited")
        assert calculate_hours("abc-123", 1000, 2000) == 0

    @patch("src.riot_api.get_match_duration")
    @patch("src.riot_api.get_match_ids")
    def test_skips_failed_match(self, mock_ids, mock_duration):
        mock_ids.return_value = ["NA1_1", "NA1_2", "NA1_3"]
        mock_duration.side_effect = [3600, Exception("timeout"), 3600]
        assert calculate_hours("abc-123", 1000, 2000) == 2.0
