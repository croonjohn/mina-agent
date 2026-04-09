from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

_ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    # App
    app_name: str = "Mina Agent"
    debug: bool = False

    # Database
    database_url: str = "sqlite+aiosqlite:///./mina_agent.db"

    # Redis
    redis_url: str = ""

    # Reddit
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_username: str = ""
    reddit_password: str = ""
    reddit_user_agent: str = "mina-agent:v1.0 (by /u/verse8_official)"

    # Discord
    discord_webhook_url: str = ""

    # Auth
    api_secret_key: str = "dev-secret-change-me"

    model_config = {"env_file": str(_ENV_FILE), "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
