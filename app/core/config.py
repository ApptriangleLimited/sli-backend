from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/project_db"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40
    DATABASE_POOL_RECYCLE: int = 1800
    UPLOAD_ROOT: str = "./uploads"
    MAX_UPLOAD_BYTES: int = 26_214_400  # 25 MiB
    JWT_SECRET_KEY: str = "change_this_secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REMEMBER_ME_ACCESS_TOKEN_EXPIRE_DAYS: int = 7
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    CORS_ORIGINS: str = "http://localhost:8080,http://127.0.0.1:8080"
    # Optional regex string from env (e.g. Vercel preview URLs). Empty = disabled.
    CORS_ORIGIN_REGEX: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def cors_origin_regex(self) -> str | None:
        raw = self.CORS_ORIGIN_REGEX.strip()
        return raw or None


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
