# Orchestrates the Steam side of the daily message. The flow each morning:
#
#   For each Steam player in config.STEAM_PLAYERS:
#     1. Fetch persona name (GetPlayerSummaries)
#     2. Fetch current per-game lifetime minutes (GetOwnedGames)
#     3. Save today's snapshot to DynamoDB
#     4. Diff today vs yesterday's snapshot → daily delta (per-game + total)
#     5. Diff today vs Monday's snapshot → weekly delta (total only)
#   Sort daily by total hrs desc, sort weekly by total hrs desc.
#   On Mondays, after computing, delete snapshots older than today (start fresh week).
#
# Why this works: Steam's API only gives LIFETIME totals, not "played today." So we
# store one snapshot per player per day and subtract — that gives us per-period hours.

import logging
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from src.config import STEAM_PLAYERS
from src.steam_api import get_player_status, get_owned_games
from src.steam_snapshot import save_snapshot, load_snapshot, delete_snapshots_before

logger = logging.getLogger(__name__)


@dataclass
class SteamLeaderboard:
    # daily_results:  [(name, daily_hours,  [(game, game_hours), ...]), ...]
    # weekly_results: [(name, weekly_hours, [(game, game_hours), ...]), ...]
    today: date
    daily_results: list = field(default_factory=list)
    weekly_results: list = field(default_factory=list)


def _date_str(d): return d.strftime("%Y-%m-%d")


def _week_start(today): return today - timedelta(days=today.weekday())


def _game_deltas(today_games, yesterday_games):
    # For each game played today, compute how many minutes were added since yesterday.
    # New games (not in yesterday's snapshot) count their full today playtime as the delta.
    # Filter out non-positive deltas — a game shouldn't shrink, but defensive in case
    # of API weirdness or replaced accounts.
    deltas = {}
    for game, minutes in today_games.items():
        prev = int(yesterday_games.get(game, 0))
        delta = int(minutes) - prev
        if delta > 0:
            deltas[game] = delta
    return deltas


def build_steam_leaderboard():
    # All time math happens in Eastern time so the "day" boundary matches when
    # the Lambda fires (9 AM ET). Using UTC here would put the day boundary
    # mid-morning ET, which would split sessions across two "days."
    tz = ZoneInfo("America/New_York")
    now = datetime.now(tz)
    today = now.date()
    yesterday = today - timedelta(days=1)
    week_start = _week_start(today)
    today_key = _date_str(today)
    yesterday_key = _date_str(yesterday)
    week_start_key = _date_str(week_start)

    logger.info(f"Building Steam leaderboard for {today}")
    daily_results = []
    weekly_results = []

    for player in STEAM_PLAYERS:
        steam_id = player["steam_id"]

        # Step 1: get the persona name.
        status = get_player_status(steam_id)
        if not status:
            logger.warning(f"Skipping {steam_id}: failed to fetch player status")
            continue
        name = status["name"]

        # Step 2: get per-game lifetime totals.
        games = get_owned_games(steam_id)
        if games is None:
            logger.warning(f"Skipping {name}: no games visible")
            continue

        # Step 3: persist today's snapshot. Always done, even if there's no yesterday
        # to diff against yet — that's how we bootstrap the very first run.
        save_snapshot(today_key, steam_id, name, games)
        logger.debug(f"Saved snapshot for {name} ({steam_id}): {len(games)} games, {sum(games.values())} min total")

        # Step 4: daily delta.
        yesterday_snap = load_snapshot(yesterday_key, steam_id)
        if yesterday_snap:
            deltas = _game_deltas(games, yesterday_snap.get("games", {}))
            daily_total = sum(deltas.values())
            if daily_total > 0:
                # Top 3 games this player played today, by minutes played.
                top_games = sorted(deltas.items(), key=lambda x: x[1], reverse=True)[:3]
                daily_results.append((name, daily_total / 60, [(g, m / 60) for g, m in top_games]))
                logger.info(f"{name}: {daily_total / 60:.1f} hrs today ({len(deltas)} games)")
        else:
            logger.debug(f"No yesterday snapshot for {name} — first run or bootstrapping")

        # Step 5: weekly delta. Compare against this Monday's snapshot.
        # On Mondays, week_snap == today's snapshot we just wrote → delta is 0
        # → player won't appear in weekly_results (filtered below).
        week_snap = load_snapshot(week_start_key, steam_id)
        if week_snap:
            week_deltas = _game_deltas(games, week_snap.get("games", {}))
            weekly_total = sum(week_deltas.values())
            if weekly_total > 0:
                top_games = sorted(week_deltas.items(), key=lambda x: x[1], reverse=True)[:3]
                weekly_results.append((name, weekly_total / 60, [(g, m / 60) for g, m in top_games]))
                logger.info(f"{name}: {weekly_total / 60:.1f} hrs this week ({len(week_deltas)} games)")

        # One sleep per player keeps us polite to Steam's API without being wasteful.
        time.sleep(1)

    daily_results.sort(key=lambda x: x[1], reverse=True)
    weekly_results.sort(key=lambda x: x[1], reverse=True)

    logger.info(f"Leaderboard complete: {len(daily_results)} daily, {len(weekly_results)} weekly")

    # Monday cleanup: after the message is built, drop old snapshots so the table
    # stays small. Today's snapshot is preserved (it's the anchor for the new week).
    if today.weekday() == 0:
        logger.info("Monday cleanup: deleting snapshots before today")
        for player in STEAM_PLAYERS:
            delete_snapshots_before(today_key, player["steam_id"])

    return SteamLeaderboard(today=today, daily_results=daily_results, weekly_results=weekly_results)
