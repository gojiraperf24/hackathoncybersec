from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://civic:civic@localhost:5432/civic"
    x_bearer_token: str = ""
    youtube_api_key: str = ""

    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minio"
    s3_secret_key: str = "minio123"
    s3_bucket: str = "civic-media"
    s3_region: str = "us-east-1"

    max_media_bytes: int = 50 * 1024 * 1024


@lru_cache
def settings() -> Settings:
    return Settings()