import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from src.config import PLAYERS
from src.riot_api import get_puuid, calculate_hours
from src.discord import send_to_discord


def get_yesterday_timestamps():
    tz = ZoneInfo("America/New_York")
    now = datetime.now(tz)
    today_start = datetime(now.year, now.month, now.day, tzinfo=tz)
    yesterday_start = today_start - timedelta(days=1)
    return int(yesterday_start.timestamp()), int(today_start.timestamp()), yesterday_start, today_start


def build_leaderboard():
    start_ts, end_ts, window_start, window_end = get_yesterday_timestamps()
    fmt = "%b %d %I:%M %p %Z"
    print(f"\nTime window: {window_start.strftime(fmt)} -> {window_end.strftime(fmt)}\n")

    results = []
    for game_name, tag_line in PLAYERS:
        print(f"Processing {game_name}#{tag_line}...")
        puuid = get_puuid(game_name, tag_line)
        if not puuid:
            continue
        time.sleep(1.2)
        hours = calculate_hours(puuid, start_ts, end_ts)
        results.append((game_name, hours))

    results.sort(key=lambda x: x[1], reverse=True)
    return results


if __name__ == "__main__":
    leaderboard = build_leaderboard()
    if not leaderboard:
        print("No data found.")
    else:
        send_to_discord(leaderboard)
        print("\nLeaderboard sent!")
