# The universal leaderboard: one ranking across every source and every game.
# Each source (see src/sources/) yields normalized PlayerPlaytime rows for the day
# and the week. We merge rows that share a person_id — so a player's League hours
# and Steam hours collapse into a single entry with all their games listed — then
# sort by total hours descending.
#
# The daily window is anchored to Steam: Steam can only report the span between the
# reference snapshot it diffed against and now, so it defines the true window start.
# Riot (whose query window is flexible) is then asked to cover that same span, so the
# whole board — and its printed timestamps — reflect one honest window.

import logging
from datetime import timedelta
from src.models import PlayerPlaytime
from src.sources import steam, riot

logger = logging.getLogger(__name__)


def _merge_into(by_person, rows):
    for row in rows:
        existing = by_person.get(row.person_id)
        if existing:
            existing.merge(row)
        else:
            # Copy so we never mutate a source's returned object during merge.
            by_person[row.person_id] = PlayerPlaytime(
                person_id=row.person_id,
                display_name=row.display_name,
                games=dict(row.games),
            )


def _sorted(by_person):
    return sorted(by_person.values(), key=lambda p: p.total_hours, reverse=True)


def build(now):
    # `now` is the posting-time datetime. Steam runs first and reports the real start
    # of each window (the capture time of the snapshot it diffed against); Riot is then
    # queried over that same span so both sources agree. Returns
    #   (daily_rows, weekly_rows, daily_start, weekly_start)
    # where the *_start datetimes are the true window starts used for the labels.
    steam_daily, steam_weekly, daily_since, weekly_since = steam.collect(now)

    # Fall back to a nominal window only when there's no reference snapshot to anchor
    # to (e.g. the first run after this change, or no Steam players): daily -> 24h ago,
    # weekly -> this Monday at the current time.
    daily_start = daily_since or (now - timedelta(days=1))
    weekly_start = weekly_since or (now - timedelta(days=now.weekday()))

    riot_daily, riot_weekly = riot.collect(now, daily_start)

    daily_by_person = {}
    weekly_by_person = {}
    _merge_into(daily_by_person, steam_daily)
    _merge_into(daily_by_person, riot_daily)
    _merge_into(weekly_by_person, steam_weekly)
    _merge_into(weekly_by_person, riot_weekly)

    daily_rows = _sorted(daily_by_person)
    weekly_rows = _sorted(weekly_by_person)
    logger.info(f"Unified leaderboard: {len(daily_rows)} daily, {len(weekly_rows)} weekly")
    return daily_rows, weekly_rows, daily_start, weekly_start
