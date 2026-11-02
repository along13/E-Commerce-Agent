# E-Commerce Intelligent Customer Service Agent

电商智能客服 Agent，按阶段逐步实现。本仓库目前已完成阶段一、二、三。每阶段完成检查并汇报后暂停，得到确认再开始下一阶段。

## 环境要求

- Python 3.10+（`ecommerce` Conda 环境）
- Node.js 22+（本机验证：22.23.2）
- npm 10+（本机验证：10.9.8）

## 后端环境（终端一）

在项目根目录打开 PowerShell。无需激活虚拟环境，也无需修改执行策略：

```powershell
conda activate ecommerce
cd D:\Code\E-Commerce-Agent\backend
python -m pip install -r requirements.txt
Copy-Item .env.example .env  # 仅首次需要；已有 .env 时保留现有配置
python -m app.scripts.init_db  # 首次初始化，或项目新增数据库表后安全地补建表
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

后端健康检查：<http://127.0.0.1:8000/health>

接口文档：<http://127.0.0.1:8000/docs>

后续启动先激活 `ecommerce`，再运行最后一条命令。初始化脚本可以安全地重复运行，不会重复插入演示数据。

数据库表有新增时（例如增加聊天表），先停掉后端并再次运行 `python -m app.scripts.init_db`。它会创建缺失表并保留已有数据；不会自动升级已存在表的字段结构。

## 启动前端（终端二）

另开终端，从项目根目录执行：

```powershell
cd frontend
Copy-Item .env.example .env
npm ci
npm run dev
```

打开 <http://127.0.0.1:5173>，页面会通过浏览器跨域请求检查后端状态。

后续启动只需进入 `frontend`，执行 `npm run dev`。`npm ci` 使用随仓库提供的锁文件安装相同依赖。

## 配置和检查

- `backend/.env`：应用名称、版本和 CORS 允许来源；配置文件位置固定，不随启动目录改变。
- 默认数据库为 `backend/data/ecommerce.db`；数据库文件会在首次初始化时创建并保持在项目内，与 PyCharm 启动目录无关。可通过后端 `.env` 的 `DATABASE_URL` 指向其他兼容的异步数据库。
- `frontend/.env`：`VITE_API_BASE_URL` 指向后端，默认 `http://127.0.0.1:8000`；修改后重启 Vite。该变量会公开给浏览器，不要填写密钥。
- 允许的开发来源为 `http://127.0.0.1:5173` 和 `http://localhost:5173`。修改前端端口时也要更新后端 CORS 配置。
- 前端连接失败时显示错误，可点击“重新检查”；请求 5 秒超时。
- Vite 固定使用 5173 端口，占用时直接报错，不会自动切换端口。
- 前端检查：在 `frontend` 执行 `npm run build`，包含 TypeScript 检查与生产构建。
- 退出服务：在各自终端按 `Ctrl+C`。

源码和可注释配置已在关键模块、数据约束、请求流程与样式分区处添加说明。`package.json` 和 `package-lock.json` 使用严格 JSON 格式，不支持注释；依赖用途和启动方式放在本 README 中。`tsconfig.json` 支持 JSONC 注释。PyCharm 的 `.idea` 文件及本机 `backend/.env` 属于生成或本地配置，未做注释改动。

## 基础聊天 API（阶段三）

数据库初始化后，后端提供以下接口。当前回复是固定占位文案，用于验证消息持久化闭环；LLM 和前端聊天页面会在后续阶段接入。本地演示 API 暂无登录认证，不要公开部署或写入真实个人信息。

创建匿名会话：

```http
POST /api/v1/chat/sessions
Content-Type: application/json

{}
```

也可提交已有演示用户的 `user_id`，例如 `{"user_id": 1}`。成功返回 `201` 和会话 ID。

发送消息（内容去除首尾空白，长度为 1-4000 字符）：

```http
POST /api/v1/chat/sessions/{session_id}/messages
Content-Type: application/json

{"content":"你好，我想咨询订单"}
```

用户消息和占位客服回复在同一事务中保存，并一起返回。读取历史：

```http
GET /api/v1/chat/sessions/{session_id}/messages?offset=0&limit=50
```

历史按消息 ID 正序返回；`limit` 最大为 100。不存在的用户/会话返回 `404`，已关闭会话返回 `409`，无效消息或分页参数返回 `422`。所有 API 时间戳以 UTC 的 `Z` 格式返回。

预期健康检查响应：

```json
{"status":"ok","service":"E-Commerce Customer Service API","version":"0.1.0"}
```

## 项目目录

```text
backend/
  app/main.py            # FastAPI 入口和健康检查
  app/api/               # HTTP 路由
  app/core/config.py     # 环境配置
  app/db/                # 异步 SQLAlchemy 引擎和会话
  app/models/            # 用户、商品、订单、会话和消息模型
  app/schemas/            # API 请求/响应类型
  app/services/           # 聊天逻辑和演示数据
  app/services/demo_data.py # 幂等演示数据
  app/scripts/init_db.py # 数据库和演示数据初始化
  tests/                 # 数据模型和演示数据检查
  requirements.txt       # Python 依赖
  .env.example           # 后端配置模板
frontend/
  src/App.vue            # 基础首页和连接状态
  src/services/health.ts # 健康检查请求
  src/types/health.ts    # 响应类型
  src/styles.css         # 响应式样式
  vite.config.ts         # 本地开发服务器配置
  package-lock.json      # 前端依赖锁文件
  .env.example           # 前端配置模板
docs/                    # 阶段验收记录
```

## 当前阶段边界

当前包含 FastAPI 健康检查、Vue 基础首页、SQLite 数据库、用户/商品/订单/订单明细/聊天会话/聊天消息表及基础聊天 API。聊天回复仍为固定占位文案，不包含 LLM、RAG、意图识别、情感分析或 Agent 工具。
