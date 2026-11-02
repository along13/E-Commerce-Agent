"""聊天 HTTP 接口；负责校验请求、调用服务层并定义响应形状。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.chat import (
    ChatMessageCreate,
    ChatMessagePage,
    ChatMessagePair,
    ChatSessionCreate,
    ChatSessionRead,
)
from app.services.chat_service import create_chat_session, list_chat_messages, send_chat_message


router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
# Annotated 让所有路由统一通过 FastAPI 依赖获得异步数据库会话。
DatabaseSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
    "/sessions",
    response_model=ChatSessionRead,
    status_code=status.HTTP_201_CREATED,
    summary="创建聊天会话",
)
async def create_session(payload: ChatSessionCreate, session: DatabaseSession) -> ChatSessionRead:
    """创建匿名会话；如果提供用户 ID，服务层会先确认用户存在。"""
    return await create_chat_session(session, user_id=payload.user_id)


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatMessagePair,
    status_code=status.HTTP_201_CREATED,
    summary="发送消息",
)
async def send_message(
    session_id: str,
    payload: ChatMessageCreate,
    session: DatabaseSession,
) -> ChatMessagePair:
    """保存一条用户消息和对应回复，并将二者一并返回。"""
    user_message, assistant_message = await send_chat_message(
        session, session_id, payload.content
    )
    return ChatMessagePair(
        user_message=user_message,
        assistant_message=assistant_message,
    )


@router.get(
    "/sessions/{session_id}/messages",
    response_model=ChatMessagePage,
    summary="读取会话消息历史",
)
async def get_messages(
    session_id: str,
    session: DatabaseSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> ChatMessagePage:
    """按消息 ID 正序分页读取会话历史，便于按对话顺序渲染。"""
    total, messages = await list_chat_messages(session, session_id, offset, limit)
    return ChatMessagePage(
        session_id=session_id,
        total=total,
        offset=offset,
        limit=limit,
        items=messages,
    )

