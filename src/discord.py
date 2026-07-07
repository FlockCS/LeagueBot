import logging
import boto3
import requests
from datetime import timedelta

logger = logging.getLogger(__name__)

_ssm = boto3.client("ssm", region_name="us-east-1")
_webhook_url = _ssm.get_parameter(Name="/leaguebot/discord-webhook-url", WithDecryption=True)["Parameter"]["Value"]

_MEDALS = ["\U0001f947", "\U0001f948", "\U0001f949"]  # 🥇 🥈 🥉


def _window_str(period, now):
    # `now` is the posting-time datetime. Daily covers the trailing 24h (previous
    # post → this post); weekly covers this Monday's posting time → now. Both show
    # full timestamps so the boundaries are unambiguous (and both sources use the
    # same span).
    fmt = "%b %d %I:%M %p %Z"
    if period == "weekly":
        start = now - timedelta(days=now.weekday())
    else:
        start = now - timedelta(days=1)
    return f"{start.strftime(fmt)} → {now.strftime(fmt)}"


def send_leaderboard(rows, period, now):
    # rows: list[PlayerPlaytime] already sorted by total hours descending.
    # period: "daily" or "weekly". `now` is the posting-time datetime used to label
    # the window. Renders the top 3 with a per-game breakdown and posts to Discord.
    # Callers guard against empty rows, but we no-op defensively.
    if not rows:
        logger.info(f"No {period} rows — skipping post")
        return

    if period == "weekly":
        header = "\U0001f4c5 Weekly Recap"   # 📅
    else:
        header = "\U0001f3c6 Top Gamers Today"  # 🏆

    message = f"**{header}:**\n_{_window_str(period, now)}_\n\n"
    for i, player in enumerate(rows[:3]):
        message += f"{_MEDALS[i]} {player.display_name} — {player.total_hours:.1f} hrs\n"
        # Games listed most-played first; League and Steam titles sit side by side.
        for game, hours in sorted(player.games.items(), key=lambda g: g[1], reverse=True):
            message += f"   • {game} — {hours:.1f} hrs\n"
        message += "\n"

    res = requests.post(_webhook_url, json={"content": message})
    res.raise_for_status()
    logger.info(f"{period.capitalize()} leaderboard posted to Discord")
