from aws_cdk import Duration
from aws_cdk import aws_certificatemanager as acm
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_route53 as route53
from constructs import Construct

from constants import DOMAIN_NAME


class Network(Construct):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.hosted_zone = route53.HostedZone.from_lookup(
            self,
            "HostedZone",
            domain_name=DOMAIN_NAME,
        )

        self.certificate = acm.Certificate(
            self,
            "ApiCertificate",
            domain_name="api.pz-craft.online",
            validation=acm.CertificateValidation.from_dns(self.hosted_zone),
        )

        route53.ARecord(
            self,
            "ARecord",
            zone=self.hosted_zone,
            record_name=DOMAIN_NAME,
            target=route53.RecordTarget.from_ip_addresses("192.168.1.1"),
            ttl=Duration.seconds(30),
        )

        route53.ARecord(self, "ApiAliasRecord",
            zone=self.hosted_zone,
            target=route53.RecordTarget.from_alias(targets.ApiGatewayDomain(custom_domain))
        )

        self.vpc = ec2.Vpc(
            self,
            "VPC",
            max_azs=3,
            nat_gateways=0,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Private-Egress",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                ),
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                ),
            ],
        )

        self.subnet_selection = self.vpc.select_subnets(
            subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
        )

        self.vpc.add_gateway_endpoint(
            "s3-gw-endpoint",
            service=ec2.GatewayVpcEndpointAwsService.S3,
        )

        self.security_group = ec2.SecurityGroup(
            self,
            "ServiceSecurityGroup",
            vpc=self.vpc,
            allow_all_outbound=True,
            description="Security group for Minecraft server",
        )

        self.security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(25565),
        )

        self.security_group.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(2049),
            description="Allow NFS traffic",
        )
