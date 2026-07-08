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
    # `now` is the moment of this run in Eastern time — the "posting time." The daily
    # window is the trailing 24h ending here (i.e. previous post → this post), so
    # every source reports the same span. Passed through so the message labels it too.
    now = datetime.now(ZoneInfo("America/New_York"))

    # One collection pass across all sources yields both merged leaderboards plus the
    # true start of each window (measured from the reference snapshot, not assumed).
    daily, weekly, daily_start, weekly_start = build(now)

    # Daily leaderboard posts every day (skip if nobody played).
    if daily:
        send_leaderboard(daily, "daily", daily_start, now)

    # Weekly recap is added on Sundays (weekday() == 6).
    if now.weekday() == 6 and weekly:
        send_leaderboard(weekly, "weekly", weekly_start, now)

    return {"statusCode": 200, "body": "Done"}
