# The normalized unit every source produces and the aggregator consumes.
# One PlayerPlaytime = one person's playtime within a single window (day or week),
# broken down per game. `person_id` is the canonical, source-neutral identity
# (config.PLAYERS[*]["player_id"]) so the same human's Steam and League playtime can
# be merged into a single leaderboard row. `games` maps a game's display name -> hours.

from dataclasses import dataclass, field


@dataclass
class PlayerPlaytime:
    person_id: str
    display_name: str
    games: dict = field(default_factory=dict)

    @property
    def total_hours(self):
        return sum(self.games.values())

    def merge(self, other):
        # Fold another source's playtime for the same person into this one.
        # Games are unioned; if two sources somehow report the same game name,
        # their hours add (harmless — different sources use distinct names in
        # practice, e.g. "League of Legends" vs Steam titles).
        for game, hours in other.games.items():
            self.games[game] = self.games.get(game, 0) + hours
