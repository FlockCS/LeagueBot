# The universal leaderboard: one ranking across every source and every game.
# Each source (see src/sources/) yields normalized PlayerPlaytime rows for the day
# and the week. We merge rows that share a person_id — so a player's League hours
# and Steam hours collapse into a single entry with all their games listed — then
# sort by total hours descending.

import logging
from src.models import PlayerPlaytime
from src.sources import steam, riot

logger = logging.getLogger(__name__)

# Order here only affects which source is visited first; the merge is commutative.
SOURCES = [steam, riot]


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
    # Collect from every source once, merging per person. `now` is the posting-time
    # datetime; each source derives its window from it. Returns
    # (daily_rows, weekly_rows), each a list[PlayerPlaytime] sorted by total desc.
    daily_by_person = {}
    weekly_by_person = {}

    for source in SOURCES:
        daily, weekly = source.collect(now)
        _merge_into(daily_by_person, daily)
        _merge_into(weekly_by_person, weekly)

    daily_rows = _sorted(daily_by_person)
    weekly_rows = _sorted(weekly_by_person)
    logger.info(f"Unified leaderboard: {len(daily_rows)} daily, {len(weekly_rows)} weekly")
    return daily_rows, weekly_rows
