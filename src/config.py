# Riot API regional routing — "americas" covers NA, LAN, LAS, BR accounts.
REGION = "americas"
ACCOUNT_BASE_URL = "https://americas.api.riotgames.com"

# Steam endpoints. GetPlayerSummaries returns persona name + currently-playing game.
# GetOwnedGames returns every game a player owns and their lifetime playtime in minutes.
STEAM_API_URL = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
STEAM_OWNED_GAMES_URL = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"

STEAM_PLAYERS = [
    {"discord_id": "225032479734628353", "steam_id": "76561198158759064"}, #Donkey
    {"discord_id": "297099102989189121", "steam_id": "76561198289885826"}, #Pranav
    {"discord_id": "208305260492619776", "steam_id": "76561198086647449"}, #Chris
    {"discord_id": "333959051392188417", "steam_id": "76561198365781139"}, #Manish
    {"discord_id": "439939611741913098", "steam_id": "76561198964040125"}, #Mihir
    {"discord_id": "168190192698654720", "steam_id": "76561198162142859"}, #Maanas
    {"discord_id": "428622485949513729", "steam_id": "76561199087416095"}, #Veesh
    {"discord_id": "272494999680188417", "steam_id": "76561198264091639"}, #Don
    {"discord_id": "449229001085681668", "steam_id": "76561198366009892"}, #Prabhav
    {"discord_id": "278664292818092052", "steam_id": "76561198845038364"}, #Will
]

# League (Riot) players. `discord_id` is the canonical cross-source identity: when a
# League player's discord_id matches a STEAM_PLAYERS discord_id above, their League
# and Steam hours merge into ONE row on the unified leaderboard.
#
# Entries still marked "league_*" are placeholders for players with no known Steam
# account yet — they appear as their own row (League hours only) until you replace
# the placeholder with the real Discord id from STEAM_PLAYERS. The numeric ids below
# are already linked to their Steam counterpart (see the trailing comment on each).
PLAYERS = [
    {"discord_id": "333959051392188417", "game_name": "Manny",            "tag_line": "MANG"},   # = Steam Manish
    {"discord_id": "league_gigawatts",   "game_name": "1000Gigawatts",    "tag_line": "NA1"},
    {"discord_id": "428622485949513729", "game_name": "Veesh",            "tag_line": "5030"},   # = Steam Veesh
    {"discord_id": "league_brill",       "game_name": "Brill",            "tag_line": "RUTG"},
    {"discord_id": "225032479734628353", "game_name": "IGotBannedAsSett", "tag_line": "NA1"},    # = Steam Donkey
    {"discord_id": "272494999680188417", "game_name": "Keyboard Warrior", "tag_line": "Don"},    # = Steam Don
    {"discord_id": "league_neel",        "game_name": "neeltatertots",    "tag_line": "NA1"},
    {"discord_id": "league_sqi",         "game_name": "sqi",              "tag_line": "NA1"},
    {"discord_id": "297099102989189121", "game_name": "tinman1337133722", "tag_line": "YEEEE"},  # = Steam Pranav
    {"discord_id": "168190192698654720", "game_name": "Warden1789023410", "tag_line": "SANJI"},  # = Steam Maanas
    {"discord_id": "league_yungbruh",    "game_name": "Yung Bruh 9",      "tag_line": "NA1"},
]
