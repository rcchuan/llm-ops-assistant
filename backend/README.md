# FastAPI 后端

阶段 2 后端提供 MySQL 健康检查、JWT 登录、当前用户识别、修改密码、角色权限、初始管理员引导和管理员用户管理。

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
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX, DROP
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

## 认证规则

- 仅支持用户名登录，不开放注册。
- Access Token 使用 HS256，有效期固定 120 分钟，不提供 Refresh Token。
- 用户被禁用、管理员重置密码或用户主动改密后，已签发 Token 立即且永久失效；重新启用账号不会恢复旧 Token。
- 首次登录或管理员重置密码后，只允许访问健康检查、`/auth/me` 和修改密码接口。
- 普通运维人员不能访问任何 `/users` 管理接口。
