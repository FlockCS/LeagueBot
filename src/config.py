# Riot API regional routing — "americas" covers NA, LAN, LAS, BR accounts.
REGION = "americas"
ACCOUNT_BASE_URL = "https://americas.api.riotgames.com"

# Steam endpoints. GetPlayerSummaries returns persona name + currently-playing game.
# GetOwnedGames returns every game a player owns and their lifetime playtime in minutes.
STEAM_API_URL = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
STEAM_OWNED_GAMES_URL = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"

# Unified player roster — one row per person. `player_id` is the canonical, source-
# neutral identity and the primary key everywhere (leaderboard merge + the Riot
# playtime table). A person's source handles are just fields on their row:
#   steam_ids — list of SteamID64s; present if they're tracked on Steam (omit otherwise).
#               Most players have one account; list more to merge all into one row.
#               WARNING: the first entry is the DynamoDB snapshot key for this player.
#               Never reorder or remove it — doing so orphans all existing snapshot history.
#   riot      — {game_name, tag_line}; present if they're tracked on League (omit otherwise)
# Both the Steam and Riot sources iterate this one list and emit playtime keyed by
# player_id, so a person's Steam and League hours merge into ONE leaderboard row.
# `name` is the display name shown on the board.
PLAYERS = [
    {"player_id": "manish",  "name": "Manish",  "steam_ids": ["76561198365781139"], "riot": {"game_name": "Manny",            "tag_line": "MANG"}},
    {"player_id": "kabir",   "name": "Kabir",                                        "riot": {"game_name": "1000Gigawatts",    "tag_line": "NA1"}},
    {"player_id": "vishal",  "name": "Vishal",  "steam_ids": ["76561199087416095"], "riot": {"game_name": "Veesh",            "tag_line": "5030"}},
    {"player_id": "bryle",   "name": "Bryle",                                        "riot": {"game_name": "Brill",            "tag_line": "RUTG"}},
    {"player_id": "daksh",   "name": "Daksh",   "steam_ids": ["76561198158759064", "76561199000814578"], "riot": {"game_name": "IGotBannedAsSett", "tag_line": "NA1"}},
    {"player_id": "amer",    "name": "Amer",    "steam_ids": ["76561198264091639"], "riot": {"game_name": "Keyboard Warrior", "tag_line": "Don"}},
    {"player_id": "neel",    "name": "Neel",                                        "riot": {"game_name": "neeltatertots",    "tag_line": "NA1"}},
    {"player_id": "sai",     "name": "Sai",                                         "riot": {"game_name": "sqi",              "tag_line": "NA1"}},
    {"player_id": "pranav",  "name": "Pranav",  "steam_ids": ["76561198289885826"], "riot": {"game_name": "tinman1337133722", "tag_line": "YEEEE"}},
    {"player_id": "maanas",  "name": "Maanas",  "steam_ids": ["76561198162142859"], "riot": {"game_name": "Warden1789023410", "tag_line": "SANJI"}},
    {"player_id": "numair",  "name": "Numair",                                      "riot": {"game_name": "Yung Bruh 9",      "tag_line": "NA1"}},
    {"player_id": "chris",   "name": "Chris",   "steam_ids": ["76561198086647449"]},
    {"player_id": "prabhav", "name": "Prabhav", "steam_ids": ["76561198366009892"]},
    {"player_id": "will",    "name": "Will",    "steam_ids": ["76561198845038364"]},
    {"player_id": "mihir",   "name": "Mihir",   "steam_ids": ["76561198964040125"]},
]
