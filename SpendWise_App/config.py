# code for pydantic models for environment variables 
# can create a .env file in the root directory for development purposes 
# (initial setup of default values)

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"

class Settings(BaseSettings):
    # database settings
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    DB_USERNAME: str
    DB_PASSWORD: str

    # auth settings
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    DB_ECHO: bool = False
    
    # Email settings
    SMTP_SERVER: str
    SMTP_PORT: int
    SENDER_EMAIL: str
    SENDER_PASSWORD: str
    SENDER_NAME: str = "SpendWise"

    BACKEND_URL: str
    GEMINI_API_KEY: str
    TELEGRAM_BOT_TOKEN: str
    INTERNAL_BOT_SECRET: str

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),
        extra="ignore"  # This allows the backend to ignore the bot's keys
    )

settings = Settings() # type: ignore
