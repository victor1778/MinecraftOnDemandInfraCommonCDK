from aws_cdk import Duration
from aws_cdk import aws_route53 as route53
from constructs import Construct

from constants import DOMAIN_NAME


class Domain(Construct):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create hosted zone from lookup
        self.hosted_zone = route53.HostedZone.from_lookup(
            self,
            "HostedZone",
            domain_name=DOMAIN_NAME,
        )

        route53.ARecord(
            self,
            "ARecord",
            zone=self.hosted_zone,
            record_name=DOMAIN_NAME,
            target=route53.RecordTarget.from_ip_addresses("192.168.1.1"),
            ttl=Duration.seconds(30),
        )
