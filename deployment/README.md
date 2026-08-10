# CentOS Stream 9 部署

本文覆盖新虚拟机部署和现有 `/root/Dify_agent` 升级。阶段 7A 仅准备命令框架和 Systemd unit，所有 CentOS 版本、命令输出与服务状态均待 7B 实测填写。

## 部署边界

- 单机运行 FastAPI/Uvicorn，由其托管已构建的 Vue `dist`。
- MySQL 使用既定实例，Dify 使用既定 Cloud 服务。
- 不包含 Nginx、Docker、域名、HTTPS、SELinux 或 `firewalld` 配置。
- 执行迁移、恢复或服务切换前，必须另行确认备份、目标分支和真实配置。

## 新虚拟机部署

先记录系统和工具版本，再安装 Git、Python、Node/npm 与 MySQL client。以下输出待 7B 实测填写：

```bash
cat /etc/os-release
git --version
python3 --version
node --version
npm --version
mysql --version
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
python3 -m venv .venv
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

浏览器验收地址为 `http://192.168.100.42:8000`。CentOS 版本、安装命令输出、服务状态、页面结果及最终 commit/tag：**待 7B 实测填写**。

阶段 7 不提供专项回滚流程；v1.0.0 发布后作为后续版本升级与容器化的稳定基线。
