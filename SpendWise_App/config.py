# code for pydantic models for environment variables 
# can create a .env file in the root directory for development purposes 
# (initial setup of default values)

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # database settings
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    DB_USERNAME: str
    DB_PASSWORD: str

    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

