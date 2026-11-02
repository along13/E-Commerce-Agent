"""聊天领域服务：封装会话校验、消息事务和历史查询。"""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ChatMessage, ChatSession, MessageSender, User


PLACEHOLDER_REPLY = (
    # 阶段三只验证持久化闭环；后续阶段会在此处接入 LLM/Agent 编排。
    "收到您的消息，当前基础聊天服务已接通。智能客服回复能力将在后续阶段接入。"
)


async def create_chat_session(session: AsyncSession, user_id: int | None = None) -> ChatSession:
    """创建会话；关联用户时先做存在性检查，避免产生无效外键。"""
    if user_id is not None:
        user_exists = await session.scalar(select(User.id).where(User.id == user_id))
        if user_exists is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    chat_session = ChatSession(user_id=user_id)
    session.add(chat_session)
    await session.commit()
    await session.refresh(chat_session)
    return chat_session


async def send_chat_message(
    session: AsyncSession, session_id: str, content: str
) -> tuple[ChatMessage, ChatMessage]:
    """在同一事务中写入用户消息和占位回复，保证历史不会只保存一半。"""
    chat_session = await session.get(ChatSession, session_id)
    if chat_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")
    if not chat_session.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="会话已关闭")

    activity_at = datetime.now(timezone.utc)
    user_message = ChatMessage(
        session_id=session_id,
        sender=MessageSender.USER,
        content=content,
        created_at=activity_at,
    )
    assistant_message = ChatMessage(
        session_id=session_id,
        sender=MessageSender.ASSISTANT,
        content=PLACEHOLDER_REPLY,
        created_at=activity_at,
    )
    chat_session.updated_at = activity_at
    session.add_all([user_message, assistant_message])

    # 用户消息、占位回复和会话活动时间必须原子提交。
    await session.commit()
    await session.refresh(user_message)
    await session.refresh(assistant_message)
    return user_message, assistant_message


async def list_chat_messages(
    session: AsyncSession, session_id: str, offset: int, limit: int
) -> tuple[int, list[ChatMessage]]:
    """校验会话后按消息 ID 正序分页查询历史。"""
    chat_session = await session.get(ChatSession, session_id)
    if chat_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="会话不存在")

    total = int(
        await session.scalar(
            select(func.count(ChatMessage.id)).where(ChatMessage.session_id == session_id)
        )
        or 0
    )
    messages = list(
        (
            await session.scalars(
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.id.asc())
                .offset(offset)
                .limit(limit)
            )
        ).all()
    )
    return total, messages
