from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class BackupConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )

    backup_restore_enabled: bool = Field(default=False, alias="BACKUP_RESTORE_ENABLED")

    disaster_recovery_enabled: bool = Field(default=False, alias="DISASTER_RECOVERY_ENABLED")
    disaster_recovery_backup_dir: str = Field(default="/tmp/agent-backups", alias="DISASTER_RECOVERY_BACKUP_DIR")
    disaster_recovery_schedule_hours: int = Field(default=24, alias="DISASTER_RECOVERY_SCHEDULE_HOURS")
