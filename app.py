#!/usr/bin/env python3
import os

import aws_cdk as cdk
from dotenv import load_dotenv

from src.component import MinecraftOnDemandInfraCommonCdkStack

load_dotenv()

account = os.getenv("ACCOUNT_ID")
region = os.getenv("REGION") or "us-east-1"

app = cdk.App()

MinecraftOnDemandInfraCommonCdkStack(
    app,
    "MinecraftOnDemandInfraCommonCdkStack",
    env=cdk.Environment(account=account, region=region),
)

app.synth()
