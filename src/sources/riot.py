# League (Riot) playtime source. Unlike Steam, Riot's match API returns exact game
# durations for an arbitrary time window, so:
#   daily  = live query of yesterday's matches, summed to hours
#   weekly = SUM of the last 7 persisted daily records (src/riot_snapshot.py)
# We persist each day's computed hours and sum them for the weekly recap rather than
# re-querying a week of matches, which would blow the 5-min Lambda timeout under the
# Riot dev-key rate limit (100 req / 2 min).
#
# All date math is Eastern time to match when the Lambda fires (9 AM ET).

import logging
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from src.config import PLAYERS
from src.models import PlayerPlaytime
from src.riot_api import get_puuid, calculate_hours
from src.riot_snapshot import save_daily, load_week, delete_daily_before

logger = logging.getLogger(__name__)

GAME_NAME = "League of Legends"


def _riot_players():
    # Roster rows tracked on League (those carrying a riot handle).
    return [p for p in PLAYERS if p.get("riot")]


def _week_start(today):
    return today - timedelta(days=today.weekday())


def _day_bounds(today):
    # Epoch-second window for "yesterday" in Eastern time. Riot's match query takes
    # startTime/endTime as UNIX seconds.
    tz = ZoneInfo("America/New_York")
    today_start = datetime(today.year, today.month, today.day, tzinfo=tz)
    yesterday_start = today_start - timedelta(days=1)
    return int(yesterday_start.timestamp()), int(today_start.timestamp())


def _daily(today):
    # Live-query yesterday's League hours per player and persist each result so the
    # weekly recap can sum it later.
    start_ts, end_ts = _day_bounds(today)
    logger.info(f"Collecting League playtime for {today}")
    results = []

    for player in _riot_players():
        player_id = player["player_id"]
        name = player["name"]
        game_name = player["riot"]["game_name"]
        tag_line = player["riot"]["tag_line"]

        puuid = get_puuid(game_name, tag_line)
        if not puuid:
            logger.warning(f"Skipping {name} ({game_name}#{tag_line}): no PUUID")
            continue
        time.sleep(1.2)

        hours = calculate_hours(puuid, start_ts, end_ts)
        if hours > 0:
            save_daily(today, player_id, name, hours)
            results.append(PlayerPlaytime(
                person_id=player_id,
                display_name=name,
                games={GAME_NAME: hours},
            ))
            logger.info(f"{name}: {hours:.1f} League hrs yesterday")

    return results


def _weekly(today):
    # Sum each player's persisted daily records from this Monday forward. Missing
    # days simply contribute nothing (graceful bootstrap over the first week).
    week_start = _week_start(today)
    weekly = []

    for player in _riot_players():
        player_id = player["player_id"]
        records = load_week(week_start, player_id)
        total = sum(float(r["hours"]) for r in records)
        if total > 0:
            weekly.append(PlayerPlaytime(
                person_id=player_id,
                display_name=player["name"],
                games={GAME_NAME: total},
            ))
            logger.info(f"{player['name']}: {total:.1f} League hrs this week")

    # Monday cleanup: drop last week's records after the recap window rolls over,
    # mirroring the Steam snapshot cleanup.
    if today.weekday() == 0:
        logger.info("Monday cleanup: deleting League records before today")
        for player in _riot_players():
            delete_daily_before(today, player["player_id"])

    return weekly


def collect(today):
    # Returns (daily, weekly). _daily persists today's records first so _weekly's
    # sum includes them.
    daily = _daily(today)
    weekly = _weekly(today)
    return daily, weekly
