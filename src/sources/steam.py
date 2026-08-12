# Steam playtime source. Steam's API only exposes LIFETIME per-game totals, so we
# store one snapshot per player per day (src/steam_snapshot.py) and diff:
#   daily  = today's totals - yesterday's snapshot
#   weekly = today's totals - this Monday's snapshot
# Each diff becomes a PlayerPlaytime keyed by the person's canonical player_id, so
# the unified aggregator can merge it with the same person's League playtime.
#
# The snapshot table is keyed by steam_id (Steam's own natural key); player_id is the
# cross-source identity applied here at the leaderboard layer.
#
# All date math is Eastern time so the "day" boundary matches when the Lambda fires
# (9 AM ET); UTC would split sessions across two days.

import logging
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from src.config import PLAYERS

_ET = ZoneInfo("America/New_York")
from src.models import PlayerPlaytime
from src.steam_api import get_owned_games
from src.steam_snapshot import save_snapshot, load_snapshot, delete_snapshots_before

logger = logging.getLogger(__name__)


def _steam_players():
    # Roster rows tracked on Steam (those carrying at least one steam_ids entry).
    return [p for p in PLAYERS if p.get("steam_ids")]


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


def _playtime_from_deltas(player_id, name, deltas):
    # Convert a {game: minutes} delta map into a PlayerPlaytime with hours.
    return PlayerPlaytime(
        person_id=player_id,
        display_name=name,
        games={g: m / 60 for g, m in deltas.items()},
    )


def _earliest(captured_ats):
    # Parse ISO-8601 capture timestamps and return the earliest as a datetime, or
    # None if none are present (e.g. pre-existing snapshots saved before captured_at
    # was added). The earliest reference is the true start of the diff window.
    # Re-attach the ET zone so the label renders "EDT"/"EST" (fromisoformat yields a
    # bare UTC offset otherwise).
    times = [datetime.fromisoformat(c).astimezone(_ET) for c in captured_ats if c]
    return min(times) if times else None


def collect(now):
    # Single pass over every Steam-tracked player: fetch, snapshot, and compute both
    # the daily and weekly delta in one loop so we only hit the Steam API once per run.
    # `now` is the posting-time datetime; today's snapshot is taken now and diffed
    # against the reference snapshot (yesterday's for daily, Monday's for weekly).
    #
    # Returns (daily, weekly, daily_since, weekly_since) where the *_since values are
    # the actual capture times of the reference snapshots — the true window starts —
    # or None if those snapshots predate captured_at (first run after this change).
    today = now.date()
    yesterday = today - timedelta(days=1)
    week_start = _week_start(today)
    today_key = _date_str(today)
    yesterday_key = _date_str(yesterday)
    week_start_key = _date_str(week_start)
    now_iso = now.isoformat()

    logger.info(f"Collecting Steam playtime for {today}")
    daily = []
    weekly = []
    daily_ref_times = []   # captured_at of every yesterday snapshot we diffed against
    weekly_ref_times = []  # captured_at of every Monday snapshot we diffed against

    for player in _steam_players():
        steam_ids = player["steam_ids"]
        primary_id = steam_ids[0]  # DynamoDB snapshot key — see PLAYERS comment in config.py
        player_id = player["player_id"]
        name = player["name"]

        # Fetch all accounts and merge into one game map. We must have a complete
        # picture before writing anything: a partial merge (one account missing)
        # would undercount today's snapshot, and the next run would then diff the
        # recovered account's full lifetime playtime as "one day's hours". So if
        # any account is unreachable we skip the player entirely for this run.
        merged_games = {}
        all_fetched = True
        for steam_id in steam_ids:
            games = get_owned_games(steam_id)
            if games is None:
                logger.warning(f"Skipping {name} ({steam_id}): no games visible — skipping all accounts to avoid partial snapshot")
                all_fetched = False
                time.sleep(1)
                break
            for game, minutes in games.items():
                merged_games[game] = merged_games.get(game, 0) + minutes
            time.sleep(1)

        if not all_fetched:
            continue

        # Always persist today's merged snapshot under the primary steam_id.
        save_snapshot(today_key, primary_id, name, merged_games, now_iso)
        logger.debug(f"Saved merged snapshot for {name} ({len(steam_ids)} account(s)): {len(merged_games)} games")

        yesterday_snap = load_snapshot(yesterday_key, primary_id)
        if yesterday_snap:
            daily_ref_times.append(yesterday_snap.get("captured_at"))
            deltas = _game_deltas(merged_games, yesterday_snap.get("games", {}))
            if deltas:
                daily.append(_playtime_from_deltas(player_id, name, deltas))
                logger.info(f"{name}: {sum(deltas.values()) / 60:.1f} hrs today ({len(deltas)} games)")

        # Weekly delta vs this Monday's snapshot. On Mondays the week snapshot is the
        # one we just wrote, so the delta is empty and the player is omitted.
        week_snap = load_snapshot(week_start_key, primary_id)
        if week_snap:
            weekly_ref_times.append(week_snap.get("captured_at"))
            week_deltas = _game_deltas(merged_games, week_snap.get("games", {}))
            if week_deltas:
                weekly.append(_playtime_from_deltas(player_id, name, week_deltas))
                logger.info(f"{name}: {sum(week_deltas.values()) / 60:.1f} hrs this week")

    # Monday cleanup: drop old snapshots after computing (today's is preserved as the
    # anchor for the new week). One call per player — the merged snapshot lives under
    # the primary steam_id.
    if today.weekday() == 0:
        logger.info("Monday cleanup: deleting Steam snapshots before today")
        for player in _steam_players():
            delete_snapshots_before(today_key, player["steam_ids"][0])

    return daily, weekly, _earliest(daily_ref_times), _earliest(weekly_ref_times)
