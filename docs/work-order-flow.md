# 问答转工单与最小状态流转

## 定位与边界

工单只承接普通运维人员本人已持久化的问答，形成“创建工单 -> 管理员处理 -> 用户确认或退回”的最小人工闭环。阶段 4 完成时尚未实现知识沉淀；阶段 5 将增加关闭时生成候选知识和 Dify Dataset API 同步，但仍不实现派单、SLA、审批、附件、通知、搜索、删除或归档。

## 状态与权限

```text
pending -> processing    管理员开始处理
processing -> resolved   管理员填写解决方案
resolved -> closed       创建者确认解决
resolved -> processing   创建者填写未解决说明
```

其它跳转均由后端拒绝。管理员不能创建或代确认工单；普通用户只能读取自己的工单，管理员可读取全部工单。普通用户在 `pending` 和 `processing` 状态收到的 `solution` 固定为 `null`，管理员始终可见；`resolved` 和 `closed` 状态才向创建者展示解决方案。

阶段 5 已确认从整个正式系统删除重复的 `processing_notes`（处理过程）字段，仅保留 `solution`（解决方案）。删除范围包括 ORM、Schema、Service、API、前端和测试；数据库删列前必须统计非空历史数据、审查离线迁移 SQL，并单独取得真实 MySQL 执行授权。历史处理过程不自动拼接到解决方案。

## 数据表与事务

- `formal_work_orders`：正式系统工单表，唯一关联 `qa_record_id`，保存用户补充内容、管理员处理内容、最新未解决说明和当前状态。
- `formal_work_order_logs`：正式系统状态日志表，只记录创建、开始处理、标记已解决、确认关闭和问题仍存在。暂存处理内容不写日志。
- `work_orders`：旧 Flask 原型工单表，保留原结构和数据；正式系统不读取、不修改、不迁移、不删除也不重命名该表。

创建与创建日志同事务，状态变化与状态日志同事务，状态修改在检查前使用行锁，处理内容暂存使用独立事务。`qa_record_id` 同时由 Service 前置查重和数据库唯一约束保护。

### 表名冲突调整

首次真实迁移前 Alembic 为 `20260804_03`。首次执行 `20260805_04` 时，MySQL 因旧原型 `work_orders` 已存在而在第一条 DDL 上返回 1050；版本未推进，未创建状态日志表。经授权后，revision 仍保持 `20260805_04`，仅将阶段 4 正式表改为 `formal_work_orders` 和 `formal_work_order_logs`，API 路径继续使用 `/work-orders`。

## API

- `POST /api/v1/work-orders`
- `GET /api/v1/work-orders`
- `GET /api/v1/work-orders/{id}`
- `POST /api/v1/work-orders/links`
- `POST /api/v1/work-orders/{id}/start`
- `PUT /api/v1/work-orders/{id}/processing-content`
- `POST /api/v1/work-orders/{id}/resolve`
- `POST /api/v1/work-orders/{id}/confirm`
- `POST /api/v1/work-orders/{id}/reopen`

列表每页 20 条，后端按 `created_at DESC, id DESC` 排序。`links` 一次查询最多 50 个去重正整数，只返回当前 operator 本人的问答映射。

## 页面

- `/work-orders`：普通用户查看本人工单，管理员查看全部工单。
- `/work-orders/new/:qaRecordId`：普通用户从问答创建工单。
- `/work-orders/:id`：按角色和状态显示处理或确认操作。

问答页和历史页使用批量映射显示“转为工单”或“查看工单”。所有内容使用纯文本绑定，不使用 `v-html`，不展示日志时间线。

## 当前验证

- TDD 表名调整 RED：2 个模型与迁移结构测试按预期失败；修改正式 ORM 和 revision 后 GREEN：`2 passed`。
- 隔离 SQLite 后端全量测试：`111 passed, 1 warning`；真实 MySQL `alembic check` 无待生成升级操作。
- 前端内置测试：`6 passed`；`npm run build` 通过，保留既有 Rollup 注释和大 chunk warning。
- offline SQL：只创建 `formal_work_orders`、`formal_work_order_logs`、3 个显式索引、4 个外键、`qa_record_id` 唯一约束和 3 个状态 CHECK；不包含旧 `work_orders` 的 CREATE、ALTER 或 DROP。
- 真实 MySQL：首次使用旧正式表名执行迁移时因原型 `work_orders` 同名冲突失败，版本未推进且未留下正式表残留；改用 `formal_work_orders`、`formal_work_order_logs` 并再次取得授权后，仅执行一次 `alembic upgrade head`，成功由 `20260804_03` 升级到 `20260805_04 (head)`。两张正式表及约束均存在；MySQL 另为外键和唯一约束生成支撑索引。旧 `work_orders` 结构未变且仍为 10 行，既有正式表和原型表仍存在。
- 真实 API：创建、重复创建、跨用户隔离、批量映射、分页，以及 `pending -> processing -> resolved -> processing -> resolved -> closed` 全流程均通过；关闭后非法保存或退回返回冲突。
- 桌面浏览器（1280x720）：operator 创建入口与工单映射、admin 列表/开始处理/暂存/首次解决、处理草稿隔离、operator 查看方案/退回/再次查看方案/确认关闭、关闭后只读均通过；关键保存请求为 1 个业务 XHR，另有 1 个 CORS preflight，不是重复提交；Console 无新增 error 或 warning。
- 独立只读审查：首次发现查询异常映射、并发状态锁、trim 校验顺序、Service 可见性职责和映射失败入口共 6 项问题；逐项 RED -> GREEN 修复，Standards 轴复核通过，Spec 轴相关回归测试通过。
- Hermes 最终独立复核发现并已修复 4 项问题：创建页和详情页补齐参考来源及时间字段；移除 commit 成功后的非必要 refresh，避免误报保存失败；精确识别 `qa_record_id` 唯一冲突；增加创建 409 恢复和状态写失败后的单次详情对账。
- 最终补验：创建页、详情页展示内容符合冻结需求；创建返回 409 时可进入已有工单；状态写失败只产生 1 次业务写请求和 1 次 GET 对账；links 失败保持 fail-closed。
- 本轮修复未新增 Alembic revision，未重新执行数据库迁移；真实 MySQL 继续保持 `20260805_04 (head)`，旧 `work_orders` 仍为 10 行。
- 失败迁移未推进 Alembic 版本，且未留下正式表残留；旧原型表未被修改。验收产生的账号、问答和工单数据按授权边界保留，未执行未授权清理。

## 阶段 5 边界

阶段 5 只处理阶段上线后新关闭工单的候选知识、管理员轻量复核和首次 Dify Dataset API 同步：关闭工单、关闭日志和唯一候选在同一事务生成；初始资料仍在 Dify 控制台导入。阶段 5 不提供通用文档上传、`knowledge_documents`、搜索分类、删除驳回、版本管理、远端更新删除或索引轮询。
