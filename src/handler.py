# Lambda entry point. AWS EventBridge fires this once per day (see CDK stack).
# `event` and `context` are passed by AWS — we don't use them but the signature is required.

from src.leaderboard import build_leaderboard
from src.steam_leaderboard import build_steam_leaderboard
from src.discord import send_to_discord, send_steam_to_discord


def handler(event, context):
    # League side: build the leaderboard, post if there's anything to show.
    # If Riot's API is down or returns no matches for anyone, send nothing.
    leaderboard = build_leaderboard()
    if leaderboard:
        send_to_discord(leaderboard)

    # Steam side: always runs because it needs to save today's snapshot regardless
    # of whether it has yesterday's. send_steam_to_discord handles the empty case
    # itself (no message sent on first run / no usable data).
    daily, weekly, today, yesterday = build_steam_leaderboard()
    send_steam_to_discord(daily, weekly, today, yesterday)

    return {"statusCode": 200, "body": "Done"}
