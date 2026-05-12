# LeagueBot

A serverless Discord bot that tracks daily League of Legends playtime for a group of players and posts a daily leaderboard to a Discord channel.

## How it works

An AWS Lambda runs daily at 9 AM EST (via EventBridge). It queries the Riot API for each player's matches from the previous day, totals up game time, and posts the top 3 grinders to Discord via webhook.

## Project structure

```
src/
  config.py        - Region, base URL, and player list
  riot_api.py      - Riot API calls (PUUID lookup, match history, duration)
  leaderboard.py   - Builds the sorted leaderboard for the previous day
  discord.py       - Posts the leaderboard to Discord via webhook
  handler.py       - Lambda entry point
cdk/
  stacks/          - CDK infrastructure (Lambda, EventBridge schedule, IAM)
tests/             - Unit tests
```

## Secrets

API keys are fetched at runtime from AWS SSM Parameter Store:

- `/leaguebot/riot-api-key` - Riot Games API key
- `/leaguebot/discord-webhook-url` - Discord webhook URL

## Development

```bash
pip install -r requirements.txt
pip install -r requirements-test.txt
python -m pytest tests/ -v
```

Or run `bash build.sh` to install deps and run tests in one step.

## Deployment

Merging a PR to `main` triggers a GitHub Actions workflow that runs `cdk deploy` to update the Lambda and infrastructure on AWS.
