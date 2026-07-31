# Flask 原型

这是本项目早期的功能验证原型，用于验证 Dify Cloud、MySQL、语料处理和简单 Web 问答链路。正式系统在仓库根目录的 `backend/` 与 `frontend/` 中继续开发。

## 环境要求

- Python 3.10+
- MySQL 8
- 可访问的 Dify Cloud 应用与知识库

## 配置

在 `prototype/` 目录复制配置模板：

```powershell
Copy-Item .env.example .env
```

填写 MySQL 和 Dify 配置。真实密码、API Key 和 Token 只能保存在 `.env`，不得提交 Git。

主要配置项：

- MySQL：`MYSQL_HOST`、`MYSQL_PORT`、`MYSQL_USER`、`MYSQL_PASSWORD`、`MYSQL_DATABASE`
- Dify：`DIFY_BASE_URL`、`DIFY_APP_API_KEY`、`DIFY_DATASET_API_KEY`、`DIFY_DATASET_ID`
- Flask：`FLASK_HOST`、`FLASK_PORT`

## 安装与启动

Windows PowerShell：

```powershell
cd prototype
python -m pip install -r requirements.txt
python app.py
```

Linux：

```bash
cd prototype
python3 -m pip install -r requirements.txt
python3 app.py
```

默认页面：`http://127.0.0.1:5000/`

健康检查：`http://127.0.0.1:5000/api/health`

## 已实现能力

- 调用 Dify Chat API 完成单轮运维问答
- 将问答日志写入 MySQL
- 清洗示例语料并生成导入数据
- 上传 Markdown 或清洗语料到 Dify 知识库
- 基于规则进行工单分类、去重和高频问题汇总
- 提供 Flask 单页自测界面

原型仅作为已验证链路和迁移参考，不继续扩展登录、权限、工单流转等正式业务。
