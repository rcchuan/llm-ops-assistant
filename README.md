# 基于大语言模型的智能运维问答与工单辅助系统

本科毕业设计项目，目标是建立“智能问答 → 未解决问题转工单 → 管理员处理 → 解决方案沉淀知识 → Dify 知识库复用”的业务闭环。

阶段 1～6 已完成工程化、认证权限、智能问答、工单闭环、知识沉淀、统计看板与健康检查。阶段 7 正在实施 Windows 生产构建与部署准备；智能问答仍是核心，工单只承接 AI 未解决问题，已确认的解决方案经管理员复核后首次同步到 Dify Dataset。

## 技术栈

- 前端：Vue 3、Vite、TypeScript、Element Plus、Vue Router、Axios
- 后端：FastAPI、SQLAlchemy、Alembic、Pydantic Settings、PyMySQL
- 认证：Argon2 密码哈希、JWT Access Token
- 数据库：MySQL 8
- 测试：Pytest、隔离 SQLite、浏览器流程验证
- AI 与知识库：Dify Cloud Chatflow API，由 FastAPI Integration 适配，前端不接触 Dify 凭证

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

## 使用与验收入口

- [后端本地开发](backend/README.md) / [前端本地开发](frontend/README.md)
- [CentOS Stream 9 部署](deployment/README.md)
- [测试与演示记录](docs/testing-and-demo.md)
- [阶段 7 手动演示脚本](docs/stage-7-demo-script.md)
- [阶段 7 截图索引](docs/screenshots/stage-7/README.md)
- [环境版本清单](docs/environment-versions.md)

认证与权限矩阵见 [docs/auth-and-rbac.md](docs/auth-and-rbac.md)，智能问答契约见 [docs/intelligent-chat.md](docs/intelligent-chat.md)，工单状态和权限见 [docs/work-order-flow.md](docs/work-order-flow.md)，候选知识与 Dify Dataset 契约见 [docs/knowledge-deposition.md](docs/knowledge-deposition.md)。

## 当前范围

已实现：Flask 原型隔离、FastAPI/Vue 工程、认证与用户管理、Dify blocking 问答、问答历史、本地反馈、工单闭环、候选知识、统计看板和健康检查。阶段 7A 增加同源生产构建、FastAPI 条件静态托管和部署文档。

尚未完成：CentOS Stream 9 真实部署验收（阶段 7B）。多会话管理、流式输出、Refresh Token、注册、密码找回和通用知识库管理不在当前范围。

## 安全边界

- 真实 `.env`、密码、API Key 和 Token 不得提交。
- 前端只保存 Access Token，不保存数据库凭证、Dify Key 或密码。
- `prototype/` 使用原有连接配置，正式后端使用 `llm_ops_app`，两者互不修改。
- 旧原型 `work_orders` 原样保留；阶段 4 正式系统使用 `formal_work_orders` 和 `formal_work_order_logs`。
- 初始化管理员成功后必须设置 `INITIAL_ADMIN_ENABLED=false` 并清空 `INITIAL_ADMIN_PASSWORD`。
