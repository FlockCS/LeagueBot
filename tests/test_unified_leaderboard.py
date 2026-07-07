from datetime import date
from unittest.mock import patch, MagicMock
from src.models import PlayerPlaytime
from src.unified_leaderboard import build


def _source(daily, weekly):
    # A stand-in source module: build() only calls source.collect(today).
    src = MagicMock()
    src.collect.return_value = (daily, weekly)
    return src


class TestBuild:
    def test_merges_same_person_across_sources(self):
        steam = _source(
            daily=[PlayerPlaytime("1", "Veesh", {"Counter-Strike 2": 2.2}),
                   PlayerPlaytime("2", "Manish", {"Dota 2": 3.1})],
            weekly=[],
        )
        riot = _source(
            daily=[PlayerPlaytime("1", "Veesh", {"League of Legends": 4.0})],
            weekly=[],
        )

        with patch("src.unified_leaderboard.SOURCES", [steam, riot]):
            daily, _ = build(date(2026, 5, 13))

        # Veesh's League + Steam hours collapse into one row, sorted to the top.
        assert daily[0].person_id == "1"
        assert daily[0].games == {"Counter-Strike 2": 2.2, "League of Legends": 4.0}
        assert round(daily[0].total_hours, 2) == 6.2
        assert daily[1].person_id == "2"
        assert round(daily[1].total_hours, 2) == 3.1

    def test_sorts_by_total_hours_descending(self):
        steam = _source(
            daily=[PlayerPlaytime("a", "A", {"G": 1.0}),
                   PlayerPlaytime("b", "B", {"G": 9.0}),
                   PlayerPlaytime("c", "C", {"G": 5.0})],
            weekly=[],
        )
        with patch("src.unified_leaderboard.SOURCES", [steam]):
            daily, _ = build(date(2026, 5, 13))

        assert [p.display_name for p in daily] == ["B", "C", "A"]

    def test_does_not_mutate_source_rows(self):
        # The merge must copy, never mutate a source's returned PlayerPlaytime.
        shared = PlayerPlaytime("1", "Veesh", {"Counter-Strike 2": 2.0})
        steam = _source(daily=[shared], weekly=[])
        riot = _source(daily=[PlayerPlaytime("1", "Veesh", {"League of Legends": 3.0})], weekly=[])

        with patch("src.unified_leaderboard.SOURCES", [steam, riot]):
            build(date(2026, 5, 13))

        assert shared.games == {"Counter-Strike 2": 2.0}

    def test_weekly_merges_independently_of_daily(self):
        steam = _source(
            daily=[PlayerPlaytime("1", "V", {"CS2": 1.0})],
            weekly=[PlayerPlaytime("1", "V", {"CS2": 10.0})],
        )
        riot = _source(
            daily=[],
            weekly=[PlayerPlaytime("1", "V", {"League of Legends": 5.0})],
        )
        with patch("src.unified_leaderboard.SOURCES", [steam, riot]):
            daily, weekly = build(date(2026, 5, 13))

        assert round(daily[0].total_hours, 2) == 1.0
        assert round(weekly[0].total_hours, 2) == 15.0
