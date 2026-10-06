import logging
import boto3
import requests

logger = logging.getLogger(__name__)

_ssm = boto3.client("ssm", region_name="us-east-1")
_webhook_url = _ssm.get_parameter(Name="/leaguebot/discord-webhook-url", WithDecryption=True)["Parameter"]["Value"]

_MEDALS = ["\U0001f947", "\U0001f948", "\U0001f949"]  # 🥇 🥈 🥉


def _window_str(start, now):
    # Both bounds are actual datetimes — `start` is the true window start (the previous
    # post/snapshot time, measured, not assumed) and `now` is this posting time. Full
    # timestamps are shown so the window is unambiguous.
    fmt = "%b %d %I:%M %p %Z"
    return f"{start.strftime(fmt)} → {now.strftime(fmt)}"


def send_leaderboard(rows, period, start, now):
    # rows: list[PlayerPlaytime] already sorted by total hours descending.
    # period: "daily" or "weekly" (selects the header). `start`/`now` are the real
    # window bounds used for the label. Renders the top 3 with a per-game breakdown
    # and posts to Discord. Callers guard against empty rows, but we no-op defensively.
    if not rows:
        logger.info(f"No {period} rows — skipping post")
        return

    if period == "weekly":
        header = "\U0001f4c5 Weekly Recap"   # 📅
    else:
        header = "\U0001f3c6 Top Gamers Today"  # 🏆

    message = f"**{header}:**\n_{_window_str(start, now)}_\n\n"
    for i, player in enumerate(rows[:3]):
        message += f"{_MEDALS[i]} {player.display_name} — {player.total_hours:.1f} hrs\n"
        # Games listed most-played first; League and Steam titles sit side by side.
        for game, hours in sorted(player.games.items(), key=lambda g: g[1], reverse=True):
            message += f"   • {game} — {hours:.1f} hrs\n"
        message += "\n"

    _post(message)
    logger.info(f"{period.capitalize()} leaderboard posted to Discord")


def send_notice(message):
    # Plain announcement with no leaderboard (e.g. a snapshot reset day).
    _post(message)
    logger.info("Notice posted to Discord")


def _post(content):
    res = requests.post(_webhook_url, json={"content": content})
    res.raise_for_status()
