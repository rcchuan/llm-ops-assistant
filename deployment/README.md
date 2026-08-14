# CentOS Stream 9 部署

本文覆盖新虚拟机部署和现有 `/root/Dify_agent` 升级。阶段 7B 已完成精确代码部署、依赖安装、测试构建、MySQL 逻辑备份、Systemd 常驻服务、Windows 外部访问和整机重启自恢复验证（部署基线 `cb7c346`）。完整实操、命令、原因和真实结果见 [阶段 7B 部署操作记录](stage-7b-deployment-record.md)。

## 部署边界

- 单机运行 FastAPI/Uvicorn，由其托管已构建的 Vue `dist`。
- MySQL 使用既定实例，Dify 使用既定 Cloud 服务。
- 不包含 Nginx、Docker、域名、HTTPS、SELinux 或 `firewalld` 配置。
- 执行迁移、恢复或服务切换前，必须另行确认备份、目标分支和真实配置。

## 新虚拟机部署

先记录系统和工具版本，再安装 Git、Python、Node/npm 与 MySQL client。本机（阶段 7B 确认点 A）实测输出：

```text
CentOS Stream release 9
git version 2.43.5
Python 3.11.13        （系统默认 python3.9 改用 python3.11 满足 pwdlib/fastapi 依赖）
v22.23.1              （AppStream nodejs:22 模块）
10.9.8
mysql  Ver 8.0.46
```

通过 GitHub 获取代码是主路径：

```bash
git clone <仓库 GitHub URL> /root/Dify_agent
cd /root/Dify_agent
git status --short --branch
git rev-parse HEAD
```

若目标机不能访问 GitHub，只能从 Windows 干净工作区生成归档并人工传输。归档前必须确认 `git status --short` 无输出；归档不包含被 Git 忽略的 `.env`、`node_modules`、`.venv` 或 `dist`：

```powershell
git archive --format=zip --output llm-ops-assistant.zip HEAD
```

## 现有目录升级

先确认现有目录无未提交改动并完成数据库备份，再使用 fast-forward 更新：

```bash
cd /root/Dify_agent
git status --short --branch
git fetch origin
git switch <部署分支>
git pull --ff-only origin <部署分支>
git rev-parse HEAD
```

工作区不干净、分支不符或拉取不能 fast-forward 时停止，不覆盖服务器文件。

## Python、Node 与配置

```bash
cd /root/Dify_agent/backend
# CentOS Stream 9 默认 python3 为 3.9，不满足 pwdlib/fastapi 依赖，须使用 python3.11
python3.11 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
chmod 600 .env

cd /root/Dify_agent/frontend
npm ci
npm test
npm run build
test -f dist/index.html
```

真实密码、JWT Secret、Dify API Key 和 Dataset ID 只写入 `/root/Dify_agent/backend/.env`，不得进入 Git、终端截图或部署文档。前端生产配置只包含公开的 `VITE_API_BASE_URL=/api/v1`。

## MySQL 与 Alembic

先核对 MySQL Host、端口、数据库名及 `llm_ops_app` 的来源 Host/授权，再执行迁移：

```bash
cd /root/Dify_agent/backend
./.venv/bin/python -m alembic current
./.venv/bin/python -m alembic check
./.venv/bin/python -m alembic upgrade head
./.venv/bin/python -m alembic current
```

`upgrade head` 属于真实数据库写操作，7B 执行前必须核对目标数据库与备份；禁止在共享库执行 `downgrade` 或清库。

备份与恢复命令模板如下，文件名应包含实际时间：

```bash
mysqldump -h <MYSQL_HOST> -u <MYSQL_USER> -p --single-transaction --routines --triggers dify_ops > dify_ops-YYYYMMDD-HHMMSS.sql
mysql -h <MYSQL_HOST> -u <MYSQL_USER> -p dify_ops < dify_ops-YYYYMMDD-HHMMSS.sql
```

恢复会写入数据库，只能在明确指定的恢复窗口和目标库执行；阶段 7A/7B 验收不做完整恢复演练。

阶段 7B 确认点 A 已生成一次仓库外逻辑备份（`llm_ops_app` 账号）：

```text
/root/db-backups/dify_ops-20260812_213952.sql
12 张表全部包含（含 6 张业务表数据），大小 81,664 字节
SHA-256: f955467deeabdc25f8a105a24ce2b1954e5efef00c2a4b0bbe447dac2affd162
说明：llm_ops_app 无 PROCESS 权限，mysqldump 对 tablespace 元数据输出提示，但不影响表结构与数据导出。
```

## Systemd

仓库模板为 `deployment/llm-ops-assistant.service`。确认路径和配置后手工安装：

```bash
cp /root/Dify_agent/deployment/llm-ops-assistant.service /etc/systemd/system/llm-ops-assistant.service
systemctl daemon-reload
systemctl enable --now llm-ops-assistant.service
systemctl status llm-ops-assistant.service --no-pager
journalctl -u llm-ops-assistant.service -n 100 --no-pager
```

unit 以 `root` 运行单个 Uvicorn worker，启动前检查后端 `.env` 和前端 `dist/index.html`，失败时自动重启；不使用 `--reload`。

## 验证与回退

```bash
curl -i http://127.0.0.1:8000/api/v1/health
curl -I http://127.0.0.1:8000/
```

浏览器验收地址为 `http://192.168.100.42:8000`。

阶段 7B 确认点 A 临时 Uvicorn（`127.0.0.1:8000`）实测：

- `/api/v1/health` → `200 application/json`，`database.status=up`，`dify_app/dify_dataset=configured`
- `/` 与 `/chat`（深层路由）→ `200 text/html`
- 未知 `/api/v1/*` 与缺失 `/assets/*` → `404 application/json`，不回退

Systemd 安装启动、Windows 外部访问、后台日志和整机重启自恢复均已实测通过；最终 commit/tag 仍待 Git 收尾授权。

阶段 7 不提供专项回滚流程；v1.0.0 发布后作为后续版本升级与容器化的稳定基线。
