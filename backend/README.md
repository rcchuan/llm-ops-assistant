# FastAPI 后端

阶段 1 后端只提供配置加载、MySQL 连接框架和健康检查，不包含正式业务接口。

## 本地配置

```powershell
cd backend
Copy-Item .env.example .env
```

在 `.env` 中填写现有 MySQL 的用户名、密码和数据库名。真实配置不得提交。

## Windows 开发

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Linux 开发

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -v
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

健康检查：`GET http://127.0.0.1:8000/api/v1/health`

- MySQL 可用：HTTP 200，应用状态为 `ok`，数据库状态为 `up`
- MySQL 不可用：HTTP 503，应用状态为 `degraded`，数据库状态为 `down`

错误响应不会包含数据库密码、完整连接串或内部堆栈。
