from src.main import build_leaderboard
from src.discord import send_to_discord


def handler(event, context):
    leaderboard = build_leaderboard()
    if leaderboard:
        send_to_discord(leaderboard)
        return {"statusCode": 200, "body": "Leaderboard sent"}
    return {"statusCode": 200, "body": "No data found"}
