# 阶段 7B CentOS Stream 9 部署操作记录

> 本文记录“智能运维问答与工单辅助系统”阶段 7B 在 `192.168.100.42` 上的实际部署过程、执行命令、执行原因、真实结果和安全边界。
> 执行日期：2026-08-12
> 目标版本：`feature/stage-7-deployment@cb7c346690169eda0aa6a4e1cf1e65c9d4d43779`
> 正式目录：`/root/Dify_agent`
> 正式服务：`llm-ops-assistant.service`
> 正式地址：`http://192.168.100.42:8000`

## 1. 部署原则与安全边界

本次部署遵循以下原则：

1. 先创建虚拟机快照，再执行远端写操作。
2. 旧 Flask 原型不删除，先改名保留。
3. 旧 `.env` 在仓库外独立备份，真实凭证不写入 Git 或本文。
4. 只部署精确 commit，不使用不明确的分支最新状态。
5. 正式后端使用 `llm_ops_app`，不沿用 MySQL root 账号。
6. 数据库已经位于 Alembic head，不执行无必要的 migration。
7. 先用临时 Uvicorn 验证，再安装 Systemd。
8. Systemd、数据库逻辑备份和整机重启分别确认后执行。
9. 不引入 Nginx、Docker、HTTPS、域名、SELinux 或 `firewalld` 配置。
10. 不新增业务功能，不修改 Dify Chatflow/Dataset，不同步第二条知识。

所有示例中的密码、JWT Secret 和 Dify Key 均使用占位符，禁止把真实值复制到文档或终端截图中。

## 2. 部署前基线核验

### 2.1 本地代码核验

```bash
cd /d/projectcode/llm-ops-assistant
git status --short --branch
git rev-parse HEAD
git rev-parse '@{upstream}'
```

**原因：**确认本地代码已经通过阶段 7A 验收，工作区干净，且本地与远端 feature 分支指向同一提交，避免部署未验收代码。

**实测结果：**

```text
branch: feature/stage-7-deployment
HEAD: cb7c346690169eda0aa6a4e1cf1e65c9d4d43779
upstream: origin/feature/stage-7-deployment
工作区：干净
```

### 2.2 远端只读盘点

```bash
ssh root@192.168.100.42
cat /etc/redhat-release
uname -r
cd /root/Dify_agent
git branch --show-current
git rev-parse HEAD
git status --short --branch
systemctl is-active mysqld
systemctl is-enabled mysqld
systemctl is-active llm-ops-assistant.service
ss -tlnp | grep -E ':(22|3306|33060|8000|5000|5173)\b'
ps aux | grep -E '(flask|uvicorn|vite|node|gunicorn)' | grep -v grep
stat -c '%a %U:%G %s' /root/Dify_agent/.env
```

**原因：**在任何写操作前确认操作系统、旧代码、进程、端口、数据库和 `.env` 状态没有变化。

**实测结果：**

- CentOS Stream 9，Kernel `5.14.0-511.el9.x86_64`。
- 旧目录为 Flask 原型：`main@bf68ec9419e9abeb076120b80c6597fa561a90dd`。
- MySQL active/enabled；应用未运行；8000 未监听。
- 旧 `.env` 权限为 `600 root:root`。
- 正式数据库 Alembic revision 已为 `20260807_05`。

## 3. 旧环境保护

### 3.1 仓库外备份旧 `.env`

```bash
mkdir -p /root/env-backups
TS=$(date +%Y%m%d_%H%M%S)
cp -p /root/Dify_agent/.env /root/env-backups/Dify_agent.env.${TS}.bak
chmod 600 /root/env-backups/Dify_agent.env.${TS}.bak
stat -c '%a %U:%G %s' /root/env-backups/Dify_agent.env.${TS}.bak
sha256sum /root/env-backups/Dify_agent.env.${TS}.bak
```

**原因：**旧 `.env` 包含 MySQL 和 Dify 配置，不能直接覆盖或提交到 Git；仓库外备份便于对照和应急恢复。

**实测结果：**

```text
路径：/root/env-backups/Dify_agent.env.20260812_202940.bak
权限：600 root:root
大小：384 字节
SHA-256：2367185201a1ede6306f8f2128a295bb73712ce72fceaac6230c7ba4c401d69f
```

检查配置时仅检查键名和空/非空状态，不执行 `cat .env` 或其他会回显真实值的命令。

### 3.2 保留旧 Flask 原型目录

```bash
mv /root/Dify_agent /root/Dify_agent.prototype-backup-proto-20260812-2042
```

**原因：**不在旧目录上盲目覆盖；保留旧原型作为独立历史现场，同时把标准正式路径留给 Monorepo。

**实测结果：**旧目录保留于：

```text
/root/Dify_agent.prototype-backup-proto-20260812-2042
```

## 4. 获取精确代码版本

```bash
cd /root
git clone --no-checkout https://github.com/rcchuan/llm-ops-assistant.git /root/Dify_agent
cd /root/Dify_agent
git fetch origin cb7c346690169eda0aa6a4e1cf1e65c9d4d43779
git checkout --detach cb7c346690169eda0aa6a4e1cf1e65c9d4d43779
git rev-parse HEAD
git status --short --branch
```

**原因：**部署精确 SHA，避免 feature 分支在部署期间变化导致代码不可复现。使用 detached HEAD（分离头指针）表示服务器固定运行该版本，不在服务器上开发。

**实测结果：**

```text
HEAD = cb7c346690169eda0aa6a4e1cf1e65c9d4d43779
初始工作区干净
Monorepo 包含 backend/、frontend/、deployment/、docs/、prototype/
```

### 4.1 核验旧原型仍被保留

```bash
diff -q /root/Dify_agent/prototype/app.py \
  /root/Dify_agent.prototype-backup-proto-20260812-2042/app.py
diff -q /root/Dify_agent/prototype/config.py \
  /root/Dify_agent.prototype-backup-proto-20260812-2042/config.py
diff -q /root/Dify_agent/prototype/dify_api.py \
  /root/Dify_agent.prototype-backup-proto-20260812-2042/dify_api.py
```

同时检查：

```bash
test ! -e /root/Dify_agent/.env
test ! -e /root/Dify_agent/app.log
find /root/Dify_agent -name __pycache__ -print
```

**原因：**确认 `prototype/` 保留旧 Flask 核心代码，同时没有把旧 `.env`、日志、缓存或旧 `.git` 混入新仓库。

**实测结果：**三个核心文件内容一致；未复制 `.env`、日志或缓存。

## 5. 组装正式 backend/.env

配置来源：

- 通用应用配置、JWT 和 Dify 配置：Windows 已验证的 `backend/.env`。
- MySQL 账号：强制使用 `llm_ops_app`。
- 数据库：`dify_ops`。
- 初始管理员引导：关闭。

安全组装逻辑示例：

```bash
# Windows 主机执行；传输文件只作为临时中转
scp D:/projectcode/llm-ops-assistant/backend/.env \
  root@192.168.100.42:/root/env-backups/windows-backend.env.transfer

# CentOS 执行
SRC=/root/env-backups/windows-backend.env.transfer
DST=/root/Dify_agent/backend/.env
sed -E 's/^MYSQL_USER=.*/MYSQL_USER=llm_ops_app/' "$SRC" > "$DST"
# 根据已确认密码安全更新 MYSQL_PASSWORD；禁止把真实值写入文档
chmod 600 "$DST"
chown root:root "$DST"
rm -f "$SRC"
```

安全核验：

```bash
stat -c '%a %U:%G' /root/Dify_agent/backend/.env
for key in APP_NAME MYSQL_HOST MYSQL_PORT MYSQL_USER MYSQL_PASSWORD MYSQL_DATABASE \
  JWT_SECRET_KEY DIFY_BASE_URL DIFY_APP_API_KEY DIFY_DATASET_API_KEY DIFY_DATASET_ID; do
  grep -q "^${key}=" /root/Dify_agent/backend/.env && echo "${key}=present"
done
```

**原因：**正式应用必须使用最小权限账号；真实凭证只进入权限为 600 的 `.env`，不进入代码仓库或部署文档。

**实测结果：**

- `MYSQL_USER=llm_ops_app`。
- `MYSQL_DATABASE=dify_ops`。
- `INITIAL_ADMIN_ENABLED=false`。
- `INITIAL_ADMIN_PASSWORD` 为空。
- `.env` 权限 `600 root:root`。
- 临时传输文件已删除。

> 密码包含 `@` 等 URL 特殊字符时，不能手工拼接 SQLAlchemy URL。项目 `app/core/config.py` 已使用 `sqlalchemy.engine.URL.create()`，可正确转义特殊字符。

## 6. 安装 Python 运行环境

CentOS Stream 9 默认 Python 3.9，不能满足 `pwdlib>=0.3` 等依赖，因此安装 AppStream 的 Python 3.11：

```bash
dnf install -y python3.11 python3.11-pip
cd /root/Dify_agent/backend
rm -rf .venv
/usr/bin/python3.11 -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
```

**原因：**保留系统 Python 3.9，不替换系统解释器；项目 venv 显式使用 Python 3.11，满足现代依赖且不影响系统工具。

**实测版本：**

```text
Python 3.11.13
pip 26.2.1
FastAPI 0.141.1
Uvicorn 0.52.1
SQLAlchemy 2.0.52
Alembic 1.19.1
PyMySQL 1.2.0
Pytest 9.1.1
```

## 7. 安装 Node.js 与 npm

先只读查询可用模块：

```bash
dnf module list nodejs
dnf module info nodejs:22
```

安装 Node.js 22 LTS：

```bash
dnf module enable -y nodejs:22
dnf install -y nodejs
```

该 CentOS 包已安装 npm 内容，但没有创建可执行入口；使用正确的 JS CLI 入口：

```bash
ln -s /usr/lib/node_modules/npm/bin/npm-cli.js /usr/bin/npm
node --version
npm --version
```

**原因：**Vite 7 需要受支持的新版本 Node.js；选择系统 AppStream 的 Node.js 22，避免引入 nvm 或多套运行时。不能链接 npm 的 Bash wrapper，因为其相对路径解析会失败，应链接 `npm-cli.js`。

**实测结果：**

```text
Node.js v22.23.1
npm 10.9.8
```

## 8. 安装前端依赖并构建

```bash
cd /root/Dify_agent/frontend
npm ci
npm test
npm run build
test -f dist/index.html
```

**原因：**`npm ci` 严格依据 lockfile 安装，保证可重复；先运行测试，再生成由 FastAPI 托管的生产 `dist`。

**实测结果：**

```text
前端测试：19 passed, 0 failed
Vite 构建：1700 modules transformed
构建产物：frontend/dist/index.html 存在
```

构建存在大 chunk warning，但不影响本阶段功能和部署，不在阶段 7 扩大范围做性能拆包。

## 9. 后端测试与数据库只读核验

```bash
cd /root/Dify_agent/backend
./.venv/bin/python -m pytest -q
./.venv/bin/python -m pytest tests/test_static_frontend.py -q
./.venv/bin/python -m alembic current
./.venv/bin/python -m alembic check
```

**原因：**在正式服务启动前验证全部后端行为、静态托管边界和数据库 revision；本步骤只读，不执行 migration。

**实测结果：**

```text
后端全量：154 passed, 1 warning
静态托管专项：4 passed, 1 warning
Alembic current：20260807_05 (head)
```

### 9.1 Alembic check 误报说明

`alembic check` 在 MySQL 8 上报告 6 个 `remove_constraint`：

- `user_role`
- `qa_record_feedback`
- `work_order_status`
- `work_order_log_from_status`
- `work_order_log_to_status`
- `knowledge_entry_status`

只读查询确认这些 CHECK 约束真实存在，且模型与 migration 都声明了 `native_enum=False, create_constraint=True`。误报来自 model 的 `SqlEnum(..., length=8)` 与 migration 元数据细节差异，不代表存在待执行 migration。

**处理原则：**数据库已为 `(head)`，因此不执行 `upgrade`、`downgrade` 或删除约束；只把差异记录为既有 Alembic/MySQL 反射误报。

## 10. 临时 Uvicorn 验证

```bash
cd /root/Dify_agent/backend
./.venv/bin/python -m uvicorn app.main:app \
  --host 127.0.0.1 --port 8000
```

另一终端验证：

```bash
curl -i http://127.0.0.1:8000/api/v1/health
curl -I http://127.0.0.1:8000/
curl -I http://127.0.0.1:8000/chat
curl -i http://127.0.0.1:8000/api/v1/does-not-exist
curl -i http://127.0.0.1:8000/assets/nonexistent.js
```

验证完成后停止临时进程，并确认端口释放：

```bash
pkill -f 'uvicorn app.main:app'
ss -tlnp | grep ':8000' || echo '8000 closed'
```

**原因：**先验证代码、配置、MySQL、Dify 配置和生产 `dist` 可以协同工作，再改 Systemd，避免服务管理问题掩盖应用问题。

**实测结果：**

- health → `200 application/json`，数据库 `up`，Dify App/Dataset `configured`。
- `/`、`/chat` → `200 text/html`。
- 未知 API 和缺失 asset → `404 application/json`，没有错误 SPA 回退。
- 临时进程已停止，8000 一度确认无监听。

## 11. MySQL 逻辑备份

```bash
mkdir -p /root/db-backups
cd /root/Dify_agent/backend
# 从 .env 安全读取连接参数，不把值写入日志
MYSQL_PWD='<MYSQL_PASSWORD>' mysqldump \
  -h 192.168.100.42 -P 3306 -u llm_ops_app \
  --single-transaction --routines --triggers --databases dify_ops \
  > /root/db-backups/dify_ops-20260812_213952.sql
```

完整性核验：

```bash
F=/root/db-backups/dify_ops-20260812_213952.sql
grep -c 'CREATE TABLE' "$F"
for t in users conversations qa_records formal_work_orders \
  formal_work_order_logs knowledge_entries; do
  grep -c "INSERT INTO \`$t\`" "$F"
done
sha256sum "$F"
```

**原因：**虚拟机快照不等于 MySQL 逻辑一致性备份；在正式服务切换和重启前增加一个可读、可校验的数据库保护点。

**实测结果：**

```text
文件：/root/db-backups/dify_ops-20260812_213952.sql
大小：81,664 字节
表数：12
六张正式业务表均包含 INSERT 数据块
SHA-256：f955467deeabdc25f8a105a24ce2b1954e5efef00c2a4b0bbe447dac2affd162
```

`llm_ops_app` 没有 `PROCESS` 权限，因此 mysqldump 对 tablespace 元数据给出提示；表结构和数据均已完整导出。为保持最小权限，不额外授予 `PROCESS`。

## 12. 安装并启动 Systemd 服务

先检查模板与目标位置：

```bash
cat /root/Dify_agent/deployment/llm-ops-assistant.service
test ! -e /etc/systemd/system/llm-ops-assistant.service
```

安装并启动：

```bash
cp /root/Dify_agent/deployment/llm-ops-assistant.service \
  /etc/systemd/system/llm-ops-assistant.service
chmod 644 /etc/systemd/system/llm-ops-assistant.service
systemctl daemon-reload
systemctl enable llm-ops-assistant.service
systemctl start llm-ops-assistant.service
systemctl status llm-ops-assistant.service --no-pager
```

**原因：**Systemd 提供后台常驻、统一日志、故障自动重启和开机自启；单 worker 与毕设演示规模一致，不引入额外部署组件。

unit 的关键行为：

```text
WorkingDirectory=/root/Dify_agent/backend
启动前检查 backend/.env 和 frontend/dist/index.html
ExecStart=... uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=on-failure
WantedBy=multi-user.target
```

**实测结果：**

```text
Loaded: loaded
Active: active (running)
Enabled: enabled
ExecStartPre 两项检查均 SUCCESS
首次 Main PID: 35322
内存约 54.2 MiB
```

## 13. 正式服务与外部访问验证

CentOS 本机验证：

```bash
ss -tlnp | grep ':8000'
curl -i http://127.0.0.1:8000/api/v1/health
curl -I http://127.0.0.1:8000/
curl -I http://127.0.0.1:8000/chat
systemctl is-enabled llm-ops-assistant.service
journalctl -u llm-ops-assistant.service -n 20 --no-pager
```

Windows 外部验证：

```bash
curl.exe -sS --max-time 15 -o NUL -w "%{http_code}" \
  http://192.168.100.42:8000/api/v1/health
curl.exe -sS --max-time 15 -o NUL -w "%{http_code}" \
  http://192.168.100.42:8000/
curl.exe -sS --max-time 15 -o NUL -w "%{http_code}" \
  http://192.168.100.42:8000/chat
```

**原因：**本机 200 只证明应用启动，Windows 访问 200 才能证明正式监听地址和网络路径满足答辩演示要求。

**实测结果：**

- `0.0.0.0:8000` 正常监听。
- health、`/`、`/chat` 在 CentOS 本机与 Windows 外部均返回 200。
- 日志可见 Windows 来源 `192.168.100.1` 的三次 200 请求。
- recent journal 无 error、exception 或 traceback。

> Git Bash 自带 curl 对 Windows `NUL` 的处理可能返回 `curl: (23)`，但 HTTP 已为 200。使用 `curl.exe -o NUL` 复核后，HTTP 200 且 `curl_rc=0`。

## 14. 整机重启与自恢复验证

在已获得单独确认后执行：

```bash
sync
reboot
```

系统恢复后重新连接：

```bash
uptime
systemctl is-active llm-ops-assistant.service
systemctl is-enabled llm-ops-assistant.service
systemctl is-active mysqld
ss -tlnp | grep ':8000'
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/api/v1/health
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/chat
```

Windows 再次执行外部 HTTP 验证。

**原因：**只有整机重启后服务自动恢复，才能证明 `enable`、启动依赖和正式部署路径真实有效，而不只是当前 shell 中临时可用。

**实测结果：**

```text
重启后 uptime：1 分钟
llm-ops-assistant.service：active + enabled
mysqld：active
8000：0.0.0.0 正常监听
重启后 Main PID：776
CentOS 本机 health、/、/chat：全部 200
Windows 外部 health、/、/chat：全部 200，curl_rc=0
```

## 15. 最终状态与维护命令

### 15.1 当前状态

```text
正式地址：http://192.168.100.42:8000
代码版本：cb7c346690169eda0aa6a4e1cf1e65c9d4d43779
服务：llm-ops-assistant.service active/enabled
数据库：MySQL active，Alembic 20260807_05 (head)
运行方式：FastAPI/Uvicorn 单 worker，同时托管 Vue dist
```

### 15.2 常用运维命令

查看状态：

```bash
systemctl status llm-ops-assistant.service --no-pager
```

查看最近日志：

```bash
journalctl -u llm-ops-assistant.service -n 100 --no-pager
```

持续查看日志：

```bash
journalctl -u llm-ops-assistant.service -f
```

仅在确认配置或代码已更新后重启服务：

```bash
systemctl restart llm-ops-assistant.service
systemctl status llm-ops-assistant.service --no-pager
```

验证健康状态：

```bash
curl -i http://127.0.0.1:8000/api/v1/health
```

### 15.3 当前保留的保护点

```text
VM 快照：部署前已创建
旧原型：/root/Dify_agent.prototype-backup-proto-20260812-2042
旧配置：/root/env-backups/Dify_agent.env.20260812_202940.bak
数据库：/root/db-backups/dify_ops-20260812_213952.sql
```

阶段 7 不提供专项自动回滚脚本。`v1.0.0` 发布后作为后续升级与容器化的稳定版本基线；涉及数据库恢复必须另设恢复窗口并单独确认。

## 16. 本次未做与后续事项

本次明确未做：

- 未引入 Nginx、Docker、HTTPS 或域名。
- 未修改 SELinux 或 `firewalld`。
- 未修改 MySQL 用户、Host、密码或授权。
- 未执行 Alembic upgrade/downgrade 或删除 CHECK 约束。
- 未清理或修改历史业务数据。
- 未新增或同步第二条 Dify Dataset 文档。
- 未在服务器执行 Git commit、push、merge 或 tag。

后续事项：

1. 在本地 feature 分支接收并审查本次三份既有文档和本操作记录。
2. 经授权提交、推送后，再按既定 Git 流程合并 develop/main 并创建 `v1.0.0`。
3. 按演示脚本完成最终浏览器演示与 CentOS 截图索引更新。
