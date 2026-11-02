"""FastAPI 应用入口：注册全局中间件、业务路由和健康检查。"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="E-commerce intelligent customer service API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 聊天路由以统一的 /api/v1 前缀提供版本化 API。
app.include_router(chat_router)


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """供前端和运行环境探测服务是否已启动。"""
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}

