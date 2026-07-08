# This module is the only place that talks to DynamoDB. Every snapshot we ever store
# is one item in this table, keyed by (steam_id, date). The table schema:
#
#   PK: steam_id (String)
#   SK: date     (String, "YYYY-MM-DD")
#   Attrs:
#     name: persona name as of that day (e.g. "Donkey")
#     games: {game_name: lifetime_minutes_at_that_moment}
#     total_minutes: sum of games.values()  (cached so weekly delta is one read)
#     captured_at: ISO-8601 timestamp of the exact moment this snapshot was taken.
#                  The real start of the window a later diff covers (a snapshot's
#                  date is only a day-granularity key; captured_at is the true time).

import os
import boto3
from boto3.dynamodb.conditions import Key

# Table name comes from a Lambda env var set by CDK (see leaguebot_stack.py).
# Reading os.environ at import time means a missing var crashes loudly on startup
# rather than silently failing during the first DynamoDB call.
_dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
_table = _dynamodb.Table(os.environ["STEAM_TABLE_NAME"])


def save_snapshot(date, steam_id, name, games, captured_at):
    # PutItem overwrites by default (no version check), so running the Lambda twice
    # in one day just replaces the snapshot — exactly what we want. captured_at is
    # the ISO-8601 moment of capture, used later to label the real window a diff spans.
    total_minutes = sum(games.values())
    _table.put_item(Item={
        "steam_id": steam_id,
        "date": date,
        "name": name,
        "games": games,
        "total_minutes": total_minutes,
        "captured_at": captured_at,
    })


def load_snapshot(date, steam_id):
    # Returns the full item dict, or None if no snapshot exists for that day.
    # Numbers come back from DynamoDB as Decimal — callers cast with int() before math.
    res = _table.get_item(Key={"steam_id": steam_id, "date": date})
    return res.get("Item")


def delete_snapshots_before(cutoff_date, steam_id):
    # Used for Monday cleanup — drops last week's snapshots once we've sent the
    # weekly recap. Free-tier DynamoDB has generous limits but the leaderboard
    # only needs ~8 days of history, so we delete the rest to stay tidy.
    res = _table.query(
        KeyConditionExpression=Key("steam_id").eq(steam_id) & Key("date").lt(cutoff_date),
    )
    # batch_writer batches up to 25 deletes per request and retries on throttling.
    with _table.batch_writer() as batch:
        for item in res.get("Items", []):
            batch.delete_item(Key={"steam_id": item["steam_id"], "date": item["date"]})
