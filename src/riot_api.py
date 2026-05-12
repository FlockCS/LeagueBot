import time
import boto3
import requests
from src.config import REGION, ACCOUNT_BASE_URL

_ssm = boto3.client("ssm", region_name="us-east-1")
_api_key = _ssm.get_parameter(Name="/leaguebot/riot-api-key", WithDecryption=True)["Parameter"]["Value"]
HEADERS = {"X-Riot-Token": _api_key}


def get_puuid(game_name, tag_line):
    url = f"{ACCOUNT_BASE_URL}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    res = requests.get(url, headers=HEADERS)
    if res.status_code != 200:
        print(f"Failed PUUID for {game_name}#{tag_line}: {res.status_code}")
        return None
    return res.json().get("puuid")


def get_match_ids(puuid, start_ts, end_ts):
    url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
    params = {
        "startTime": start_ts,
        "endTime": end_ts,
        "count": 100,
    }
    res = requests.get(url, headers=HEADERS, params=params)
    res.raise_for_status()
    return res.json()


def get_match_duration(match_id):
    url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    return res.json()["info"]["gameDuration"]


def calculate_hours(puuid, start_ts, end_ts):
    try:
        match_ids = get_match_ids(puuid, start_ts, end_ts)
    except Exception as e:
        print(f"Error fetching matches: {e}")
        return 0

    total_seconds = 0
    for match_id in match_ids:
        try:
            total_seconds += get_match_duration(match_id)
            time.sleep(0.1)
        except Exception as e:
            print(f"Error match {match_id}: {e}")

    return total_seconds / 3600
