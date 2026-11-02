"""创建异步数据库引擎，并按请求提供可自动关闭的会话。"""

from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


def create_database_engine(database_url: str = settings.database_url) -> AsyncEngine:
    """创建异步引擎；文件型 SQLite 的父目录不存在时会先创建目录。"""
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite" and url.database not in (None, "", ":memory:"):
        Path(url.database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
    engine = create_async_engine(database_url, pool_pre_ping=True)
    if url.get_backend_name() == "sqlite":

        @event.listens_for(engine.sync_engine, "connect")
        def enable_sqlite_foreign_keys(connection, _record) -> None:
            # SQLite 默认不执行外键约束，每条新连接都必须单独开启。
            cursor = connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


engine = create_database_engine()
# 每次 API 请求复用工厂创建独立 AsyncSession；提交后 ORM 对象仍可读取属性。
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI 依赖：请求期间共享一个会话，结束后确保关闭连接。"""
    async with SessionLocal() as session:
        yield session
