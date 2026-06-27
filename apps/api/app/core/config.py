from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-this-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    ALLOWED_ORIGINS: str = "http://localhost:3000,https://vtuber-studio-web.onrender.com"

    # Database
    DATABASE_URL: str = "postgresql://vtuber:vtuber_pass@localhost:5432/vtuber_studio"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # YouTube OAuth
    YOUTUBE_CLIENT_ID: str = ""
    YOUTUBE_CLIENT_SECRET: str = ""
    YOUTUBE_REDIRECT_URI: str = "https://vtuber-studio-api-p1yp.onrender.com/api/youtube/oauth/callback"

    # OpenAI
    OPENAI_API_KEY: str = ""

    # X (Twitter) API — Basic plan ($100/month)
    X_API_KEY: str = ""
    X_API_SECRET: str = ""
    X_ACCESS_TOKEN: str = ""
    X_ACCESS_TOKEN_SECRET: str = ""
    X_BEARER_TOKEN: str = ""

    # TTS
    TTS_PROVIDER: str = "mock"
    TTS_API_KEY: str = ""
    VOICEVOX_URL: str = "http://localhost:50021"

    # Image Generation
    IMAGE_GENERATION_PROVIDER: str = "mock"
    IMAGE_GENERATION_API_KEY: str = ""

    # Video Generation
    VIDEO_GENERATION_PROVIDER: str = "mock"
    VIDEO_GENERATION_API_KEY: str = ""

    # Storage
    STORAGE_PROVIDER: str = "local"
    STORAGE_BUCKET: str = "vtuber-uploads"
    STORAGE_ACCESS_KEY: str = ""
    STORAGE_SECRET_KEY: str = ""
    STORAGE_BASE_URL: str = "http://localhost:8000/static"

    # File paths
    UPLOAD_DIR: str = "static/uploads"

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]


settings = Settings()
