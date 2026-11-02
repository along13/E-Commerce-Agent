"""声明所有 SQLAlchemy ORM 表共用的元数据基类。"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """所有数据库模型都继承该类，供建表脚本统一发现模型定义。"""
