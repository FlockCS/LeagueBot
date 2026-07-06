# Steam playtime source. Steam's API only exposes LIFETIME per-game totals, so we
# store one snapshot per player per day (src/steam_snapshot.py) and diff:
#   daily  = today's totals - yesterday's snapshot
#   weekly = today's totals - this Monday's snapshot
# Each diff becomes a PlayerPlaytime keyed by the player's Discord id, so the
# unified aggregator can merge it with the same person's League playtime.
#
# All date math is Eastern time so the "day" boundary matches when the Lambda fires
# (9 AM ET); UTC would split sessions across two days.

import logging
import time
from datetime import timedelta
from src.config import STEAM_PLAYERS
from src.models import PlayerPlaytime
from src.steam_api import get_player_status, get_owned_games
from src.steam_snapshot import save_snapshot, load_snapshot, delete_snapshots_before

logger = logging.getLogger(__name__)


def _date_str(d):
    return d.strftime("%Y-%m-%d")


def _week_start(today):
    return today - timedelta(days=today.weekday())


def _game_deltas(today_games, yesterday_games):
    # Minutes each game gained since the reference snapshot. New games (absent from
    # the reference) count their full playtime. Non-positive deltas are dropped —
    # a game shouldn't shrink, but guard against API weirdness / replaced accounts.
    deltas = {}
    for game, minutes in today_games.items():
        prev = int(yesterday_games.get(game, 0))
        delta = int(minutes) - prev
        if delta > 0:
            deltas[game] = delta
    return deltas


def _playtime_from_deltas(discord_id, name, deltas):
    # Convert a {game: minutes} delta map into a PlayerPlaytime with hours.
    return PlayerPlaytime(
        person_id=discord_id,
        display_name=name,
        games={g: m / 60 for g, m in deltas.items()},
    )


def collect(today):
    # Single pass over every Steam player: fetch, snapshot, and compute both the
    # daily and weekly delta in one loop so we only hit the Steam API once per run.
    # Returns (daily: list[PlayerPlaytime], weekly: list[PlayerPlaytime]).
    yesterday = today - timedelta(days=1)
    week_start = _week_start(today)
    today_key = _date_str(today)
    yesterday_key = _date_str(yesterday)
    week_start_key = _date_str(week_start)

    logger.info(f"Collecting Steam playtime for {today}")
    daily = []
    weekly = []

    for player in STEAM_PLAYERS:
        steam_id = player["steam_id"]
        discord_id = player["discord_id"]

        status = get_player_status(steam_id)
        if not status:
            logger.warning(f"Skipping {steam_id}: failed to fetch player status")
            continue
        name = status["name"]

        games = get_owned_games(steam_id)
        if games is None:
            logger.warning(f"Skipping {name}: no games visible")
            continue

        # Always persist today's snapshot — this is how the very first run bootstraps.
        save_snapshot(today_key, steam_id, name, games)
        logger.debug(f"Saved snapshot for {name} ({steam_id}): {len(games)} games")

        yesterday_snap = load_snapshot(yesterday_key, steam_id)
        if yesterday_snap:
            deltas = _game_deltas(games, yesterday_snap.get("games", {}))
            if deltas:
                daily.append(_playtime_from_deltas(discord_id, name, deltas))
                logger.info(f"{name}: {sum(deltas.values()) / 60:.1f} hrs today ({len(deltas)} games)")

        # Weekly delta vs this Monday's snapshot. On Mondays the week snapshot is the
        # one we just wrote, so the delta is empty and the player is omitted.
        week_snap = load_snapshot(week_start_key, steam_id)
        if week_snap:
            week_deltas = _game_deltas(games, week_snap.get("games", {}))
            if week_deltas:
                weekly.append(_playtime_from_deltas(discord_id, name, week_deltas))
                logger.info(f"{name}: {sum(week_deltas.values()) / 60:.1f} hrs this week")

        # One sleep per player keeps us polite to Steam's API.
        time.sleep(1)

    # Monday cleanup: drop old snapshots after computing (today's is preserved as the
    # anchor for the new week).
    if today.weekday() == 0:
        logger.info("Monday cleanup: deleting Steam snapshots before today")
        for player in STEAM_PLAYERS:
            delete_snapshots_before(today_key, player["steam_id"])

    return daily, weekly
