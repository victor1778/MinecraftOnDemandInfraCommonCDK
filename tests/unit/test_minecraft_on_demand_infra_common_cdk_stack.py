import aws_cdk as core
import aws_cdk.assertions as assertions

from src.component import MinecraftOnDemandInfraCommonCdkStack

# example tests. To run these tests, uncomment this file along with the example
# resource in minecraft_on_demand_infra_common_cdk/minecraft_on_demand_infra_common_cdk_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = MinecraftOnDemandInfraCommonCdkStack(app, "minecraft-on-demand-infra-common-cdk")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
