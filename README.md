# 基于大语言模型的智能运维问答与工单辅助系统

本科毕业设计项目，目标是建立“智能问答 → 未解决问题转工单 → 管理员处理 → 解决方案沉淀知识 → Dify 知识库复用”的业务闭环。

当前完成阶段 2：保留 Flask 原型，正式 Vue 3 + FastAPI 系统已具备用户认证、普通运维人员与管理员角色权限、首次强制改密和管理员用户管理。

## 技术栈

- 前端：Vue 3、Vite、TypeScript、Element Plus、Vue Router、Axios
- 后端：FastAPI、SQLAlchemy、Alembic、Pydantic Settings、PyMySQL
- 认证：Argon2 密码哈希、JWT Access Token
- 数据库：MySQL 8
- 测试：Pytest、隔离 SQLite、浏览器流程验证
- AI 与知识库：Dify Cloud API，仍由 Flask 原型验证，尚未迁入正式后端

## 目录

```text
prototype/   已验证的 Flask 原型，冻结保留
backend/     FastAPI 正式后端
frontend/    Vue 3 正式前端
dataset/     后续统一管理知识语料与评测数据
docs/        正式项目文档
deployment/  后续部署说明
```

## 运行顺序

1. 准备项目专用 MySQL 账号 `llm_ops_app`，仅授权访问 `dify_ops`。
2. 配置 `backend/.env`，不要提交真实密码、JWT Secret 或初始管理员密码。
3. 在 `backend/` 执行 `alembic upgrade head`。
4. 临时启用初始管理员引导并启动 FastAPI；创建成功后关闭开关并清空初始密码配置。
5. 启动 Vue 前端并使用管理员账号完成首次改密。

详细命令见 [backend/README.md](backend/README.md) 和 [frontend/README.md](frontend/README.md)。认证与权限矩阵见 [docs/auth-and-rbac.md](docs/auth-and-rbac.md)。

## 当前范围

已实现：Flask 原型隔离、FastAPI/Vue 工程、MySQL 健康检查、用户登录、2 小时 Access Token、首次强制改密、角色权限和管理员用户管理。

尚未实现：正式 Dify 问答、问答历史、工单流转、知识管理、统计看板、Refresh Token、注册和密码找回。

## 安全边界

- 真实 `.env`、密码、API Key 和 Token 不得提交。
- 前端只保存 Access Token，不保存数据库凭证、Dify Key 或密码。
- `prototype/` 使用原有连接配置，正式后端使用 `llm_ops_app`，两者互不修改。
- 初始化管理员成功后必须设置 `INITIAL_ADMIN_ENABLED=false` 并清空 `INITIAL_ADMIN_PASSWORD`。
