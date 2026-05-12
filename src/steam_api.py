import boto3
import requests
from src.config import STEAM_API_URL

_ssm = boto3.client("ssm", region_name="us-east-1")
_api_key = _ssm.get_parameter(Name="/leaguebot/steam-api-key", WithDecryption=True)["Parameter"]["Value"]


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
