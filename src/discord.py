import logging
import boto3
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

_ssm = boto3.client("ssm", region_name="us-east-1")
_webhook_url = _ssm.get_parameter(Name="/leaguebot/discord-webhook-url", WithDecryption=True)["Parameter"]["Value"]


def send_to_discord(results):
    tz = ZoneInfo("America/New_York")
    now = datetime.now(tz)
    today_start = datetime(now.year, now.month, now.day, tzinfo=tz)
    yesterday_start = today_start - timedelta(days=1)
    fmt = "%b %d %I:%M %p %Z"
    window_str = f"{yesterday_start.strftime(fmt)} → {today_start.strftime(fmt)}"

    message = f"**\U0001f3c6 Top 3 League Grind:**\n_{window_str}_\n\n"
    medals = ["\U0001f947", "\U0001f948", "\U0001f949"]

    for i, (name, hours) in enumerate(results[:3]):
        message += f"{medals[i]} {name} — {hours:.1f} hrs\n"

    res = requests.post(_webhook_url, json={"content": message})
    res.raise_for_status()


def send_steam_to_discord(leaderboard):
    # Sunday (weekday=6) posts the weekly recap; Mon–Sat post the daily leaderboard.
    # Splitting by day avoids competing sections in a single message.
    today = leaderboard.today
    medals = ["\U0001f947", "\U0001f948", "\U0001f949"]  # 🥇 🥈 🥉

    if today.weekday() == 6:
        if not leaderboard.weekly_results:
            logger.info("Sunday with no weekly results — skipping post")
            return
        logger.info(f"Posting Steam weekly recap ({len(leaderboard.weekly_results)} players)")
        message = "**\U0001f4c5 Steam Weekly Recap:**\n\n"  # 📅
        for i, (name, hours) in enumerate(leaderboard.weekly_results[:3]):
            message += f"{medals[i]} {name} — {hours:.1f} hrs\n"
    else:
        if not leaderboard.daily_results:
            logger.info(f"{today.strftime('%A')} with no daily results — skipping post")
            return
        logger.info(f"Posting Steam daily leaderboard ({len(leaderboard.daily_results)} players)")
        yesterday = today - timedelta(days=1)
        fmt = "%b %d"
        # \U0001f3ae is the 🎮 video game emoji.
        message = f"**\U0001f3ae Top Steam Players Today:**\n_{yesterday.strftime(fmt)} → {today.strftime(fmt)}_\n\n"
        # daily_results items are (name, total_hours, [(game_name, game_hours), ...]).
        for i, (name, hours, top_games) in enumerate(leaderboard.daily_results[:3]):
            message += f"{medals[i]} {name} — {hours:.1f} hrs\n"
            for game, game_hours in top_games:
                message += f"   • {game} — {game_hours:.1f} hrs\n"
            message += "\n"

    res = requests.post(_webhook_url, json={"content": message})
    res.raise_for_status()
    logger.info("Steam message posted to Discord")
