"""Application configuration, read from ``AZATHOTH_*`` environment variables."""

import json
import shlex
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Azathoth configuration.

    - ``AZATHOTH_HOST``: bind address; loopback by default. Binding a
      non-loopback address is possible but leaves the localhost-only
      enforcement to the request guard.
    - ``AZATHOTH_PORT``: bind port (default ``8000``).
    - ``AZATHOTH_ACP_COMMAND``: the ACP agent server to spawn (default
      ``vibe-acp``, installed by the Mistral Vibe CLI).
    - ``AZATHOTH_ACP_ARGS``: extra command-line arguments for the agent
      server, space-separated.
    - ``AZATHOTH_TIMEOUT_SECS``: seconds to wait for each agent turn before
      failing the request and reopening the connection (default ``600``).
    """

    model_config = SettingsConfigDict(env_prefix="AZATHOTH_")

    host: str = "127.0.0.1"
    port: int = 8000
    acp_command: str = "vibe-acp"
    acp_args: Annotated[list[str], NoDecode] = []
    timeout_secs: float = 600.0

    @field_validator("acp_args", mode="before")
    @classmethod
    def _parse_args(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        try:
            return json.loads(value)
        except ValueError:
            return shlex.split(value)
