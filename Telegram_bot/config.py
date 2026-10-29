import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# 1. Dynamically find the root directory (one level up from this file)
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(ROOT_DIR, '.env')

class BotSettings(BaseSettings):

    BACKEND_URL: str
    GEMINI_API_KEY: str
    TELEGRAM_BOT_TOKEN: str
    INTERNAL_BOT_SECRET: str

    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        extra="ignore"  # This tells Pydantic to ignore DB_HOST, SMTP_SERVER, etc.
    )

settings = BotSettings() # type: ignore
