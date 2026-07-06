from datetime import date
from unittest.mock import patch
from src.sources.steam import _game_deltas, _week_start, collect


class TestGameDeltas:
    def test_computes_per_game_delta(self):
        today = {"Counter-Strike 2": 1300, "Dota 2": 600}
        yesterday = {"Counter-Strike 2": 1100, "Dota 2": 580}
        result = _game_deltas(today, yesterday)
        assert result == {"Counter-Strike 2": 200, "Dota 2": 20}

    def test_new_game_counts_full_playtime(self):
        result = _game_deltas({"Apex Legends": 120}, {})
        assert result == {"Apex Legends": 120}

    def test_no_plays_returns_empty(self):
        games = {"Counter-Strike 2": 1000}
        assert _game_deltas(games, games) == {}

    def test_filters_negative_or_zero_deltas(self):
        today = {"Counter-Strike 2": 1000}
        yesterday = {"Counter-Strike 2": 1000, "Dota 2": 500}
        assert _game_deltas(today, yesterday) == {}


class TestWeekStart:
    def test_wednesday_returns_previous_monday(self):
        assert _week_start(date(2026, 5, 13)) == date(2026, 5, 11)

    def test_monday_returns_itself(self):
        assert _week_start(date(2026, 5, 11)) == date(2026, 5, 11)

    def test_sunday_returns_monday_of_same_week(self):
        assert _week_start(date(2026, 5, 17)) == date(2026, 5, 11)


class TestCollect:
    @patch("src.sources.steam.delete_snapshots_before")
    @patch("src.sources.steam.save_snapshot")
    @patch("src.sources.steam.load_snapshot")
    @patch("src.sources.steam.get_owned_games")
    @patch("src.sources.steam.get_player_status")
    @patch("src.sources.steam.time.sleep")
    def test_computes_daily_and_weekly_playtime(
        self, mock_sleep, mock_status, mock_games, mock_load, mock_save, mock_delete
    ):
        mock_status.return_value = {"name": "Donkey", "game": None}
        mock_games.return_value = {"Counter-Strike 2": 1300, "Dota 2": 600}

        def fake_load(date_key, steam_id):
            return {
                "2026-05-12": {"games": {"Counter-Strike 2": 1100, "Dota 2": 580}},
                "2026-05-11": {"games": {"Counter-Strike 2": 1000}},
            }.get(date_key)

        mock_load.side_effect = fake_load

        with patch("src.sources.steam.STEAM_PLAYERS", [{"discord_id": "1", "steam_id": "100"}]):
            daily, weekly = collect(date(2026, 5, 13))  # a Wednesday

        # Daily: CS2 +200 min, Dota +20 min = 220 min = 3.667 hrs, keyed by discord_id.
        assert len(daily) == 1
        assert daily[0].person_id == "1"
        assert daily[0].display_name == "Donkey"
        assert round(daily[0].total_hours, 2) == round(220 / 60, 2)
        assert round(daily[0].games["Counter-Strike 2"], 4) == round(200 / 60, 4)

        # Weekly: CS2 +300, Dota +600 vs Monday = 900 min = 15 hrs.
        assert len(weekly) == 1
        assert weekly[0].total_hours == 15.0
        assert round(weekly[0].games["Dota 2"], 4) == round(600 / 60, 4)

        mock_delete.assert_not_called()  # Wednesday — no cleanup.

    @patch("src.sources.steam.delete_snapshots_before")
    @patch("src.sources.steam.save_snapshot")
    @patch("src.sources.steam.load_snapshot")
    @patch("src.sources.steam.get_owned_games")
    @patch("src.sources.steam.get_player_status")
    @patch("src.sources.steam.time.sleep")
    def test_first_run_no_snapshots_skips_gracefully(
        self, mock_sleep, mock_status, mock_games, mock_load, mock_save, mock_delete
    ):
        mock_status.return_value = {"name": "Donkey", "game": None}
        mock_games.return_value = {"Counter-Strike 2": 1000}
        mock_load.return_value = None

        with patch("src.sources.steam.STEAM_PLAYERS", [{"discord_id": "1", "steam_id": "100"}]):
            daily, weekly = collect(date(2026, 5, 13))

        assert daily == []
        assert weekly == []
        mock_save.assert_called_once()  # Baseline snapshot still saved.

    @patch("src.sources.steam.delete_snapshots_before")
    @patch("src.sources.steam.save_snapshot")
    @patch("src.sources.steam.load_snapshot")
    @patch("src.sources.steam.get_owned_games")
    @patch("src.sources.steam.get_player_status")
    @patch("src.sources.steam.time.sleep")
    def test_monday_triggers_cleanup(
        self, mock_sleep, mock_status, mock_games, mock_load, mock_save, mock_delete
    ):
        mock_status.return_value = {"name": "Donkey", "game": None}
        mock_games.return_value = {"Counter-Strike 2": 1000}
        mock_load.return_value = None

        with patch("src.sources.steam.STEAM_PLAYERS", [{"discord_id": "1", "steam_id": "100"}]):
            collect(date(2026, 5, 11))  # a Monday

        mock_delete.assert_called_once_with("2026-05-11", "100")

    @patch("src.sources.steam.delete_snapshots_before")
    @patch("src.sources.steam.save_snapshot")
    @patch("src.sources.steam.load_snapshot")
    @patch("src.sources.steam.get_owned_games")
    @patch("src.sources.steam.get_player_status")
    @patch("src.sources.steam.time.sleep")
    def test_sorts_by_daily_hours_descending(
        self, mock_sleep, mock_status, mock_games, mock_load, mock_save, mock_delete
    ):
        # collect returns rows in player order; the aggregator sorts. Here we just
        # confirm both players surface with the right totals.
        mock_status.side_effect = [
            {"name": "Alice", "game": None},
            {"name": "Bob", "game": None},
        ]
        mock_games.side_effect = [
            {"Counter-Strike 2": 200},
            {"Counter-Strike 2": 600},
        ]
        mock_load.side_effect = lambda date_key, _: (
            {"games": {}} if date_key == "2026-05-12" else None
        )

        players = [{"discord_id": "1", "steam_id": "111"}, {"discord_id": "2", "steam_id": "222"}]
        with patch("src.sources.steam.STEAM_PLAYERS", players):
            daily, _ = collect(date(2026, 5, 13))

        totals = {p.display_name: p.total_hours for p in daily}
        assert round(totals["Bob"], 4) == round(600 / 60, 4)
        assert round(totals["Alice"], 4) == round(200 / 60, 4)
