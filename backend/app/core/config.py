from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://jobcrm:password@db:5432/jobcrm"
    DATABASE_URL_SYNC: str = "postgresql://jobcrm:password@db:5432/jobcrm"

    # Redis
    REDIS_URL: str = "redis://:redispassword@redis:6379/0"

    # Auth
    JWT_SECRET_KEY: str = "change-me-to-a-random-256-bit-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Single user credentials
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "changeme"

    # Anthropic
    ANTHROPIC_API_KEY: str = "sk-ant-..."
    CLAUDE_MODEL: str = "claude-sonnet-4-6"
    CLAUDE_MAX_TOKENS: int = 2048
    CLAUDE_DAILY_BUDGET_USD: float = 5.00

    # Browser session encryption
    BROWSER_SESSION_ENCRYPTION_KEY: str = "0000000000000000000000000000000000000000000000000000000000000000"

    # Notifications
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # Rate limits
    MAX_APPLICATIONS_PER_DAY: int = 10
    MAX_JOBS_COLLECTED_PER_RUN: int = 30
    MAX_COLLECTION_RUNS_PER_DAY: int = 4
    PLAYWRIGHT_MIN_DELAY_MS: int = 2000
    PLAYWRIGHT_MAX_DELAY_MS: int = 8000

    # Storage
    CV_UPLOAD_DIR: str = "/app/uploads"
    MAX_CV_SIZE_BYTES: int = 5242880

    # App
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
