\
import os
from typing import List

class Settings:
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    WORKERS: int = int(os.getenv("WORKERS", "4"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./simmental_nutrition.db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    # 开发期允许所有源，彻底避免 localhost:3000 / 8080 跨域问题
    CORS_ORIGINS: List[str] = ["*"]
    ENABLE_SCHEDULER: bool = os.getenv("ENABLE_SCHEDULER", "true").lower() == "true"
    PRICE_CHECK_INTERVAL_HOURS: int = int(os.getenv("PRICE_CHECK_INTERVAL_HOURS", "6"))
    NUTRITION_CHECK_INTERVAL_HOURS: int = int(os.getenv("NUTRITION_CHECK_INTERVAL_HOURS", "12"))
    ALERT_WS_PUSH: bool = os.getenv("ALERT_WS_PUSH", "true").lower() == "true"
    NRC_VERSION: str = "2001"

settings = Settings()
