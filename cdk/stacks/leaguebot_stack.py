from pathlib import Path
from aws_cdk import (
    Stack,
    Duration,
    BundlingOptions,
    aws_lambda as _lambda,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_dynamodb as dynamodb,
)
from constructs import Construct

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)


class LeaguebotStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # DynamoDB table for Steam playtime snapshots — one item per (player, day).
        # PAY_PER_REQUEST means we only pay for actual reads/writes (no provisioned
        # throughput to manage). With ~10 players * 2 reads + 1 write per day,
        # we use ~30 RCUs and ~10 WCUs daily — well inside the 25 GB / 25 R+WCU free tier.
        steam_table = dynamodb.Table(
            self, "SteamSnapshotsTable",
            table_name="leaguebot-steam-snapshots",
            partition_key=dynamodb.Attribute(
                name="steam_id",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="date",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        )

        # DynamoDB table for computed daily League playtime — one item per
        # (player, day). The weekly recap sums the week's items instead of
        # re-querying Riot, keeping us inside the Lambda timeout and the API rate
        # limit. Same tiny footprint as the Steam table (well inside free tier).
        riot_table = dynamodb.Table(
            self, "RiotPlaytimeTable",
            table_name="leaguebot-riot-playtime",
            partition_key=dynamodb.Attribute(
                name="discord_id",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="date",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        )

        fn = _lambda.Function(
            self, "LeaguebotFunction",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="src.handler.handler",
            code=_lambda.Code.from_asset(
                PROJECT_ROOT,
                bundling=BundlingOptions(
                    image=_lambda.Runtime.PYTHON_3_12.bundling_image,
                    command=[
                        "bash", "-c",
                        "pip install -r requirements.txt -t /asset-output"
                        " && cp -au src /asset-output/",
                    ],
                ),
            ),
            timeout=Duration.minutes(5),
            memory_size=256,
            environment={
                "STEAM_TABLE_NAME": steam_table.table_name,
                "RIOT_TABLE_NAME": riot_table.table_name,
            },
        )

        fn.add_to_role_policy(iam.PolicyStatement(
            actions=["ssm:GetParameter"],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/leaguebot/*",
            ],
        ))

        steam_table.grant_read_write_data(fn)
        riot_table.grant_read_write_data(fn)

        rule = events.Rule(
            self, "DailySchedule",
            schedule=events.Schedule.cron(hour="14", minute="0"), # 2PM UTC is 9 AM EST
        )
        rule.add_target(targets.LambdaFunction(fn))
