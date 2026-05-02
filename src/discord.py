import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from src.config import WEBHOOK_URL


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

    res = requests.post(WEBHOOK_URL, json={"content": message})
    res.raise_for_status()
