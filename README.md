# 基于 Dify 的移动运维工单智能答疑机器人

> 对标湖南移动运维 AI 业务：一线答疑、工单辅助、语料治理、功能自测

## 项目背景

传统通信运维一线工单重复咨询量大、口径不统一；本项目基于 **Dify 云端智能体** + **Python 自动化** + **MySQL**，实现：

- AI 一线运维答疑（可溯源引用）
- 工单自动分类 / 去重 / 高频问题汇总
- 语料批量清洗并 API 上传 Dify 知识库
- 简易 Web 自测页

## 技术栈

| 组件 | 说明 |
|------|------|
| Python 3 | 主语言 |
| MySQL 8 | 工单、问答日志、语料表 |
| Dify OpenAPI | 云端 `https://api.dify.ai/v1` |
| Flask + HTML/JS | 自测前端 |

## 目录结构

```
Dify_agent/
├── .env                    # 密钥配置（勿提交 Git）
├── config.py               # 统一加载配置
├── db_utils.py             # MySQL 工具
├── dify_api.py             # 模块1：Dify 答疑 API + 日志入库
├── work_order_sql.py       # 模块2：工单预处理
├── data_clean.py           # 模块3：语料治理 + 上传知识库
├── app.py                  # Flask 后端
├── static/index.html       # 模块4：自测页
├── sql/init.sql            # 建表 + 模拟工单
├── data/corpus/            # 四类运维语料 Markdown
├── scripts/
│   ├── setup_mysql.ps1     # MySQL 一键初始化
│   └── init_db.py          # 执行建表 SQL
└── docs/
    ├── CLOUD_DIFY_SETUP.md # 云端 Dify 配置说明
    └── DIFY_AGENT_SETUP.md # 智能体编排说明
```

## 快速开始

### 1. 配置 `.env`

复制 `.env.example` 为 `.env`，填写：

```env
DIFY_APP_API_KEY=app-xxx
DIFY_DATASET_API_KEY=dataset-xxx
DIFY_DATASET_ID=uuid
MYSQL_PASSWORD=你的密码
```

### 2. 安装 MySQL（Windows）

**管理员 PowerShell**：

```powershell
cd D:\Dify_agent\scripts
.\setup_mysql.ps1
```

默认 root 密码：`DifyOps@2026`（脚本会自动写入 `.env`）

### 3. 安装 Python 依赖并初始化库表

```powershell
cd D:\Dify_agent
pip install -r requirements.txt
python scripts/init_db.py
```

### 4. 上传语料到 Dify 知识库

```powershell
python data_clean.py --all
```

### 5. 工单预处理（可选）

```powershell
python work_order_sql.py --all
```

### 6. 命令行答疑测试

```powershell
python dify_api.py "MySQL主从延迟告警怎么处理？"
python dify_api.py --interactive
```

### 7. 启动 Web 自测页

```powershell
python app.py
```

浏览器打开：http://127.0.0.1:5000/

## 模块说明

| 模块 | 文件 | 功能 |
|------|------|------|
| 1 | `dify_api.py` | 调用 Dify Chat API，问答日志入 MySQL |
| 2 | `work_order_sql.py` | 工单正则分类、去重、高频问题推送 Dify |
| 3 | `data_clean.py` | 语料清洗、导出 JSON、API 上传知识库 |
| 4 | `static/index.html` + `app.py` | 前端自测 |

## 语料分类

| 文件 | 类别 |
|------|------|
| `server_fault.md` | 服务器故障 |
| `database_error.md` | 数据库报错 |
| `base_station.md` | 基站运维 |
| `ticket_workflow.md` | 工单流程 |

## 业务价值

- 覆盖约 80% 基础运维重复答疑
- 自动分拣重复工单、沉淀标准语料
- 完全匹配移动运维智能化研发实习场景

## 文档

- [云端 Dify 配置](docs/CLOUD_DIFY_SETUP.md)
- [智能体编排说明](docs/DIFY_AGENT_SETUP.md)
- [本地 Dify Docker 教程](dify/SETUP_手把手教程.md)（可选）
