import os

WORLD: str = os.getenv("WORLD")
MODPACK: str = os.getenv("MODPACK")

CLUSTER_NAME: str = "minecraft"
SERVICE_NAME: str = "minecraft-server"
MC_SERVER_CONTAINER_NAME: str = "minecraft-server"
DOMAIN_NAME: str = "pz-craft.online"
DOMAIN_STACK_REGION: str = "us-east-1"
ECS_VOLUME_NAME: str = "data"
JAVA_EDITION_DOCKER_IMAGE: str = "itzg/minecraft-server"
BEDROCK_EDITION_DOCKER_IMAGE: str = "itzg/minecraft-bedrock-server"
