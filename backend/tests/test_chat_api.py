"""使用内存 SQLite 对聊天 REST API 做隔离集成测试。"""

import unittest

from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.base import Base
from app.db.session import create_database_engine, get_db
from app.main import app
from app.models import ChatMessage, ChatSession
from app.services.demo_data import seed_demo_data


class ChatApiTests(unittest.IsolatedAsyncioTestCase):
    """每个测试单独建库，避免读写项目中的本地演示数据库。"""

    async def asyncSetUp(self) -> None:
        # 创建临时表、演示用户并覆盖请求级数据库依赖。
        self.engine = create_database_engine("sqlite+aiosqlite:///:memory:")
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self.sessions() as session, session.begin():
            await seed_demo_data(session)

        async def override_get_db():
            async with self.sessions() as session:
                yield session

        app.dependency_overrides[get_db] = override_get_db
        self.client = AsyncClient(
            transport=ASGITransport(app=app), base_url="http://testserver"
        )

    async def asyncTearDown(self) -> None:
        # 移除依赖覆盖并关闭客户端和内存数据库连接。
        await self.client.aclose()
        app.dependency_overrides.pop(get_db, None)
        await self.engine.dispose()

    async def create_session(self, user_id: int | None = None) -> dict:
        # 通过实际路由创建测试会话，并断言创建状态码。
        payload = {} if user_id is None else {"user_id": user_id}
        response = await self.client.post("/api/v1/chat/sessions", json=payload)
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    async def test_create_anonymous_and_user_linked_sessions(self) -> None:
        # 匿名和已关联用户的会话都应能成功创建。
        anonymous = await self.create_session()
        linked = await self.create_session(user_id=1)

        self.assertEqual(anonymous["user_id"], None)
        self.assertTrue(anonymous["is_active"])
        self.assertEqual(linked["user_id"], 1)
        self.assertTrue(anonymous["id"])
        self.assertTrue(anonymous["created_at"].endswith("Z"))

    async def test_create_session_rejects_unknown_user(self) -> None:
        # 无效用户 ID 应被服务层拒绝，而非写入孤立会话。
        response = await self.client.post(
            "/api/v1/chat/sessions", json={"user_id": 99999}
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "用户不存在")

    async def test_send_persists_user_and_placeholder_reply_and_lists_history(self) -> None:
        # 验证输入清理、成对消息持久化、UTC 响应和会话更新时间。
        chat = await self.create_session()
        session_id = chat["id"]

        sent = await self.client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"content": "  你好，请问订单到哪里了？  "},
        )
        self.assertEqual(sent.status_code, 201, sent.text)
        pair = sent.json()
        self.assertEqual(pair["user_message"]["sender"], "user")
        self.assertEqual(pair["user_message"]["content"], "你好，请问订单到哪里了？")
        self.assertEqual(pair["assistant_message"]["sender"], "assistant")
        self.assertIn("后续阶段接入", pair["assistant_message"]["content"])

        history = await self.client.get(f"/api/v1/chat/sessions/{session_id}/messages")
        self.assertEqual(history.status_code, 200, history.text)
        body = history.json()
        self.assertEqual(body["total"], 2)
        self.assertEqual([item["id"] for item in body["items"]], sorted(
            item["id"] for item in body["items"]
        ))
        self.assertEqual([item["sender"] for item in body["items"]], ["user", "assistant"])
        self.assertTrue(all(item["created_at"].endswith("Z") for item in body["items"]))

        async with self.sessions() as session:
            records = list((await session.scalars(
                select(ChatMessage).where(ChatMessage.session_id == session_id)
            )).all())
            stored_session = await session.get(ChatSession, session_id)
        self.assertEqual(len(records), 2)
        self.assertEqual(stored_session.updated_at, records[-1].created_at)

    async def test_message_history_paginates_and_isolated_by_session(self) -> None:
        # 分页只读取指定会话的消息，不泄露其他会话的历史。
        first = await self.create_session()
        second = await self.create_session()
        for content in ("第一条", "第二条"):
            response = await self.client.post(
                f"/api/v1/chat/sessions/{first['id']}/messages", json={"content": content}
            )
            self.assertEqual(response.status_code, 201, response.text)

        page = await self.client.get(
            f"/api/v1/chat/sessions/{first['id']}/messages?offset=1&limit=2"
        )
        empty = await self.client.get(
            f"/api/v1/chat/sessions/{second['id']}/messages"
        )
        self.assertEqual(page.json()["total"], 4)
        self.assertEqual(page.json()["offset"], 1)
        self.assertEqual(len(page.json()["items"]), 2)
        self.assertEqual(empty.json()["total"], 0)
        self.assertEqual(empty.json()["items"], [])

    async def test_rejects_blank_long_and_malformed_messages(self) -> None:
        # 无效正文请求返回 422，且不留下部分消息记录。
        chat = await self.create_session()
        url = f"/api/v1/chat/sessions/{chat['id']}/messages"
        for payload in ({"content": "  \n "}, {"content": "x" * 4001}, {"text": "missing content"}):
            response = await self.client.post(url, json=payload)
            self.assertEqual(response.status_code, 422)

        history = await self.client.get(f"/api/v1/chat/sessions/{chat['id']}/messages")
        self.assertEqual(history.json()["total"], 0)

    async def test_missing_or_closed_sessions_are_reported(self) -> None:
        # 不存在的会话返回 404，关闭的会话拒绝新消息并返回 409。
        missing_id = "00000000-0000-0000-0000-000000000000"
        missing_message = await self.client.post(
            f"/api/v1/chat/sessions/{missing_id}/messages", json={"content": "hello"}
        )
        missing_history = await self.client.get(
            f"/api/v1/chat/sessions/{missing_id}/messages"
        )
        self.assertEqual(missing_message.status_code, 404)
        self.assertEqual(missing_history.status_code, 404)

        chat = await self.create_session()
        async with self.sessions() as session, session.begin():
            stored_session = await session.get(ChatSession, chat["id"])
            stored_session.is_active = False

        closed = await self.client.post(
            f"/api/v1/chat/sessions/{chat['id']}/messages", json={"content": "hello"}
        )
        self.assertEqual(closed.status_code, 409)
        self.assertEqual(closed.json()["detail"], "会话已关闭")
        async with self.sessions() as session:
            records = list((await session.scalars(select(ChatMessage))).all())
        self.assertEqual(records, [])

    async def test_history_query_bounds_and_health_endpoint(self) -> None:
        # 检查分页参数边界，并保证原健康检查接口仍可用。
        chat = await self.create_session()
        too_many = await self.client.get(
            f"/api/v1/chat/sessions/{chat['id']}/messages?limit=101"
        )
        negative_offset = await self.client.get(
            f"/api/v1/chat/sessions/{chat['id']}/messages?offset=-1"
        )
        health = await self.client.get("/health")
        self.assertEqual(too_many.status_code, 422)
        self.assertEqual(negative_offset.status_code, 422)
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ok")


if __name__ == "__main__":
    unittest.main()
