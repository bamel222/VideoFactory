from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Video Factory AI"
    environment: str = "dev"
    backend_port: int = 3001

    database_url: str = "sqlite:///./video_factory.db"
    redis_url: str = "redis://localhost:6379/0"

    encryption_key: str = "change-me-32-bytes-min-secret-key"
    jwt_secret: str = "change-me-jwt-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    cors_origins: str = "http://localhost:3000,http://localhost:3001"

    supabase_enabled: bool = False
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # Security limits
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    max_payload_bytes: int = 10 * 1024 * 1024
    max_upload_mb: int = 200
    allowed_extensions: str = "mp4,mov,webm,mp3,wav,ogg,jpg,jpeg,png,webp,srt,vtt,json,txt,ttf,otf,zip"

    # Provider keys come from env at runtime (never stored in settings)
    openai_api_key: str = ""
    deepgram_api_key: str = ""
    deepl_api_key: str = ""
    elevenlabs_api_key: str = ""
    heygen_api_key: str = ""
    cartesia_api_key: str = ""
    pcloud_client_id: str = ""
    pcloud_app_secret: str = ""

    # Behavior
    use_fake_providers: bool = True
    data_dir: str = "./data"
    montage_enabled: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [e.strip().lower() for e in self.allowed_extensions.split(",") if e.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
