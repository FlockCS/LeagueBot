import os
from unittest.mock import MagicMock, patch

os.environ["STEAM_TABLE_NAME"] = "test-steam-table"
os.environ["RIOT_TABLE_NAME"] = "test-riot-table"

_ssm_values = {
    "/leaguebot/riot-api-key": "test-riot-key",
    "/leaguebot/discord-webhook-url": "https://test-webhook-url",
    "/leaguebot/steam-api-key": "test-steam-key",
}


def _mock_get_parameter(Name, WithDecryption=False):
    return {"Parameter": {"Value": _ssm_values[Name]}}


mock_ssm = MagicMock()
mock_ssm.get_parameter = MagicMock(side_effect=_mock_get_parameter)

patch("boto3.client", return_value=mock_ssm).start()
patch("boto3.resource", return_value=MagicMock()).start()
