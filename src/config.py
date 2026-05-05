import os

API_KEY = os.environ.get("RIOT_API_KEY", "")
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

REGION = "americas"
ACCOUNT_BASE_URL = "https://americas.api.riotgames.com"

HEADERS = {
    "X-Riot-Token": API_KEY
}

PLAYERS = [
    ("Manny", "MANG"),
    ("1000Gigawatts", "NA1"),
    ("Veesh", "5030"),
    ("Brill", "RUTG"),
    ("IGotBannedAsSett", "NA1"),
    ("Keyboard Warrior", "Don"),
    ("neeltatertots", "NA1"),
    ("sqi", "NA1"),
    ("tinman1337133722", "YEEEE"),
    ("Warden1789023410", "SANJI"),
    ("Yung Bruh 9", "NA1"),
]
