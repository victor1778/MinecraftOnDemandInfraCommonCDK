#!/usr/bin/env python3
import os

import aws_cdk as cdk

from src.component import (
    MinecraftOnDemandInfraCommonCdkStack,
)


app = cdk.App()
MinecraftOnDemandInfraCommonCdkStack(
    app,
    "MinecraftOnDemandInfraCommonCdkStack",
    env=cdk.Environment(account="533267195973", region="us-east-1"),
)

app.synth()
