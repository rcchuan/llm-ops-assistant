# 智能运维问答

阶段 3 将正式系统接入已有 Dify Chatflow，仅使用现有知识库生成运维回答，不管理知识库内容，也不实现工单、多会话列表或流式输出。

## 调用链与职责

```text
Vue View -> frontend API -> Chat Router -> Chat Service
                                      |-> ConversationRepository / QARecordRepository -> MySQL
                                      `-> Dify Integration -> Dify Cloud
```

- Router 负责认证依赖、Schema、状态码和领域异常映射。
- Service 负责最近会话恢复、新对话、多轮上下文、保存降级、归属隔离和反馈规则。
- Repository 负责 SQLAlchemy 查询、组合持久化、事务提交与回滚。
- Integration 负责 Dify blocking 请求、60 秒超时、响应校验、来源精简和外部错误脱敏。

前端只访问 FastAPI，不持有 Dify Key，也不读取 Dify 原始 ID。

## 配置

真实值只写入被 Git 忽略的 `backend/.env`：

```dotenv
DIFY_BASE_URL=https://api.dify.ai/v1
DIFY_APP_API_KEY=<Dify App API Key>
DIFY_TIMEOUT_SECONDS=60
```

自动化测试通过 `httpx.MockTransport` 模拟 Dify，不发出真实网络请求。

## 数据

- `conversations` 保存用户归属、Dify conversation ID 和时间。
- `qa_records` 保存成功问答、精简来源、响应时间和可覆盖的本地反馈。
- 首次问答的 conversation 与 qa_record 在一次事务中创建，失败不产生空会话。
- 历史原型表（包括 `qa_logs`）保持原样，不迁移、不删除，也不与正式表混用。

迁移 revision 为 `20260804_03`。真实 MySQL 执行前应先离线审查 SQL，确认只创建上述两张表。

## 行为与失败处理

进入问答页恢复最近一次已保存会话的最近 50 条记录。手动新对话只清空页面；下一次成功问答才创建新会话。个人历史按时间倒序最多返回 50 条。

Dify timeout 映射为 504，配置或服务不可用映射为 503，无效响应映射为 502。Dify 成功但数据库保存失败时，回答仍显示且标记 `persisted=false`，不返回记录 ID、不显示反馈，并锁定当前对话，直到用户点击“新对话”。

问题在后端 trim 后必须非空且不超过 1000 字符。回答和来源仅作纯文本渲染，不执行 HTML 或脚本。

## 本地验证

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q

cd ..\frontend
npm run build
```

本阶段不包含工单、知识库管理、Dify Dataset API、多会话管理、Markdown 渲染或流式输出。
