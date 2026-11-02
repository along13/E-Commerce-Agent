"""创建缺失表并导入演示数据的命令行入口。"""

import asyncio

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models import Order, OrderItem, Product, User  # noqa: F401 - register models
from app.services.demo_data import seed_demo_data


async def initialize_database() -> dict[str, int]:
    """创建当前模型尚不存在的表，再在事务中幂等写入演示数据。"""
    try:
        async with engine.begin() as connection:
            # create_all 不会删除或覆盖已有数据；结构迁移需另行使用迁移工具。
            await connection.run_sync(Base.metadata.create_all)

        async with SessionLocal() as session:
            async with session.begin():
                return await seed_demo_data(session)
    finally:
        await engine.dispose()


def main() -> None:
    """供 ``python -m app.scripts.init_db`` 调用并打印初始化摘要。"""
    counts = asyncio.run(initialize_database())
    print(f"Database ready: {engine.url.database}")
    print(
        "Demo data: "
        f"{counts['users']} users, {counts['products']} products, "
        f"{counts['orders']} orders, {counts['order_items']} order items"
    )


if __name__ == "__main__":
    main()
