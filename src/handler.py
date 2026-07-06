# Lambda entry point. AWS EventBridge fires this once per day at 9 AM ET (see CDK
# stack). `event` and `context` are passed by AWS — unused, but the signature is
# required.

import logging

# Lambda captures the root logger but defaults to WARNING. Set INFO so all
# logger.info() calls from the sources, aggregator, and discord appear in CloudWatch.
logging.getLogger().setLevel(logging.INFO)

from datetime import datetime
from zoneinfo import ZoneInfo
from src.unified_leaderboard import build
from src.discord import send_leaderboard


def handler(event, context):
    # "Today" in Eastern time so day boundaries line up with the 9 AM ET trigger.
    today = datetime.now(ZoneInfo("America/New_York")).date()

    # One collection pass across all sources yields both the daily and weekly
    # merged leaderboards. Posting each source's fetch happens exactly once.
    daily, weekly = build(today)

    # Daily leaderboard posts every day (skip if nobody played).
    if daily:
        send_leaderboard(daily, "daily", today)

    # Weekly recap is added on Sundays (weekday() == 6).
    if today.weekday() == 6 and weekly:
        send_leaderboard(weekly, "weekly", today)

    return {"statusCode": 200, "body": "Done"}
