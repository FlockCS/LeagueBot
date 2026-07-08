from datetime import date, datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch
from src.sources.steam import _game_deltas, _week_start, collect

_ET = ZoneInfo("America/New_York")
WED = datetime(2026, 5, 13, 10, 0, tzinfo=_ET)   # Wednesday 10 AM ET
MON = datetime(2026, 5, 11, 10, 0, tzinfo=_ET)   # Monday 10 AM ET


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
    @patch("src.sources.steam.time.sleep")
    def test_computes_daily_and_weekly_playtime(
        self, mock_sleep, mock_games, mock_load, mock_save, mock_delete
    ):
        mock_games.return_value = {"Counter-Strike 2": 1300, "Dota 2": 600}

        # Reference snapshots carry the real capture time; the window starts should
        # reflect those, not an assumed 24h.
        yday_cap = datetime(2026, 5, 12, 9, 30, tzinfo=_ET)
        mon_cap = datetime(2026, 5, 11, 9, 15, tzinfo=_ET)

        def fake_load(date_key, steam_id):
            return {
                "2026-05-12": {"games": {"Counter-Strike 2": 1100, "Dota 2": 580}, "captured_at": yday_cap.isoformat()},
                "2026-05-11": {"games": {"Counter-Strike 2": 1000}, "captured_at": mon_cap.isoformat()},
            }.get(date_key)

        mock_load.side_effect = fake_load

        roster = [{"player_id": "donkey", "name": "Donkey", "steam_id": "100"}]
        with patch("src.sources.steam.PLAYERS", roster):
            daily, weekly, daily_since, weekly_since = collect(WED)  # a Wednesday

        # Daily: CS2 +200 min, Dota +20 min = 220 min = 3.667 hrs, keyed by player_id.
        assert len(daily) == 1
        assert daily[0].person_id == "donkey"
        assert daily[0].display_name == "Donkey"
        assert round(daily[0].total_hours, 2) == round(220 / 60, 2)
        assert round(daily[0].games["Counter-Strike 2"], 4) == round(200 / 60, 4)

        # Weekly: CS2 +300, Dota +600 vs Monday = 900 min = 15 hrs.
        assert len(weekly) == 1
        assert weekly[0].person_id == "donkey"
        assert weekly[0].total_hours == 15.0
        assert round(weekly[0].games["Dota 2"], 4) == round(600 / 60, 4)

        # Window starts come from the reference snapshots' captured_at.
        assert daily_since == yday_cap
        assert weekly_since == mon_cap

        # Today's snapshot is saved with this run's timestamp.
        assert mock_save.call_args[0][4] == WED.isoformat()

        mock_delete.assert_not_called()  # Wednesday — no cleanup.

    @patch("src.sources.steam.delete_snapshots_before")
    @patch("src.sources.steam.save_snapshot")
    @patch("src.sources.steam.load_snapshot")
    @patch("src.sources.steam.get_owned_games")
    @patch("src.sources.steam.time.sleep")
    def test_first_run_no_snapshots_skips_gracefully(
        self, mock_sleep, mock_games, mock_load, mock_save, mock_delete
    ):
        mock_games.return_value = {"Counter-Strike 2": 1000}
        mock_load.return_value = None

        roster = [{"player_id": "donkey", "name": "Donkey", "steam_id": "100"}]
        with patch("src.sources.steam.PLAYERS", roster):
            daily, weekly, daily_since, weekly_since = collect(WED)

        assert daily == []
        assert weekly == []
        mock_save.assert_called_once()  # Baseline snapshot still saved.

    @patch("src.sources.steam.delete_snapshots_before")
    @patch("src.sources.steam.save_snapshot")
    @patch("src.sources.steam.load_snapshot")
    @patch("src.sources.steam.get_owned_games")
    @patch("src.sources.steam.time.sleep")
    def test_private_profile_skipped(
        self, mock_sleep, mock_games, mock_load, mock_save, mock_delete
    ):
        mock_games.return_value = None  # private profile
        roster = [{"player_id": "donkey", "name": "Donkey", "steam_id": "100"}]
        with patch("src.sources.steam.PLAYERS", roster):
            daily, weekly, daily_since, weekly_since = collect(WED)

        assert daily == []
        assert weekly == []
        mock_save.assert_not_called()

    @patch("src.sources.steam.delete_snapshots_before")
    @patch("src.sources.steam.save_snapshot")
    @patch("src.sources.steam.load_snapshot")
    @patch("src.sources.steam.get_owned_games")
    @patch("src.sources.steam.time.sleep")
    def test_monday_triggers_cleanup(
        self, mock_sleep, mock_games, mock_load, mock_save, mock_delete
    ):
        mock_games.return_value = {"Counter-Strike 2": 1000}
        mock_load.return_value = None

        roster = [{"player_id": "donkey", "name": "Donkey", "steam_id": "100"}]
        with patch("src.sources.steam.PLAYERS", roster):
            collect(MON)  # a Monday

        mock_delete.assert_called_once_with("2026-05-11", "100")

    @patch("src.sources.steam.delete_snapshots_before")
    @patch("src.sources.steam.save_snapshot")
    @patch("src.sources.steam.load_snapshot")
    @patch("src.sources.steam.get_owned_games")
    @patch("src.sources.steam.time.sleep")
    def test_skips_league_only_players(
        self, mock_sleep, mock_games, mock_load, mock_save, mock_delete
    ):
        # A roster row with no steam_id must be ignored by the Steam source.
        mock_games.return_value = {"Counter-Strike 2": 200}
        mock_load.side_effect = lambda date_key, _: (
            {"games": {}} if date_key == "2026-05-12" else None
        )
        roster = [
            {"player_id": "kabir", "name": "Kabir", "riot": {"game_name": "x", "tag_line": "y"}},
            {"player_id": "chris", "name": "Chris", "steam_id": "222"},
        ]
        with patch("src.sources.steam.PLAYERS", roster):
            daily, _, _, _ = collect(WED)

        names = {p.display_name for p in daily}
        assert names == {"Chris"}
        assert mock_games.call_count == 1  # only the Steam-tracked player fetched
