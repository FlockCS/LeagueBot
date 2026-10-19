# One-time migration for PR #15 (key Steam snapshots by appid instead of name):
# rewrites every existing snapshot item's `games` dict from {name: minutes} to
# {appid: minutes} in place, so old snapshots stay diffable against the new
# appid-keyed code instead of every game looking "new" on the first post-deploy run.
#
# Run this AFTER deploying the appid-keyed src/steam_api.py (it imports
# get_owned_games and needs the new tuple return shape), and before the next
# scheduled Lambda invocation.
#
# KNOWN LIMITATION: a game renamed on Steam before this script runs (e.g. "The
# Witcher 3: Wild Hunt" -> "...Complete Edition") no longer appears under its old
# name in the current owned-games response, so the old name can't be resolved
# automatically — it would silently drop from the migrated snapshot and cause
# that one game's lifetime hours to spike again on the next diff (the exact bug
# this migration exists to avoid). Add any such known renames to RENAME_OVERRIDES
# below before running with --apply. Dry-run output lists every name it couldn't
# resolve so you can catch these before writing anything.
#
# Usage:
#   python -m scripts.migrate_steam_snapshots_to_appid            # dry run, writes nothing
#   python -m scripts.migrate_steam_snapshots_to_appid --apply    # writes the rewritten items

import argparse
import logging
import os
import time
import boto3
from boto3.dynamodb.conditions import Key
from src.config import PLAYERS
from src.steam_api import get_owned_games

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

_dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
_table = _dynamodb.Table(os.environ["STEAM_TABLE_NAME"])

# Old name -> appid, for renames that happened before this script's name->appid
# map (built from CURRENT owned games) could ever observe the old name.
RENAME_OVERRIDES = {
    "The Witcher 3: Wild Hunt": 292030,
}


def _steam_players():
    return [p for p in PLAYERS if p.get("steam_ids")]


def _build_name_to_appid(steam_ids):
    # Union current name->appid across every account linked to this player — a
    # merged snapshot can contain games owned on any one of their accounts.
    mapping = dict(RENAME_OVERRIDES)
    for steam_id in steam_ids:
        result = get_owned_games(steam_id)
        if result is None:
            logger.warning(f"  could not fetch owned games for {steam_id} — its games may be left unmapped")
            continue
        _, names = result
        for appid, name in names.items():
            mapping[name] = int(appid)
        time.sleep(1)
    return mapping


def _is_already_migrated(games):
    # Appid keys are all-digit strings; name keys never are. An empty dict
    # counts as migrated (nothing to rewrite).
    return all(str(k).isdigit() for k in games)


def _migrate_item(item, name_to_appid):
    games = item.get("games", {})
    if _is_already_migrated(games):
        return None

    new_games = {}
    unmapped = []
    for name, minutes in games.items():
        appid = name_to_appid.get(name)
        if appid is None:
            unmapped.append(name)
            continue
        key = str(appid)
        new_games[key] = new_games.get(key, 0) + int(minutes)

    if unmapped:
        logger.warning(
            f"  {item['steam_id']}/{item['date']}: could not resolve {unmapped} to an appid "
            "— dropped from this snapshot (add to RENAME_OVERRIDES to preserve, then re-run)"
        )

    return {**item, "games": new_games, "total_minutes": sum(new_games.values())}


def main(apply):
    total_items = 0
    total_migrated = 0

    for player in _steam_players():
        primary_id = player["steam_ids"][0]
        logger.info(f"{player['name']} ({primary_id})")

        name_to_appid = _build_name_to_appid(player["steam_ids"])

        items = _table.query(KeyConditionExpression=Key("steam_id").eq(primary_id)).get("Items", [])
        total_items += len(items)

        for item in items:
            migrated = _migrate_item(item, name_to_appid)
            if migrated is None:
                continue
            total_migrated += 1
            logger.info(f"  {item['date']}: {list(item.get('games', {}).keys())} -> {list(migrated['games'].keys())}")
            if apply:
                _table.put_item(Item=migrated)

    mode = "APPLIED" if apply else "DRY RUN — pass --apply to write"
    logger.info(f"\n{mode}: {total_migrated}/{total_items} snapshot items needed migration")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write changes (default is dry-run)")
    args = parser.parse_args()
    main(args.apply)
