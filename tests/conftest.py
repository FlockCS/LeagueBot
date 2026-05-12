from unittest.mock import MagicMock, patch

_ssm_values = {
    "/leaguebot/riot-api-key": "test-riot-key",
    "/leaguebot/discord-webhook-url": "https://test-webhook-url",
}


def _mock_get_parameter(Name, WithDecryption=False):
    return {"Parameter": {"Value": _ssm_values[Name]}}


mock_ssm = MagicMock()
mock_ssm.get_parameter = MagicMock(side_effect=_mock_get_parameter)

patcher = patch("boto3.client", return_value=mock_ssm)
patcher.start()
