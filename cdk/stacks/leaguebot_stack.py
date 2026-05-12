from pathlib import Path
from aws_cdk import (
    Stack,
    Duration,
    BundlingOptions,
    aws_lambda as _lambda,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
)
from constructs import Construct

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)


class LeaguebotStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

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
        )

        fn.add_to_role_policy(iam.PolicyStatement(
            actions=["ssm:GetParameter"],
            resources=[
                f"arn:aws:ssm:{self.region}:{self.account}:parameter/leaguebot/*",
            ],
        ))

        rule = events.Rule(
            self, "DailySchedule",
            schedule=events.Schedule.cron(hour="14", minute="0"), # 2PM UTC is 9 AM EST
        )
        rule.add_target(targets.LambdaFunction(fn))
