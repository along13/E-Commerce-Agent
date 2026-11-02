"""验证数据库模型约束和演示数据初始化行为。"""

import unittest
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import selectinload

from app.db.base import Base
from app.db.session import create_database_engine
from app.models import Order, OrderItem, Product, User
from app.services.demo_data import seed_demo_data


class DemoDatabaseTests(unittest.IsolatedAsyncioTestCase):
    """使用仅存在于测试进程内的 SQLite 数据库，保护本地演示数据。"""

    async def asyncSetUp(self) -> None:
        # 为每个测试建立空库并创建全部 ORM 表。
        self.engine = create_database_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)

    async def asyncTearDown(self) -> None:
        # 释放测试引擎和内存数据库。
        await self.engine.dispose()

    async def test_seed_is_complete_and_idempotent(self) -> None:
        # 重复运行种子逻辑不会重复插入，并检查用户、订单和金额关系。
        async with self.sessions() as session, session.begin():
            first_counts = await seed_demo_data(session)
        async with self.sessions() as session, session.begin():
            second_counts = await seed_demo_data(session)

        self.assertEqual(first_counts, {
            "users": 2,
            "products": 4,
            "orders": 3,
            "order_items": 5,
        })
        self.assertEqual(second_counts, first_counts)

        async with self.sessions() as session:
            order = await session.scalar(
                select(Order)
                .where(Order.order_no == "EC202611020001")
                .options(selectinload(Order.items), selectinload(Order.user))
            )
            self.assertIsNotNone(order)
            self.assertEqual(order.user.username, "demo_customer")
            self.assertEqual(len(order.items), 2)
            self.assertEqual(str(order.total_amount), "3798.00")

    async def test_catalog_contains_available_and_sold_out_demo_products(self) -> None:
        # 演示目录同时包含有库存和零库存商品。
        async with self.sessions() as session, session.begin():
            await seed_demo_data(session)

        async with self.sessions() as session:
            products = (await session.scalars(select(Product).order_by(Product.sku))).all()
            user_count = await session.scalar(select(func.count()).select_from(User))
            item_count = await session.scalar(select(func.count()).select_from(OrderItem))

        self.assertEqual(len(products), 4)
        self.assertTrue(any(product.stock > 0 for product in products))
        self.assertTrue(any(product.stock == 0 for product in products))
        self.assertEqual(user_count, 2)
        self.assertEqual(item_count, 5)

    async def test_seed_preserves_existing_values_and_order_price_snapshots(self) -> None:
        # 重新初始化不覆盖商品改动，已有订单继续保留原单价快照。
        async with self.sessions() as session, session.begin():
            await seed_demo_data(session)
            product = await session.scalar(select(Product).where(Product.sku == "PHONE-SPRUCE-X1"))
            product.stock = 7
            product.price = Decimal("3199.00")

        async with self.sessions() as session, session.begin():
            await seed_demo_data(session)
            product = await session.scalar(select(Product).where(Product.sku == "PHONE-SPRUCE-X1"))
            self.assertEqual(product.stock, 7)
            self.assertEqual(product.price, Decimal("3199.00"))
            orders = (await session.scalars(select(Order).options(selectinload(Order.items)))).all()
            for order in orders:
                self.assertEqual(
                    order.total_amount,
                    sum((item.unit_price * item.quantity for item in order.items), Decimal("0.00")),
                )
            first_order = next(order for order in orders if order.order_no == "EC202611020001")
            phone_item = next(item for item in first_order.items if item.sku == "PHONE-SPRUCE-X1")
            self.assertEqual(phone_item.unit_price, Decimal("3299.00"))

    async def test_foreign_keys_reject_unknown_user(self) -> None:
        # SQLite 外键应拒绝引用不存在用户的订单。
        with self.assertRaises(IntegrityError):
            async with self.sessions() as session, session.begin():
                session.add(Order(order_no="INVALID-USER", user_id=999, total_amount=Decimal("1.00")))
                await session.flush()

    async def test_stock_constraint_rejects_negative_stock(self) -> None:
        # 商品库存约束拒绝负数。
        with self.assertRaises(IntegrityError):
            async with self.sessions() as session, session.begin():
                session.add(Product(sku="INVALID-STOCK", name="Invalid stock", category="test",
                                    price=Decimal("1.00"), stock=-1))
                await session.flush()

    async def test_unique_sku_and_positive_quantity_constraints(self) -> None:
        # 唯一 SKU 和正数量规则由数据库约束保证。
        async with self.sessions() as session, session.begin():
            await seed_demo_data(session)

        with self.assertRaises(IntegrityError):
            async with self.sessions() as session, session.begin():
                session.add(Product(sku="PHONE-SPRUCE-X1", name="Duplicate", category="test",
                                    price=Decimal("1.00"), stock=1))
                await session.flush()

        with self.assertRaises(IntegrityError):
            async with self.sessions() as session, session.begin():
                order_id = await session.scalar(select(Order.id).where(Order.order_no == "EC202611020003"))
                product_id = await session.scalar(select(Product.id).where(Product.sku == "BAG-TRAIL-02"))
                session.add(OrderItem(order_id=order_id, product_id=product_id, product_name="Invalid quantity",
                                      sku="BAG-TRAIL-02", unit_price=Decimal("259.00"), quantity=0))
                await session.flush()


if __name__ == "__main__":
    unittest.main()
