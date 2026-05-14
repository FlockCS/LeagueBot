from unittest.mock import patch
from freezegun import freeze_time
from src.steam_leaderboard import _game_deltas, _week_start, build_steam_leaderboard
from datetime import date


class TestGameDeltas:
    def test_computes_per_game_delta(self):
        today = {"Counter-Strike 2": 1300, "Dota 2": 600}
        yesterday = {"Counter-Strike 2": 1100, "Dota 2": 580}
        result = _game_deltas(today, yesterday)
        assert result == {"Counter-Strike 2": 200, "Dota 2": 20}

    def test_new_game_counts_full_playtime(self):
        # A game not in yesterday's snapshot is brand new — its full playtime counts.
        result = _game_deltas({"Apex Legends": 120}, {})
        assert result == {"Apex Legends": 120}

    def test_no_plays_returns_empty(self):
        games = {"Counter-Strike 2": 1000}
        result = _game_deltas(games, games)
        assert result == {}

    def test_filters_negative_or_zero_deltas(self):
        # Shouldn't happen with real data, but safe to guard against.
        today = {"Counter-Strike 2": 1000}
        yesterday = {"Counter-Strike 2": 1000, "Dota 2": 500}
        result = _game_deltas(today, yesterday)
        assert result == {}


class TestWeekStart:
    def test_wednesday_returns_previous_monday(self):
        wednesday = date(2026, 5, 13)   # a Wednesday
        assert _week_start(wednesday) == date(2026, 5, 11)

    def test_monday_returns_itself(self):
        monday = date(2026, 5, 11)
        assert _week_start(monday) == monday

    def test_sunday_returns_monday_of_same_week(self):
        sunday = date(2026, 5, 17)
        assert _week_start(sunday) == date(2026, 5, 11)


class TestBuildSteamLeaderboard:
    @freeze_time("2026-05-13 14:00:00")  # Wednesday at 9 AM ET (UTC-5 in winter, UTC-4 in summer)
    @patch("src.steam_leaderboard.delete_snapshots_before")
    @patch("src.steam_leaderboard.save_snapshot")
    @patch("src.steam_leaderboard.load_snapshot")
    @patch("src.steam_leaderboard.get_owned_games")
    @patch("src.steam_leaderboard.get_player_status")
    @patch("src.steam_leaderboard.time.sleep")
    def test_computes_daily_and_weekly_correctly(
        self, mock_sleep, mock_status, mock_games, mock_load, mock_save, mock_delete
    ):
        mock_status.return_value = {"name": "Donkey", "game": None}
        mock_games.return_value = {"Counter-Strike 2": 1300, "Dota 2": 600}

        def fake_load(date_key, steam_id):
            snapshots = {
                "2026-05-12": {"games": {"Counter-Strike 2": 1100, "Dota 2": 580}, "total_minutes": 1680},
                "2026-05-11": {"games": {"Counter-Strike 2": 1000}, "total_minutes": 1000},
            }
            return snapshots.get(date_key)

        mock_load.side_effect = fake_load

        with patch("src.steam_leaderboard.STEAM_PLAYERS", [{"discord_id": "1", "steam_id": "100"}]):
            daily, weekly, today, yesterday = build_steam_leaderboard()

        # Daily: CS2 +200 min, Dota +20 min = 220 min = 3.667 hrs
        assert len(daily) == 1
        name, hours, top_games = daily[0]
        assert name == "Donkey"
        assert round(hours, 2) == round(220 / 60, 2)
        assert top_games[0][0] == "Counter-Strike 2"

        # Weekly: total today (1900) - total from Monday (1000) = 900 min = 15 hrs
        assert len(weekly) == 1
        assert weekly[0][0] == "Donkey"
        assert weekly[0][1] == 15.0

        # Should not have triggered cleanup (today is Wednesday, weekday=2)
        mock_delete.assert_not_called()

    @freeze_time("2026-05-13 14:00:00")
    @patch("src.steam_leaderboard.delete_snapshots_before")
    @patch("src.steam_leaderboard.save_snapshot")
    @patch("src.steam_leaderboard.load_snapshot")
    @patch("src.steam_leaderboard.get_owned_games")
    @patch("src.steam_leaderboard.get_player_status")
    @patch("src.steam_leaderboard.time.sleep")
    def test_first_run_no_snapshots_skips_gracefully(
        self, mock_sleep, mock_status, mock_games, mock_load, mock_save, mock_delete
    ):
        # First run ever — no yesterday or week snapshot exists.
        mock_status.return_value = {"name": "Donkey", "game": None}
        mock_games.return_value = {"Counter-Strike 2": 1000}
        mock_load.return_value = None  # No snapshots in DB yet.

        with patch("src.steam_leaderboard.STEAM_PLAYERS", [{"discord_id": "1", "steam_id": "100"}]):
            daily, weekly, today, yesterday = build_steam_leaderboard()

        # Both lists empty — only the baseline snapshot was saved.
        assert daily == []
        assert weekly == []
        mock_save.assert_called_once()  # Still saves today's snapshot as the baseline.

    @freeze_time("2026-05-11 14:00:00")  # A Monday
    @patch("src.steam_leaderboard.delete_snapshots_before")
    @patch("src.steam_leaderboard.save_snapshot")
    @patch("src.steam_leaderboard.load_snapshot")
    @patch("src.steam_leaderboard.get_owned_games")
    @patch("src.steam_leaderboard.get_player_status")
    @patch("src.steam_leaderboard.time.sleep")
    def test_monday_triggers_cleanup(
        self, mock_sleep, mock_status, mock_games, mock_load, mock_save, mock_delete
    ):
        mock_status.return_value = {"name": "Donkey", "game": None}
        mock_games.return_value = {"Counter-Strike 2": 1000}
        mock_load.return_value = None

        with patch("src.steam_leaderboard.STEAM_PLAYERS", [{"discord_id": "1", "steam_id": "100"}]):
            build_steam_leaderboard()

        mock_delete.assert_called_once_with("2026-05-11", "100")

    @freeze_time("2026-05-13 14:00:00")
    @patch("src.steam_leaderboard.delete_snapshots_before")
    @patch("src.steam_leaderboard.save_snapshot")
    @patch("src.steam_leaderboard.load_snapshot")
    @patch("src.steam_leaderboard.get_owned_games")
    @patch("src.steam_leaderboard.get_player_status")
    @patch("src.steam_leaderboard.time.sleep")
    def test_sorts_by_daily_hours_descending(
        self, mock_sleep, mock_status, mock_games, mock_load, mock_save, mock_delete
    ):
        mock_status.side_effect = [
            {"name": "Alice", "game": None},
            {"name": "Bob",   "game": None},
        ]
        mock_games.side_effect = [
            {"Counter-Strike 2": 200},  # Alice: 200 min today
            {"Counter-Strike 2": 600},  # Bob:   600 min today
        ]
        mock_load.side_effect = lambda date_key, _: (
            {"games": {}, "total_minutes": 0} if date_key == "2026-05-12" else None
        )

        players = [{"discord_id": "1", "steam_id": "111"}, {"discord_id": "2", "steam_id": "222"}]
        with patch("src.steam_leaderboard.STEAM_PLAYERS", players):
            daily, weekly, _, _ = build_steam_leaderboard()

        assert daily[0][0] == "Bob"
        assert daily[1][0] == "Alice"
