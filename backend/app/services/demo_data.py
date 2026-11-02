"""本地演示数据定义与幂等写入逻辑。"""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Order, OrderItem, OrderStatus, Product, User, UserType


# 这些记录只供本地演示和自动化测试，不代表真实用户数据。
DEMO_USERS = (
    {
        "username": "demo_customer",
        "email": "customer@example.com",
        "phone": "13800000001",
        "user_type": UserType.CUSTOMER,
    },
    {
        "username": "demo_customer_2",
        "email": "customer2@example.com",
        "phone": "13800000002",
        "user_type": UserType.CUSTOMER,
    },
)

DEMO_PRODUCTS = (
    {
        "sku": "PHONE-SPRUCE-X1",
        "name": "云杉 X1 智能手机",
        "brand": "云杉数码",
        "category": "手机数码",
        "price": Decimal("3299.00"),
        "stock": 18,
        "sales_count": 2381,
        "description": "演示商品：6.5 英寸屏幕，256GB 存储。",
    },
    {
        "sku": "AUDIO-BOAT-PRO",
        "name": "轻舟 Pro 无线耳机",
        "brand": "轻舟科技",
        "category": "数码配件",
        "price": Decimal("499.00"),
        "stock": 42,
        "sales_count": 5260,
        "description": "演示商品：主动降噪，支持蓝牙连接。",
    },
    {
        "sku": "HOME-BREWER-01",
        "name": "晨雾家用咖啡机",
        "brand": "晨雾生活",
        "category": "家用电器",
        "price": Decimal("899.00"),
        "stock": 8,
        "sales_count": 714,
        "description": "演示商品：适用于家庭日常咖啡冲煮。",
    },
    {
        "sku": "BAG-TRAIL-02",
        "name": "山径轻量双肩包",
        "brand": "山径户外",
        "category": "户外用品",
        "price": Decimal("259.00"),
        "stock": 0,
        "sales_count": 302,
        "description": "演示商品：轻量通勤背包，当前模拟库存为零。",
    },
)

DEMO_ORDERS = (
    {
        "order_no": "EC202611020001",
        "username": "demo_customer",
        "status": OrderStatus.SHIPPED,
        "items": (("PHONE-SPRUCE-X1", 1), ("AUDIO-BOAT-PRO", 1)),
    },
    {
        "order_no": "EC202611020002",
        "username": "demo_customer",
        "status": OrderStatus.DELIVERED,
        "items": (("AUDIO-BOAT-PRO", 1), ("BAG-TRAIL-02", 1)),
    },
    {
        "order_no": "EC202611020003",
        "username": "demo_customer_2",
        "status": OrderStatus.PAID,
        "items": (("HOME-BREWER-01", 1),),
    },
)


async def seed_demo_data(session: AsyncSession) -> dict[str, int]:
    """按业务唯一键补齐演示数据，不覆盖用户已有的商品价格或库存修改。"""
    users: dict[str, User] = {}
    for row in DEMO_USERS:
        user = await session.scalar(select(User).where(User.username == row["username"]))
        if user is None:
            user = User(**row)
            session.add(user)
        users[row["username"]] = user

    products: dict[str, Product] = {}
    for row in DEMO_PRODUCTS:
        product = await session.scalar(select(Product).where(Product.sku == row["sku"]))
        if product is None:
            product = Product(**row)
            session.add(product)
        products[row["sku"]] = product

    # 先落库父记录，确保新增用户和商品拥有可用于关联的主键。
    await session.flush()

    for row in DEMO_ORDERS:
        order = await session.scalar(select(Order).where(Order.order_no == row["order_no"]))
        if order is not None:
            continue

        # 订单明细复制商品名称、SKU 和价格，形成历史快照。
        items = [
            OrderItem(
                product=products[sku],
                product_name=products[sku].name,
                sku=sku,
                unit_price=products[sku].price,
                quantity=quantity,
            )
            for sku, quantity in row["items"]
        ]
        # Decimal 避免金额计算中的二进制浮点误差。
        total_amount = sum(
            (item.unit_price * item.quantity for item in items), start=Decimal("0.00")
        )
        session.add(
            Order(
                order_no=row["order_no"],
                user=users[row["username"]],
                status=row["status"],
                total_amount=total_amount,
                items=items,
            )
        )

    await session.flush()
    return {
        "users": int(await session.scalar(select(func.count()).select_from(User)) or 0),
        "products": int(await session.scalar(select(func.count()).select_from(Product)) or 0),
        "orders": int(await session.scalar(select(func.count()).select_from(Order)) or 0),
        "order_items": int(await session.scalar(select(func.count()).select_from(OrderItem)) or 0),
    }
