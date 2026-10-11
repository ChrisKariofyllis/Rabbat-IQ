"""Process configuration from the environment.

Shopping preferences live in the database and are edited in the web UI.
This module only covers how the process starts: bind address, database path,
optional HTTP basic auth, and optional Marktguru key overrides.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MARKTHUNTER_", extra="ignore")

    host: str = "0.0.0.0"
    port: int = 8000
    database_url: str = "sqlite:///./data/markthunter.db"
    data_dir: str = "./data"
    log_level: str = "INFO"
    disable_scheduler: bool = False
    disable_bot: bool = False
    basic_auth_user: str = ""
    basic_auth_password: str = ""
    marktguru_api_key: str = ""
    marktguru_client_key: str = ""
    postal_code: str = ""
    country: str = ""


_env: EnvSettings | None = None


def set_env(env: EnvSettings) -> None:
    global _env
    _env = env


def get_env() -> EnvSettings:
    return _env or EnvSettings()
