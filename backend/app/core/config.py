"""从环境变量或 backend/.env 读取运行配置，并提供类型化默认值。"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """后端配置；默认数据库路径固定在 backend/data 下，不依赖启动目录。"""

    app_name: str = "E-Commerce Customer Service API"
    app_version: str = "0.1.0"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    database_url: str = (
        # URL 使用正斜杠以兼容 SQLAlchemy URL 解析和 Windows 文件路径。
        f"sqlite+aiosqlite:///{(Path(__file__).resolve().parents[2] / 'data' / 'ecommerce.db').as_posix()}"
    )

    # 显式指定 .env 位置，确保从 PyCharm 或项目根目录启动时读取相同配置。
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """缓存 Settings 实例，避免每次依赖注入都重新读取配置文件。"""
    return Settings()


settings = get_settings()
