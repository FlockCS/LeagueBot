import boto3
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

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


def send_steam_to_discord(daily_results, weekly_results, today, yesterday):
    # Both lists empty means there's literally nothing to report (e.g. first run
    # ever — no yesterday snapshot, no week start). Skip posting to avoid spam.
    if not daily_results and not weekly_results:
        return

    fmt = "%b %d"
    medals = ["\U0001f947", "\U0001f948", "\U0001f949"]  # 🥇 🥈 🥉

    # \U0001f3ae is the 🎮 video game emoji.
    message = f"**\U0001f3ae Top Steam Players Today:**\n_{yesterday.strftime(fmt)} → {today.strftime(fmt)}_\n\n"

    # Daily section: top 3 players + top 3 games each. daily_results items are
    # (name, total_hours, [(game_name, game_hours), ...]) from steam_leaderboard.py.
    for i, (name, hours, top_games) in enumerate(daily_results[:3]):
        message += f"{medals[i]} {name} — {hours:.1f} hrs\n"
        for game, game_hours in top_games:
            message += f"   • {game} — {game_hours:.1f} hrs\n"
        message += "\n"

    # Weekly section is the running total since Monday. On Mondays this list is
    # empty (week just reset) — we skip the header entirely rather than printing
    # an empty "This Week So Far" block.
    if weekly_results:
        message += "**\U0001f4c5 This Week So Far:**\n\n"  # 📅
        for i, (name, hours) in enumerate(weekly_results[:3]):
            message += f"{medals[i]} {name} — {hours:.1f} hrs\n"

    res = requests.post(_webhook_url, json={"content": message})
    res.raise_for_status()
