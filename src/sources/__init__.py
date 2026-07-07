# Playtime sources. Each source module exposes:
#
#   daily_playtime(today)  -> list[PlayerPlaytime]
#   weekly_playtime(today) -> list[PlayerPlaytime]
#
# returning normalized per-person, per-game playtime for the given window. The
# unified aggregator (src/unified_leaderboard.py) merges these across sources by
# person_id to build one universal leaderboard.
