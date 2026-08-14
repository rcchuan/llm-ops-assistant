# 工单知识沉淀

## 定位与边界

阶段 5 将新关闭工单中的已验证解决方案沉淀为候选知识，并由管理员复核后首次同步到当前 Chatflow 使用的唯一 Dify Dataset。初始 Markdown/TXT 运维资料仍由管理员在 Dify 控制台导入；正式系统不提供通用文档上传或知识库管理平台。

本阶段不实现 `knowledge_documents`、搜索筛选、标签分类、删除驳回、版本管理、多知识库切换、远端更新或删除、自动重试、远端去重、索引轮询和索引状态。

## 候选生成

只有工单创建者 operator 在工单为 `resolved` 且 `solution` 非空时确认解决，系统才生成候选。关闭动作在一个数据库事务中完成：锁定并核验工单、更新为 `closed`、写入关闭日志、创建唯一 `pending` 候选；任一步失败都会回滚。

候选标题为关联问题的 trim 后文本，正文由后端确定性生成，不调用 LLM：

```markdown
## 故障现象
{symptom}

## 已尝试步骤
{attempted_steps，仅非空时生成}

## 补充说明
{additional_notes，仅非空时生成}

## 解决方案
{solution}
```

正文不包含 AI 原始回答、检索来源、反馈、用户名、工单状态、未解决说明或已删除的 `processing_notes`。迁移不会为历史 `closed` 工单回填候选。

## 数据与状态

单表 `knowledge_entries` 通过唯一 `work_order_id` 关联 `formal_work_orders`，只保存候选正文、同步状态和最小 Dify 映射信息。状态固定为：

- `pending`：可编辑、可同步；
- `sync_failed`：可编辑、可人工重试，编辑后回到 `pending` 并清除旧错误；
- `synced`：永久只读，不能再次同步；后续修改只能在 Dify 控制台完成。

正式系统已从 ORM、Schema、Service、API、前端和测试中移除 `processing_notes`，仅保留 `solution`。真实 MySQL 已执行 revision `20260807_05` 并删除该列。

## API 与页面

候选知识 API 均要求已完成改密的 admin，operator 返回 403：

- `GET /api/v1/knowledge-entries?page=1`：固定每页 20 条，未同步组优先；
- `PUT /api/v1/knowledge-entries/{id}`：仅编辑未同步候选的 `title` 和 `content`；
- `POST /api/v1/knowledge-entries/{id}/sync`：复核并首次同步，失败后允许管理员人工重试。

管理员页面为 `/admin/knowledge-entries`。页面直接展示候选编号、来源工单、Markdown 原文、状态、Dify 文档 ID、精简错误和时间；提交期间禁用当前条目操作。同步请求失败后只做一次本地列表对账，并保留原请求错误，避免把结果不确定误报为可安全重复提交。

## Dify Dataset 契约

2026-08-07 已依据 Dify 官方文档并对当前真实 Dataset 做脱敏 probe：

- Method/path：`POST /datasets/{dataset_id}/document/create-by-text`；
- JSON 字段：`name`、`text`、`indexing_technique`；
- 当前 Dataset 要求固定 `indexing_technique=high_quality`，缺少时真实返回 HTTP 400 `invalid_param`；
- 成功为 HTTP 200，文档 ID 位于 `document.id`；真实返回的文档 ID 长度为 36（仅记录脱敏尾号 `ddd1`），同时返回长度为 20 的 `batch`。

probe 使用合成正文并真实创建了一个核验文档，未自动删除。Dataset API Key 与 Chat App API Key 分离，只保存在后端 `SecretStr` 配置中；前端、数据库、响应和文档均不保存 Key。

同步不自动重试。401/403 归为配置或认证错误，明确 HTTP 失败归为请求失败，timeout/网络错误归为结果不确定，成功响应无有效 `document.id` 归为无效响应。结果不确定或本地同步状态保存失败时，管理员必须先在 Dify 控制台按 `[KE-{id}]` 核对，再决定是否人工重试。

## 当前验证状态

- 后端隔离 SQLite 全量：`143 passed, 1 warning`；
- 前端自动化：`10 passed`；
- 前端生产构建：通过，仅有既存 Rollup 注释和大 chunk 警告；
- 真实 MySQL 已由 `20260805_04` 一次升级到 `20260807_05 (head)`；
- 真实 MySQL 非空 `processing_notes` 为 `3` 条，只统计数量且未读取正文；历史值不会搬迁到 `solution`；
- `20260805_04:20260807_05` offline SQL 已审查：只创建 `knowledge_entries` 及必要约束/索引、删除 `formal_work_orders.processing_notes` 并更新 Alembic revision；未触碰旧原型 `work_orders`、未删除其它表列、未回填历史业务数据；
- 迁移后已核验 10 个冻结字段、来源唯一约束、FK、三状态 CHECK 和分页索引；`formal_work_orders.processing_notes` 已删除，`alembic check` 无待生成操作；
- 旧原型 `work_orders` 仍为原 9 列和 10 行，迁移未触碰该表；
- 真实关闭候选：operator 创建 `WO-000004`、admin 标记 `resolved` 后由创建者确认关闭；MySQL 核验仅生成一个 `KE-1`，且 `resolved -> closed` 日志恰好一条；
- 管理员浏览器审核与真实同步：`KE-1` 从 `pending` 变为 `synced`，有 `synced_at` 且无 `sync_error`；Dify 文档 ID 长度为 36（仅记录脱敏尾号 `b81f`），后端仅收到一次同步请求；
- Dify Dataset 控制台存在 `KE-1` 文档且状态可用；真实召回测试命中该候选的 193 字符段落；
- Chatflow 最小修正验收未通过并已回滚：经单独授权，仅在现有 LLM 节点 Context 中加入 `知识检索.result`，未修改节点、连线、知识检索配置、SYSTEM Prompt、用户输入、聊天记忆或直接回复节点，并保存、发布；发布前 Context 为空，发布后 Dify 同时提示“要启用上下文功能，请在提示中填写上下文变量”；
- 使用原未命中问题“阶段5验收：Linux 服务因磁盘日志占满停止，如何排查并恢复？”发起真实 blocking 请求。知识检索实际返回 4 条 `metadata.retriever_resources`，其中第一条为标题带 `[KE-1]` 的文档（Dify 文档 ID 仅记录脱敏尾号 `b81f`），片段包含清理 `/var/log` 测试日志、配置 `logrotate`、重启服务及检查 `df -h`/服务状态；来源不是 Mock 或人工伪造；
- 尽管召回包含 `KE-1`，LLM 回答仍声称“资料中未覆盖”，没有使用 `KE-1` 的解决方案，故回答内容验收失败。同一 Dify `conversation_id` 的第二轮请求保持了相同会话 ID，但回答仍未使用上一轮检索知识，第二轮 `retriever_resources` 为 0；
- 该结果满足“Chatflow 无法正确回答/检索知识未进入回答”的回滚条件。已移除 LLM Context 中唯一的 `知识检索.result`，Context 恢复为空，并重新保存、发布；Dify 页面记录回滚自动保存时间 `2026-08-07 17:21:08`，发布菜单随后显示“已发布”。未修改 SYSTEM Prompt 或其它配置；
- 后续经授权完成 Chatflow 最小配置修正后，真实 blocking API 已验证：`metadata.retriever_resources` 非空且命中标题带 `[KE-1]` 的文档（Dify 文档 ID 仅记录脱敏尾号 `b81f`）；回答实际使用 `/var/log`、`logrotate` 和 `df -h` 等候选知识。相同 `conversation_id` 的第二轮保持多轮上下文，第二轮未重复返回来源。
- 正式前端验收改用隔离浏览器会话访问 `http://127.0.0.1:5173/chat`，使用 15 分钟临时 operator JWT 建立登录态；临时凭据桥接文件和服务在验收后立即删除/停止，未修改账号密码。点击“新对话”并发送“阶段5验收：Linux 服务因磁盘日志占满停止，如何排查并恢复？”后，页面回答真实包含 `/var/log`、`logrotate`、`df -h` 等内容，并显示折叠的“参考来源（4）”。
- MySQL 验收前 `qa_records` 共 9 条、最大 ID 为 10；正式前端发送后共 10 条、最大 ID 为 11。新增 `qa_records.id=11` 属于 operator `user_id=4`，问题与页面输入一致，`retriever_resources` 数量为 4，第一条文档名为“阶段5验收：Linux 服务因磁盘日志占满停止，如何排查并恢复？ [KE-1]”，片段包含工单候选中的故障现象和解决方案，证明页面显示来源来自真实后端持久化结果。
- 正式前端验收期间 Console 仅有 Vite 开发连接 debug 信息，无 JavaScript error。浏览器自动化工具未提供完整 Network 请求列表，因此“单次前端业务请求”不单独宣称通过；但数据库只新增 1 条匹配问答记录，未发现重复持久化。

## 2026-08-08 最终独立审查

**审查范围**：阶段 5 全量代码、迁移、文档和验收证据，对照任务书、需求分析和总实施计划。

**审查结论**：未发现阻塞性缺陷，阶段 5 功能与验收完成。

**已验证要点**：
- 工单 closed、关闭日志和候选知识创建在同一数据库事务中完成，任一步失败均回滚；
- knowledge_entries.work_order_id 有数据库唯一约束 uq_knowledge_entries_work_order_id，Service 层在关闭前二次校验；
- 历史 closed 工单不回填候选，仅新建关闭动作触发；
- 候选 API 要求 admin，operator 返回 403；关闭确认要求原始创建者 operator；
- pending 可编辑/可同步，sync_failed 可编辑/可重试（编辑后回 pending 并清旧错），synced 永久只读；
- Dify 明确失败归请求失败，timeout/网络归结果不确定，无效响应单独归类，本地保存失败保留 Dify 侧结果；
- 外部错误不泄露 Key、Authorization 或数据库凭证；
- processing_notes 已从 ORM/Schema/Service/API/前端/测试中完全移除，Alembic 迁移 20260807_05 仅删列和建表；
- 分层保持 Router → Service → Repository / Integration；
- 前端同步失败后只做一次本地对账，保留原错误，不误报为可安全重提交；
- 未实现任务书禁止的通用文档上传、knowledge_documents、搜索分类、删除驳回、版本管理、自动重试或索引轮询；
- 无调试代码、临时文件、真实凭证或运行产物残留。

**非阻塞残余**：
- 浏览器自动化工具未提供完整 Network 请求列表，单次前端业务请求不单独宣称通过（数据库仅新增 1 条匹配记录作为无重复持久化佐证）；
- 文档中前端测试计数已从 9 更正为 10。
