import os
import requests
from src.config import STEAM_API_URL, STEAM_PLAYERS

# Set this in your terminal before running: $env:STEAM_API_KEY = "your-key-here"
STEAM_API_KEY = os.environ.get("STEAM_API_KEY")

steam_ids = [user["steam_id"] for user in STEAM_PLAYERS]

res = requests.get(STEAM_API_URL, params={
    "key": STEAM_API_KEY,
    "steamids": ",".join(steam_ids),
})

players = res.json()["response"]["players"]
for player in players:
    game = player.get("gameextrainfo", "Idle")
    print(f"{player['personaname']} — {game}")
