# 基于大语言模型的智能运维问答与工单辅助系统

本科毕业设计项目，目标是建立“智能问答 → 未解决问题转工单 → 管理员处理 → 解决方案沉淀知识 → Dify 知识库复用”的业务闭环。

当前处于阶段 1：保留已验证的 Flask 原型，建立 Vue 3 + FastAPI 正式工程骨架，并验证前端、后端与 MySQL 的基础联通。

## 技术栈

- 前端：Vue 3、Vite、TypeScript、Element Plus、Vue Router、Axios
- 后端：FastAPI、SQLAlchemy、Pydantic Settings、PyMySQL、HTTPX
- 数据库：MySQL 8
- 测试：Pytest
- AI 与知识库：Dify Cloud API，暂由 Flask 原型验证，尚未迁入正式后端

## 目录

```text
prototype/   已验证的 Flask 原型，冻结保留
backend/     FastAPI 正式后端
frontend/    Vue 3 正式前端
dataset/     后续统一管理知识语料与评测数据
docs/        正式项目文档入口
deployment/  后续部署说明
```

## 环境要求

- Python 3.10+
- Node.js 20+
- npm 10+
- MySQL 8

## Flask 原型

```powershell
cd prototype
Copy-Item .env.example .env
python -m pip install -r requirements.txt
python app.py
```

页面：`http://127.0.0.1:5000/`

详见 [prototype/README.md](prototype/README.md)。

## FastAPI 后端

```powershell
cd backend
python -m venv .venv
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

健康检查：`http://127.0.0.1:8000/api/v1/health`

详见 [backend/README.md](backend/README.md)。

## Vue 前端

```powershell
cd frontend
Copy-Item .env.example .env.local
npm install
npm run dev
npm run build
```

页面：`http://127.0.0.1:5173/`

详见 [frontend/README.md](frontend/README.md)。

## 配置与安全

各子项目独立维护配置模板：

- `prototype/.env.example`
- `backend/.env.example`
- `frontend/.env.example`

真实 `.env`、密码、API Key 和 Token 不得提交。前端不得保存数据库凭证或 Dify Key。

## 当前范围

已完成：Flask 原型隔离、正式工程目录、后端健康检查、MySQL 连通性检查、前端健康状态页和基础测试。

尚未实现：用户认证、角色权限、正式 Dify 问答、工单流转、知识同步、数据看板和正式部署。
