from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

_ = load_dotenv()

class Settings(BaseSettings):
    google_api_key: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="allow")

config = Settings()