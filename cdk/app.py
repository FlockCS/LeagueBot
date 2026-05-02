import aws_cdk as cdk
from stacks.leaguebot_stack import LeaguebotStack

app = cdk.App()
LeaguebotStack(app, "LeaguebotStack")
app.synth()
