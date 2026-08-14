# FastAPI 后端

阶段 5 后端在工单闭环基础上增加关闭事务内候选生成、管理员复核 API 和 Dify Dataset Integration。初始资料仍在 Dify 控制台导入，后端只处理工单产生的增量知识。

## 后端架构

后端采用轻量 `Router -> Service -> Repository / Integration` 分层。Router 只处理 HTTP，Service 承载业务规则，Repository 负责 SQLAlchemy 查询和持久化，Dify Integration 只适配外部请求与响应。

详细职责、调用链和扩展规则见 [`docs/backend-layering.md`](../docs/backend-layering.md)。

## 配置

```powershell
cd backend
Copy-Item .env.example .env
```

必须配置项目专用数据库账号和随机 JWT Secret。真实值只保存在 `backend/.env`：

```dotenv
MYSQL_HOST=192.168.100.42
MYSQL_PORT=3306
MYSQL_USER=llm_ops_app
MYSQL_PASSWORD=<数据库密码>
MYSQL_DATABASE=dify_ops

JWT_SECRET_KEY=<至少32字节的随机值>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=120

DIFY_BASE_URL=https://api.dify.ai/v1
DIFY_APP_API_KEY=<Dify App API Key>
DIFY_DATASET_API_KEY=<Dify Dataset API Key>
DIFY_DATASET_ID=<当前 Chatflow 使用的 Dataset ID>
DIFY_TIMEOUT_SECONDS=60
```

可用以下命令在本机生成 JWT Secret：

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## MySQL 最小权限模板

以下 SQL 由数据库管理员在虚拟机执行，必须替换密码占位符：

```sql
CREATE USER IF NOT EXISTS 'llm_ops_app'@'%' IDENTIFIED BY '<STRONG_PASSWORD>';
ALTER USER 'llm_ops_app'@'%' IDENTIFIED BY '<STRONG_PASSWORD>';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, DROP, REFERENCES
ON dify_ops.* TO 'llm_ops_app'@'%';
FLUSH PRIVILEGES;
SHOW GRANTS FOR 'llm_ops_app'@'%';
```

该账号不得获得其他数据库或全局管理权限。正式部署前应将 Host `%` 限制为实际来源地址。

## 安装、迁移与启动

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic history
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

健康检查：`GET http://127.0.0.1:8000/api/v1/health`

## 阶段 7 生产页面托管

执行前端生产构建后，仍使用原入口启动后端：

```powershell
cd ..\frontend
npm run build
cd ..\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

当 `frontend/dist/index.html` 存在时，FastAPI 同时托管 Vue 页面和 `/assets`；不存在时只提供现有 API，非 API 路径返回 `404`。API 始终使用 `/api/v1` 前缀并优先于 SPA 页面回退。

## 初始管理员

首次迁移后，在 `backend/.env` 临时填写：

```dotenv
INITIAL_ADMIN_USERNAME=<用户名>
INITIAL_ADMIN_DISPLAY_NAME=<显示姓名>
INITIAL_ADMIN_PASSWORD=<至少8位且同时包含字母和数字>
INITIAL_ADMIN_ENABLED=true
```

启动后端会幂等创建第一个管理员。同名管理员已存在时不会重复创建；同名普通用户存在时启动失败，不会自动升级角色。创建成功后立即改为：

```dotenv
INITIAL_ADMIN_PASSWORD=
INITIAL_ADMIN_ENABLED=false
```

初始管理员首次登录必须修改密码。密码和哈希不会进入 API 响应或日志。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

自动化测试使用隔离 SQLite，不连接或污染远程 MySQL。共享开发库不执行 destructive downgrade（破坏性降级）。

## 智能问答 API

- `GET /api/v1/chat/current`：恢复当前用户最近一次已保存会话。
- `POST /api/v1/chat/messages`：发送问题；`start_new=true` 时断开旧 Dify 上下文。
- `POST /api/v1/chat/new`：返回新对话状态，不立即写数据库。
- `GET /api/v1/chat/history?limit=50`：读取当前用户最近 50 条记录。
- `PUT /api/v1/chat/messages/{id}/feedback`：保存或覆盖本地反馈。

所有接口要求已登录且完成强制改密。operator 和 admin 都只能访问自己的问答数据。Dify 成功但数据库保存失败时仍返回回答，并标记 `persisted=false`、锁定当前对话；外部错误、Dify ID 和原始响应不会暴露给前端。

## 工单 API

工单接口、状态、权限和数据可见性见 [`docs/work-order-flow.md`](../docs/work-order-flow.md)。正式表为 `formal_work_orders` 和 `formal_work_order_logs`；旧原型 `work_orders` 保持不变。真实 MySQL 已迁移到 `20260807_05 (head)`；后续新迁移仍须先生成并审查 offline SQL，再取得明确授权执行。

## 候选知识 API

阶段 5 增加 admin-only 的 `GET /api/v1/knowledge-entries`、`PUT /api/v1/knowledge-entries/{id}` 和 `POST /api/v1/knowledge-entries/{id}/sync`。关闭工单、关闭日志和唯一候选在同一事务保存；`synced` 候选永久只读。Dataset client 使用独立 Key，timeout 或网络异常不会自动重试，管理员必须先按 `[KE-{id}]` 在 Dify 控制台核对。

数据结构、三状态、真实 Dataset API 契约和当前验收状态见 [`docs/knowledge-deposition.md`](../docs/knowledge-deposition.md)。revision `20260807_05` 已在真实 MySQL 一次执行并完成结构核验；旧原型 `work_orders` 仍为 10 行。

## 认证规则

- 仅支持用户名登录，不开放注册。
- Access Token 使用 HS256，有效期固定 120 分钟，不提供 Refresh Token。
- 用户被禁用、管理员重置密码或用户主动改密后，已签发 Token 立即且永久失效；重新启用账号不会恢复旧 Token。
- 首次登录或管理员重置密码后，只允许访问健康检查、`/auth/me` 和修改密码接口。
- 普通运维人员不能访问任何 `/users` 管理接口。
