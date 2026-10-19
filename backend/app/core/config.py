from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./zhihuitu.db"
    SECRET_KEY: str = "change-this-to-a-random-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    CHART_TEMPLATES_DIR: str = "../chart-templates"
    ANNOUNCEMENT_UPLOAD_DIR: str = ""
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    BACKEND_AUTO_CREATE_TABLES: bool = True
    BACKEND_SYNC_TEMPLATES_ON_STARTUP: bool = True
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    CHART_GENERATION_MAX_CONCURRENCY: int = 2
    CHART_GENERATION_CACHE_TTL_SECONDS: int = 300
    CHART_GENERATION_CACHE_MAX_ITEMS: int = 64
    AI_REQUEST_TIMEOUT_SECONDS: int = 90
    REDIS_URL: str = "redis://localhost:6379/0"
    AI_DEFAULT_MODEL: str = ""
    # 非空时，在 users 表尚无该用户名则创建（便于 Docker / 全新库首次登录；上线请删除或留空）
    BOOTSTRAP_USER_USERNAME: str = ""
    BOOTSTRAP_USER_PASSWORD: str = ""
    BOOTSTRAP_USER_ROLE: str = "admin"
    # 知识库门户 SSO 来源（不带末尾斜杠，如 https://kb.example.com）；为空则 /auth/sso 直接报错
    KGQA_BASE_URL: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
