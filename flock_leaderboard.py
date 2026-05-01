import requests
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo  # built-in in Python 3.9+

# =========================
# CONFIG
# =========================
API_KEY = "RGAPI-aa7c1528-43bf-422b-9061-3c85fc9b0ca2"
WEBHOOK_URL = "https://discord.com/api/webhooks/1498832759769272430/Z2l0nBfUAExysmWxBwrhnA2FWOBZFGDXp7wzU-MKszcvTn9A3T_SjaUIBZ5LZXf_wVIM"

# Riot routing (NA = americas)
REGION = "americas"
ACCOUNT_BASE_URL = "https://americas.api.riotgames.com"

HEADERS = {
    "X-Riot-Token": API_KEY
}

# Riot IDs (GameName, TagLine)
PLAYERS = [
    ("Manny", "MANG"),              # Me
    ("1000Gigawatts", "NA1"),       # Kabir
    ("Veesh", "5030"),              # Vishal
    ("Brill", "RUTG"),              # Bryle
    ("IGotBannedAsSett", "NA1"),    # Daksh
    ("Keyboard Warrior", "Don"),    # Amer
    ("neeltatertots", "NA1"),       # Neel
    ("sqi", "NA1"),                 # Sai
    ("tinman1337133722", "YEEEE"),  # Pranav
    ("Warden1789023410", "SANJI"),  # Maanas
    ("Yung Bruh 9", "NA1")          # Numair
]

# =========================
# TIME (EST/EDT SAFE)
# =========================
def get_yesterday_timestamps_est():
    tz = ZoneInfo("America/New_York")

    now = datetime.now(tz)
    today_start = datetime(now.year, now.month, now.day, tzinfo=tz)
    yesterday_start = today_start - timedelta(days=1)

    return int(yesterday_start.timestamp()), int(today_start.timestamp()), yesterday_start, today_start


# =========================
# GET PUUID
# =========================
def get_puuid(game_name, tag_line):
    url = f"{ACCOUNT_BASE_URL}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"

    res = requests.get(url, headers=HEADERS)

    if res.status_code != 200:
        print(f"❌ Failed PUUID for {game_name}#{tag_line}: {res.status_code}")
        return None

    return res.json().get("puuid")


# =========================
# GET MATCH IDS
# =========================
def get_match_ids(puuid, start_ts, end_ts):
    url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"

    params = {
        "startTime": start_ts,
        "endTime": end_ts,
        "count": 100
    }

    res = requests.get(url, headers=HEADERS, params=params)
    res.raise_for_status()
    return res.json()


# =========================
# GET MATCH DURATION
# =========================
def get_match_duration(match_id):
    url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"

    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()

    return res.json()["info"]["gameDuration"]


# =========================
# CALCULATE HOURS
# =========================
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
            time.sleep(0.1)  # light rate limiting
        except Exception as e:
            print(f"Error match {match_id}: {e}")

    return total_seconds / 3600


# =========================
# BUILD LEADERBOARD
# =========================
def build_leaderboard():
    start_ts, end_ts, window_start, window_end = get_yesterday_timestamps_est()
    fmt = "%b %d %I:%M %p %Z"
    print(f"\n⏱  Time window: {window_start.strftime(fmt)} → {window_end.strftime(fmt)}\n")
    results = []

    for game_name, tag_line in PLAYERS:
        print(f"\n🔍 Processing {game_name}#{tag_line}...")

        puuid = get_puuid(game_name, tag_line)
        if not puuid:
            continue

        time.sleep(1.2)  # avoid rate limits

        hours = calculate_hours(puuid, start_ts, end_ts)
        results.append((game_name, hours))

    results.sort(key=lambda x: x[1], reverse=True)
    return results

# =========================
# SEND TO DISCORD
# =========================
def send_to_discord(results):
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("America/New_York")
    now = datetime.now(tz)
    today_start = datetime(now.year, now.month, now.day, tzinfo=tz)
    yesterday_start = today_start - timedelta(days=1)
    fmt = "%b %d %I:%M %p %Z"
    window_str = f"{yesterday_start.strftime(fmt)} → {today_start.strftime(fmt)}"

    message = f"**🏆 Top 3 League Grind:**\n_{window_str}_\n\n"

    medals = ["🥇", "🥈", "🥉"]

    for i, (name, hours) in enumerate(results[:3]):
        message += f"{medals[i]} {name} — {hours:.1f} hrs\n"

    payload = {
        "content": message
    }

    import requests
    res = requests.post(WEBHOOK_URL, json=payload)
    res.raise_for_status()

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    leaderboard = build_leaderboard()

    if not leaderboard:
        print("No data found.")
    else:
        send_to_discord(leaderboard)
        print("\n✅ Leaderboard sent!")
