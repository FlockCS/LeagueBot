import os
import requests

STEAM_API_KEY = os.environ.get("STEAM_API_KEY")
STEAM_API_URL = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"

steam_ids = [user["steam_id"] for user in [
    {"steam_id": "76561198158759064"},  # Donkey
    {"steam_id": "76561198289885826"},  # Pranav
    {"steam_id": "76561198086647449"},  # Chris
    {"steam_id": "76561198365781139"},  # Manish
    {"steam_id": "76561198964040125"},  # Mihir
    {"steam_id": "76561198162142859"},  # Maanas
    {"steam_id": "76561199087416095"},  # Veesh
    {"steam_id": "76561198264091639"},  # Don
    {"steam_id": "76561198366009892"},  # Prabhav
    {"steam_id": "76561198845038364"},  # Will
]]

res = requests.get(STEAM_API_URL, params={
    "key": STEAM_API_KEY,
    "steamids": ",".join(steam_ids),
})

players = res.json()["response"]["players"]
for player in players:
    game = player.get("gameextrainfo", "Idle")
    print(f"{player['personaname']} — {game}")
