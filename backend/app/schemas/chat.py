"""聊天 API 的输入校验和输出序列化模型。"""

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.models.chat import MessageSender


class ChatSessionCreate(BaseModel):
    """创建会话请求；user_id 为空表示匿名会话。"""

    user_id: int | None = Field(default=None, gt=0)


class ChatSessionRead(BaseModel):
    """会话公开字段，不暴露 ORM 内部状态。"""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_utc_datetime(self, value: datetime) -> str:
        # SQLite 不保存时区信息，序列化时将无时区值按 UTC 处理。
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class ChatMessageCreate(BaseModel):
    """发送消息请求；先去除首尾空白，再执行长度校验。"""

    content: str = Field(min_length=1, max_length=4000)

    @field_validator("content", mode="before")
    @classmethod
    def strip_message(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ChatMessageRead(BaseModel):
    """单条消息响应，统一输出 UTC 时间戳。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: str
    sender: MessageSender
    content: str
    created_at: datetime

    @field_serializer("created_at")
    def serialize_utc_datetime(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class ChatMessagePage(BaseModel):
    """分页历史响应；total 用于前端判断是否还有更多消息。"""

    session_id: str
    total: int
    offset: int
    limit: int
    items: list[ChatMessageRead]


class ChatMessagePair(BaseModel):
    """发送消息后的成对响应，包含用户消息和客服占位回复。"""

    user_message: ChatMessageRead
    assistant_message: ChatMessageRead
