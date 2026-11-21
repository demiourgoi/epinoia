"""Application configuration, read from `ALETHEIA_*` environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Aletheia configuration.

    - `ALETHEIA_HOST`: bind host for the review web server. Default
      `127.0.0.1`; the review GUI is a loopback service, only reachable
      from the machine running the agent. The port is autodetected (a free
      OS-assigned port) so no port setting exists.
    """

    model_config = SettingsConfigDict(env_prefix="ALETHEIA_")

    host: str = "127.0.0.1"


settings = Settings()


def get_settings() -> Settings:
    """Return the process-wide settings singleton (env read once at import)."""
    return settings
