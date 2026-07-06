# LeagueBot

A serverless Discord bot that tracks daily gaming playtime for a group of friends
across **multiple sources** (Steam and League of Legends via Riot) and posts a single
**unified leaderboard** to a Discord channel.

## How it works

An AWS Lambda runs daily at 9 AM EST (via EventBridge). It collects each person's
playtime from every source, **merges it per person** (so someone's League and Steam
hours combine into one ranked entry), and posts to Discord via webhook:

- **Daily leaderboard** — every day, ranking the top players by total hours across
  all their games, with a per-game breakdown.
- **Weekly recap** — additionally on Sundays, the same thing over the whole week.

Each source derives period totals differently but produces the same normalized shape
(`src/models.py::PlayerPlaytime`):

- **Steam** only exposes lifetime per-game totals, so we store a daily snapshot in
  DynamoDB and diff it (today vs. yesterday for daily, today vs. Monday for weekly).
- **Riot** exposes exact match durations for a time window, so daily is a live query;
  each day's computed hours are persisted so the weekly recap sums the week instead
  of re-querying Riot (which would exceed the dev-key rate limit / Lambda timeout).

Cross-source merging is by `discord_id`: give a League player in `config.PLAYERS` the
same `discord_id` as their `STEAM_PLAYERS` entry and their hours combine into one row.

## Project structure

```
src/
  config.py             - Region, base URLs, and the Steam + League player lists
  models.py             - PlayerPlaytime: the normalized per-person, per-game unit
  riot_api.py           - Riot API calls (PUUID lookup, match history, duration)
  steam_api.py          - Steam API calls (persona name, owned games / playtime)
  riot_snapshot.py      - DynamoDB store for computed daily League hours
  steam_snapshot.py     - DynamoDB store for daily Steam lifetime snapshots
  sources/
    riot.py             - League source: daily/weekly -> list[PlayerPlaytime]
    steam.py            - Steam source: daily/weekly -> list[PlayerPlaytime]
  unified_leaderboard.py- Merges every source per person into one ranked board
  discord.py            - Posts the unified leaderboard to Discord via webhook
  handler.py            - Lambda entry point
cdk/
  stacks/               - CDK infrastructure (Lambda, DynamoDB, EventBridge, IAM)
tests/                  - Unit tests
```

## Secrets

API keys are fetched at runtime from AWS SSM Parameter Store:

- `/leaguebot/riot-api-key` - Riot Games API key
- `/leaguebot/steam-api-key` - Steam Web API key
- `/leaguebot/discord-webhook-url` - Discord webhook URL

## Development

```bash
pip install -r requirements.txt
pip install -r requirements-test.txt
python -m pytest tests/ -v
```

Or run `bash build.sh` to install deps and run tests in one step.

## Deployment

Merging a PR to `main` triggers a GitHub Actions workflow that runs `cdk deploy` to
update the Lambda and infrastructure on AWS.
