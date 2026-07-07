from datetime import date
from unittest.mock import patch
from src.sources.riot import collect, GAME_NAME

PLAYER = {"player_id": "vishal", "name": "Vishal", "riot": {"game_name": "Veesh", "tag_line": "5030"}}


class TestCollectDaily:
    @patch("src.sources.riot.delete_daily_before")
    @patch("src.sources.riot.load_week")
    @patch("src.sources.riot.save_daily")
    @patch("src.sources.riot.calculate_hours")
    @patch("src.sources.riot.get_puuid")
    @patch("src.sources.riot.time.sleep")
    def test_daily_queries_and_persists(
        self, mock_sleep, mock_puuid, mock_hours, mock_save, mock_load, mock_delete
    ):
        mock_puuid.return_value = "fake-puuid"
        mock_hours.return_value = 4.0
        mock_load.return_value = []

        with patch("src.sources.riot.PLAYERS", [PLAYER]):
            daily, _ = collect(date(2026, 5, 13))  # Wednesday

        assert len(daily) == 1
        assert daily[0].person_id == "vishal"
        assert daily[0].display_name == "Vishal"
        assert daily[0].games == {GAME_NAME: 4.0}
        mock_save.assert_called_once_with(date(2026, 5, 13), "vishal", "Vishal", 4.0)

    @patch("src.sources.riot.delete_daily_before")
    @patch("src.sources.riot.load_week")
    @patch("src.sources.riot.save_daily")
    @patch("src.sources.riot.calculate_hours")
    @patch("src.sources.riot.get_puuid")
    @patch("src.sources.riot.time.sleep")
    def test_zero_hours_not_persisted_or_listed(
        self, mock_sleep, mock_puuid, mock_hours, mock_save, mock_load, mock_delete
    ):
        mock_puuid.return_value = "fake-puuid"
        mock_hours.return_value = 0
        mock_load.return_value = []

        with patch("src.sources.riot.PLAYERS", [PLAYER]):
            daily, _ = collect(date(2026, 5, 13))

        assert daily == []
        mock_save.assert_not_called()

    @patch("src.sources.riot.delete_daily_before")
    @patch("src.sources.riot.load_week")
    @patch("src.sources.riot.save_daily")
    @patch("src.sources.riot.calculate_hours")
    @patch("src.sources.riot.get_puuid")
    @patch("src.sources.riot.time.sleep")
    def test_skips_failed_puuid(
        self, mock_sleep, mock_puuid, mock_hours, mock_save, mock_load, mock_delete
    ):
        mock_puuid.return_value = None
        mock_load.return_value = []

        with patch("src.sources.riot.PLAYERS", [PLAYER]):
            daily, _ = collect(date(2026, 5, 13))

        assert daily == []
        mock_hours.assert_not_called()

    @patch("src.sources.riot.delete_daily_before")
    @patch("src.sources.riot.load_week")
    @patch("src.sources.riot.save_daily")
    @patch("src.sources.riot.calculate_hours")
    @patch("src.sources.riot.get_puuid")
    @patch("src.sources.riot.time.sleep")
    def test_skips_steam_only_players(
        self, mock_sleep, mock_puuid, mock_hours, mock_save, mock_load, mock_delete
    ):
        # A roster row with no riot handle must be ignored by the Riot source.
        mock_puuid.return_value = "fake-puuid"
        mock_hours.return_value = 2.0
        mock_load.return_value = []
        roster = [
            {"player_id": "chris", "name": "Chris", "steam_id": "222"},
            PLAYER,
        ]
        with patch("src.sources.riot.PLAYERS", roster):
            daily, _ = collect(date(2026, 5, 13))

        assert [p.person_id for p in daily] == ["vishal"]
        assert mock_puuid.call_count == 1  # only the League-tracked player queried


class TestCollectWeekly:
    @patch("src.sources.riot.delete_daily_before")
    @patch("src.sources.riot.load_week")
    @patch("src.sources.riot.save_daily")
    @patch("src.sources.riot.calculate_hours")
    @patch("src.sources.riot.get_puuid")
    @patch("src.sources.riot.time.sleep")
    def test_weekly_sums_persisted_records(
        self, mock_sleep, mock_puuid, mock_hours, mock_save, mock_load, mock_delete
    ):
        mock_puuid.return_value = "fake-puuid"
        mock_hours.return_value = 0  # keep daily empty; focus on weekly
        mock_load.return_value = [
            {"player_id": "vishal", "date": "2026-05-11", "hours": 2.0, "name": "Vishal"},
            {"player_id": "vishal", "date": "2026-05-12", "hours": 3.5, "name": "Vishal"},
        ]

        with patch("src.sources.riot.PLAYERS", [PLAYER]):
            _, weekly = collect(date(2026, 5, 13))

        assert len(weekly) == 1
        assert weekly[0].person_id == "vishal"
        assert weekly[0].display_name == "Vishal"
        assert weekly[0].games == {GAME_NAME: 5.5}

    @patch("src.sources.riot.delete_daily_before")
    @patch("src.sources.riot.load_week")
    @patch("src.sources.riot.save_daily")
    @patch("src.sources.riot.calculate_hours")
    @patch("src.sources.riot.get_puuid")
    @patch("src.sources.riot.time.sleep")
    def test_monday_triggers_cleanup(
        self, mock_sleep, mock_puuid, mock_hours, mock_save, mock_load, mock_delete
    ):
        mock_puuid.return_value = "fake-puuid"
        mock_hours.return_value = 0
        mock_load.return_value = []

        with patch("src.sources.riot.PLAYERS", [PLAYER]):
            collect(date(2026, 5, 11))  # Monday

        mock_delete.assert_called_once_with(date(2026, 5, 11), "vishal")
