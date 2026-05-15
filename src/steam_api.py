import boto3
import requests
from src.config import STEAM_API_URL, STEAM_OWNED_GAMES_URL

# Pull the Steam API key from AWS Parameter Store at import time so we don't have
# to hit SSM on every request. WithDecryption=True is required for SecureString params.
_ssm = boto3.client("ssm", region_name="us-east-1")
_api_key = _ssm.get_parameter(Name="/leaguebot/steam-api-key", WithDecryption=True)["Parameter"]["Value"]


def get_player_status(steam_id):
    # Returns {name, game} dict, where `game` is what they're currently playing
    # (or None if offline / not in a game). We only use `name` in the leaderboard,
    # but `game` could be used later for "who is playing what right now" features.
    res = requests.get(STEAM_API_URL, params={
        "key": _api_key,
        "steamids": steam_id,
    })
    if res.status_code != 200:
        print(f"Failed to fetch status for {steam_id}: {res.status_code}")
        return None

    players = res.json().get("response", {}).get("players", [])
    if not players:
        return None

    player = players[0]
    return {
        "name": player["personaname"],
        "game": player.get("gameextrainfo"),
    }


def get_owned_games(steam_id):
    # Returns {game_name: lifetime_minutes} for every game the player has actually
    # played. Steam's API only gives lifetime totals — we compute "played today" by
    # diffing today's totals against yesterday's snapshot (see steam_leaderboard.py).
    res = requests.get(STEAM_OWNED_GAMES_URL, params={
        "key": _api_key,
        "steamid": steam_id,
        "include_appinfo": 1,             # Required to get the game's name (not just appid).
        "include_played_free_games": 1,   # Counts free-to-play games like CS2, Dota 2.
        "format": "json",
    })
    if res.status_code != 200:
        print(f"Failed to fetch owned games for {steam_id}: {res.status_code}")
        return None

    # If the profile is private, the API returns {} instead of {games: [...]} —
    # this is the one case we can't recover from without the user changing their privacy settings.
    games = res.json().get("response", {}).get("games")
    if games is None:
        print(f"No games visible for {steam_id} (profile may be private)")
        return None

    # Filter out games with 0 playtime to keep DynamoDB items small.
    result = {}
    for g in games:
        minutes = g.get("playtime_forever", 0)
        if minutes <= 0:
            continue
        # Fall back to a synthetic name if Steam doesn't return one — `or`
        # short-circuits so we only build the appid string when name is missing.
        name = g.get("name") or f"appid_{g.get('appid', 'unknown')}"
        result[name] = minutes
    return result
