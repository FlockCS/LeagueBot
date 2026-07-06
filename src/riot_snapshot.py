# The only place that talks to DynamoDB for League playtime. Unlike Steam (which
# stores lifetime snapshots and diffs them), Riot's match API already gives us the
# exact hours played in a window — so here we persist the *computed daily hours*
# directly, one item per (player_id, day). The weekly recap sums the last 7 items
# instead of re-querying a week of matches from Riot (which would blow the Lambda
# timeout under the dev-key rate limit). Table schema:
#
#   PK: player_id (String)  — canonical, source-neutral identity
#   SK: date      (String, "YYYY-MM-DD")
#   Attrs:
#     name:  display name as of that day
#     hours: League hours played that day (Number)

import os
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key

_dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
_table = _dynamodb.Table(os.environ["RIOT_TABLE_NAME"])


def _date_str(d):
    return d.strftime("%Y-%m-%d")


def save_daily(date, player_id, name, hours):
    # PutItem overwrites, so re-running the Lambda in one day just replaces the
    # record — exactly what we want. DynamoDB rejects floats, so store a Decimal.
    _table.put_item(Item={
        "player_id": player_id,
        "date": _date_str(date),
        "name": name,
        "hours": Decimal(str(hours)),
    })


def load_week(week_start, player_id):
    # Return every daily record from week_start (inclusive) forward for this player.
    # Callers sum the `hours` to get the weekly total. Numbers come back as Decimal.
    res = _table.query(
        KeyConditionExpression=Key("player_id").eq(player_id) & Key("date").gte(_date_str(week_start)),
    )
    return res.get("Items", [])


def delete_daily_before(cutoff_date, player_id):
    # Monday cleanup — drop last week's records once the recap is sent, mirroring
    # the Steam snapshot cleanup so the table stays small.
    res = _table.query(
        KeyConditionExpression=Key("player_id").eq(player_id) & Key("date").lt(_date_str(cutoff_date)),
    )
    with _table.batch_writer() as batch:
        for item in res.get("Items", []):
            batch.delete_item(Key={"player_id": item["player_id"], "date": item["date"]})
