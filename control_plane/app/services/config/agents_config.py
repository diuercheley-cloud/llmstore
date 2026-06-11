from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentsConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )

    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    cluster_region: str = Field(default="default", alias="CLUSTER_REGION")
