#!/usr/bin/env python3
import os

import aws_cdk as cdk
from dotenv import load_dotenv

from src.component import MinecraftOnDemandInfraCommonCdkStack

load_dotenv()

app = cdk.App()

MinecraftOnDemandInfraCommonCdkStack(
    app,
    "MinecraftOnDemandInfraCommonCdkStack",
    env=cdk.Environment(account=os.getenv("ACCOUNT"), region=os.getenv("REGION")),
)

app.synth()
