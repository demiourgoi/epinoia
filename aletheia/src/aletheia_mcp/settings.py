"""Application configuration, read from `ALETHEIA_*` environment variables."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Aletheia configuration.

    - `ALETHEIA_HOST`: bind host for the review web server. Default
      `127.0.0.1`; the review GUI is a loopback service, only reachable from
      the machine running the agent.
    - `ALETHEIA_PORT`: port for the review web server (default `8417`). Must
      be free while a review session is open; a busy port fails the
      `open_review` tool call with a message naming this variable.
    - `ALETHEIA_MAX_SESSIONS`: number of review sessions kept in memory
      (default `100`); the oldest session is dropped first.
    """

    model_config = SettingsConfigDict(env_prefix="ALETHEIA_")

    host: str = "127.0.0.1"
    port: int = Field(default=8417, gt=0)
    max_sessions: int = Field(default=100, gt=0)


settings = Settings()


def get_settings() -> Settings:
    """Return the process-wide settings singleton (env read once at import)."""
    return settings
