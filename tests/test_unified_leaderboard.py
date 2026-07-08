from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch, MagicMock
from src.models import PlayerPlaytime
from src.unified_leaderboard import build

_ET = ZoneInfo("America/New_York")
NOW = datetime(2026, 5, 13, 10, 0, tzinfo=_ET)   # Wednesday 10 AM ET


def _steam(daily, weekly, daily_since=None, weekly_since=None):
    # Stand-in Steam source: collect(now) -> (daily, weekly, daily_since, weekly_since).
    m = MagicMock()
    m.collect.return_value = (daily, weekly, daily_since, weekly_since)
    return m


def _riot(daily, weekly):
    # Stand-in Riot source: collect(now, window_start) -> (daily, weekly).
    m = MagicMock()
    m.collect.return_value = (daily, weekly)
    return m


def _patch(steam, riot):
    return patch.multiple("src.unified_leaderboard", steam=steam, riot=riot)


class TestBuild:
    def test_merges_same_person_across_sources(self):
        steam = _steam(
            daily=[PlayerPlaytime("1", "Veesh", {"Counter-Strike 2": 2.2}),
                   PlayerPlaytime("2", "Manish", {"Dota 2": 3.1})],
            weekly=[],
        )
        riot = _riot(
            daily=[PlayerPlaytime("1", "Veesh", {"League of Legends": 4.0})],
            weekly=[],
        )

        with _patch(steam, riot):
            daily, _weekly, _ds, _ws = build(NOW)

        # Veesh's League + Steam hours collapse into one row, sorted to the top.
        assert daily[0].person_id == "1"
        assert daily[0].games == {"Counter-Strike 2": 2.2, "League of Legends": 4.0}
        assert round(daily[0].total_hours, 2) == 6.2
        assert daily[1].person_id == "2"
        assert round(daily[1].total_hours, 2) == 3.1

    def test_sorts_by_total_hours_descending(self):
        steam = _steam(
            daily=[PlayerPlaytime("a", "A", {"G": 1.0}),
                   PlayerPlaytime("b", "B", {"G": 9.0}),
                   PlayerPlaytime("c", "C", {"G": 5.0})],
            weekly=[],
        )
        with _patch(steam, _riot([], [])):
            daily, _weekly, _ds, _ws = build(NOW)

        assert [p.display_name for p in daily] == ["B", "C", "A"]

    def test_does_not_mutate_source_rows(self):
        # The merge must copy, never mutate a source's returned PlayerPlaytime.
        shared = PlayerPlaytime("1", "Veesh", {"Counter-Strike 2": 2.0})
        steam = _steam(daily=[shared], weekly=[])
        riot = _riot(daily=[PlayerPlaytime("1", "Veesh", {"League of Legends": 3.0})], weekly=[])

        with _patch(steam, riot):
            build(NOW)

        assert shared.games == {"Counter-Strike 2": 2.0}

    def test_weekly_merges_independently_of_daily(self):
        steam = _steam(
            daily=[PlayerPlaytime("1", "V", {"CS2": 1.0})],
            weekly=[PlayerPlaytime("1", "V", {"CS2": 10.0})],
        )
        riot = _riot(
            daily=[],
            weekly=[PlayerPlaytime("1", "V", {"League of Legends": 5.0})],
        )
        with _patch(steam, riot):
            daily, weekly, _ds, _ws = build(NOW)

        assert round(daily[0].total_hours, 2) == 1.0
        assert round(weekly[0].total_hours, 2) == 15.0

    def test_window_start_from_steam_drives_riot_and_return(self):
        # Steam reports the real window starts; build returns them and passes the
        # daily start to Riot as its query window.
        daily_since = datetime(2026, 5, 12, 9, 30, tzinfo=_ET)
        weekly_since = datetime(2026, 5, 11, 9, 15, tzinfo=_ET)
        steam = _steam(daily=[], weekly=[], daily_since=daily_since, weekly_since=weekly_since)
        riot = _riot([], [])

        with _patch(steam, riot):
            _daily, _weekly, ds, ws = build(NOW)

        assert ds == daily_since
        assert ws == weekly_since
        riot.collect.assert_called_once_with(NOW, daily_since)

    def test_falls_back_when_no_reference_snapshot(self):
        # With no Steam reference (daily_since=None), the daily window falls back to
        # 24h before now and Riot is queried over that.
        steam = _steam(daily=[], weekly=[], daily_since=None, weekly_since=None)
        riot = _riot([], [])

        with _patch(steam, riot):
            _daily, _weekly, ds, _ws = build(NOW)

        assert ds == NOW - timedelta(days=1)
        riot.collect.assert_called_once_with(NOW, NOW - timedelta(days=1))
