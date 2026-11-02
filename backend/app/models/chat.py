"""聊天会话与消息的持久化模型。"""

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MessageSender(str, Enum):
    """消息发送方；system 预留给后续内部系统消息。"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatSession(Base):
    """一次对话的容器；user_id 为空表示尚未关联账号的访客会话。"""

    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    user: Mapped["User | None"] = relationship(back_populates="chat_sessions")
    # 会话删除时通过 ORM 级联清除其消息，避免遗留无主记录。
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.id"
    )


class ChatMessage(Base):
    """单条聊天记录；正文长度和非空规则也在数据库层复核。"""

    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint("length(trim(content)) > 0", name="ck_chat_messages_content_nonempty"),
        CheckConstraint("length(content) <= 4000", name="ck_chat_messages_content_max_length"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sender: Mapped[MessageSender] = mapped_column(
        SqlEnum(
            MessageSender,
            name="message_sender",
            native_enum=False,
            values_callable=lambda enum_type: [item.value for item in enum_type],
        ),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )

    session: Mapped[ChatSession] = relationship(back_populates="messages")
