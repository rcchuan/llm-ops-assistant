# 环境版本清单

## Windows 阶段 7A 实测

采集日期：2026-08-10。

| 项目 | 版本 |
| --- | --- |
| OS | Microsoft Windows 11 家庭中文版 10.0.22621（Build 22621） |
| Git | 2.55.0.windows.3 |
| Python | 3.12.10 |
| FastAPI / Starlette / Uvicorn | 0.141.1 / 1.3.1 / 0.52.0 |
| SQLAlchemy / Alembic / PyMySQL | 2.0.51 / 1.18.5 / 1.2.0 |
| Pytest / httpx / pydantic-settings | 9.1.1 / 0.28.1 / 2.14.2 |
| Node.js / npm | 24.15.0 / 11.12.1 |
| Vue / Vue Router / Vite | 3.5.40 / 4.6.4 / 7.3.6 |
| Element Plus / Axios | 2.14.3 / 1.19.0 |
| TypeScript / vue-tsc | 5.9.3 / 3.3.9 |
| MySQL Server | 8.0.46（只读 `SELECT VERSION()`） |
| 浏览器 | Google Chrome 148.0.7778.168 |

## CentOS Stream 9 阶段 7B 实测

采集日期：2026-08-12。已完成部署目录、依赖、测试构建、MySQL 逻辑备份、Systemd 安装启动、Windows 外部访问和整机重启自恢复验证。

| 项目 | 版本 |
| --- | --- |
| OS | CentOS Stream release 9 |
| Kernel | 5.14.0-511.el9.x86_64 |
| Git | 2.43.5 |
| Python（venv） | 3.11.13（系统默认 3.9 改用 python3.11 满足依赖） |
| FastAPI / Starlette / Uvicorn | 0.141.1 / 1.6.0 / 0.52.1 |
| SQLAlchemy / Alembic / PyMySQL | 2.0.52 / 1.19.1 / 1.2.0 |
| Pytest / httpx / pydantic-settings | 9.1.1 / 0.28.1 / 2.15.0 |
| Node.js / npm | 22.23.1 / 10.9.8（AppStream nodejs:22 模块） |
| MySQL Server / client | 8.0.46 |
| 部署目录 | `/root/Dify_agent`（Monorepo，精确 commit `cb7c346`） |
| 数据库账号 | `llm_ops_app`（非 root），数据库 `dify_ops` |
| Alembic revision | `20260807_05 (head)` |
| 服务状态 | `llm-ops-assistant.service` active/enabled；整机重启后自动恢复，监听 `0.0.0.0:8000` |
| 部署基线 / 最终 commit/tag | `cb7c346` / 待 Git 收尾授权 |
