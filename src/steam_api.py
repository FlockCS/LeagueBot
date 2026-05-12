import boto3
import requests

_ssm = boto3.client("ssm", region_name="us-east-1")
_api_key = _ssm.get_parameter(Name="/leaguebot/steam-api-key", WithDecryption=True)["Parameter"]["Value"]

STEAM_API_URL = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"


def get_player_status(steam_id):
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
