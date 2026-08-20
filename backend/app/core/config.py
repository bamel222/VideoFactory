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
    encryption_keys: str = ""
    jwt_secret: str = "change-me-jwt-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    cors_allow_credentials: bool = True

    supabase_enabled: bool = False
    supabase_url: str = ""
    supabase_service_role_key: str = ""

    # Security limits
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    max_payload_bytes: int = 10 * 1024 * 1024
    max_upload_mb: int = 200
    allowed_extensions: str = "mp4,mov,webm,mp3,wav,ogg,jpg,jpeg,png,webp,srt,vtt,json,txt,ttf,otf,zip"

    # Password policy
    password_min_length: int = 12
    password_require_upper: bool = True
    password_require_lower: bool = True
    password_require_digit: bool = True
    password_require_symbol: bool = False
    password_max_age_days: int = 90
    password_history_size: int = 5

    # Login brute-force protection
    login_max_failures: int = 5
    login_lockout_seconds: int = 900
    login_rate_limit: int = 10
    login_rate_window_seconds: int = 60

    # Deep media validation
    max_image_pixels: int = 40_000_000
    max_media_seconds: int = 600

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
    # Allow storage backends (S3/MinIO/Supabase) to target private/internal
    # endpoints. Off by default for SSRF safety; enable only for local MinIO.
    allow_private_storage_endpoints: bool = False

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_extensions_list(self) -> list[str]:
        return [e.strip().lower() for e in self.allowed_extensions.split(",") if e.strip()]

    def insecure_defaults(self) -> list[str]:
        """Return the env-var names of secrets still set to their insecure defaults."""
        return [name for name, default in DEFAULT_SECRET_VALUES.items()
                if getattr(self, name.lower()) == default]


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Insecure fallback values. A production deployment MUST override these via
# environment; otherwise JWTs can be forged and encrypted secrets decrypted.
DEFAULT_SECRET_VALUES = {
    "ENCRYPTION_KEY": "change-me-32-bytes-min-secret-key",
    "JWT_SECRET": "change-me-jwt-secret",
}
