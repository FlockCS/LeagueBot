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
from src.config import PLAYERS
from src.models import PlayerPlaytime
from src.sources import steam, riot

logger = logging.getLogger(__name__)

# No one plays more hours than the window actually contains. A row that exceeds
# this is a data glitch (e.g. a snapshot keying bug, a clock issue) rather than
# real playtime, so it's dropped from the board instead of showing an impossible
# number — the same failure mode that motivated keying snapshots by appid.
MAX_DAILY_HOURS = 24
MAX_WEEKLY_HOURS = 24 * 7


def _drop_implausible(by_person, max_hours, window):
    for person_id, row in list(by_person.items()):
        if row.total_hours > max_hours:
            logger.warning(
                f"Dropping {row.display_name} from {window}: {row.total_hours:.1f} hrs exceeds "
                f"the {max_hours}h plausible max — likely a data glitch, not real playtime"
            )
            del by_person[person_id]


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
    #   (daily_rows, weekly_rows, daily_start, weekly_start, resetting)
    # where the *_start datetimes are the true window starts used for the labels, and
    # `resetting` is True when Steam had no baseline to diff against (see below).
    steam_daily, steam_weekly, daily_since, weekly_since = steam.collect(now)

    # Steam-tracked players exist but none has a reference snapshot: the snapshot store
    # was just wiped or migrated, so the board would be League-only and misstate Steam
    # playtime. The handler announces a rebuild instead of posting it.
    resetting = any(p.get("steam_ids") for p in PLAYERS) and daily_since is None

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

    _drop_implausible(daily_by_person, MAX_DAILY_HOURS, "daily")
    _drop_implausible(weekly_by_person, MAX_WEEKLY_HOURS, "weekly")

    daily_rows = _sorted(daily_by_person)
    weekly_rows = _sorted(weekly_by_person)
    logger.info(f"Unified leaderboard: {len(daily_rows)} daily, {len(weekly_rows)} weekly")
    return daily_rows, weekly_rows, daily_start, weekly_start, resetting
