import os

from src.main import build_leaderboard
from src.discord import send_to_discord


def handler(event, context):
    if not os.environ.get("RIOT_API_KEY") or not os.environ.get("DISCORD_WEBHOOK_URL"):
        raise RuntimeError("Missing required environment variables: RIOT_API_KEY, DISCORD_WEBHOOK_URL")
    leaderboard = build_leaderboard()
    if leaderboard:
        send_to_discord(leaderboard)
        return {"statusCode": 200, "body": "Leaderboard sent"}
    return {"statusCode": 200, "body": "No data found"}
