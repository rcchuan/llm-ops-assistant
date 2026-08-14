# 阶段 7 测试与演示记录

## 环境与范围

- 日期：2026-08-10
- 仓库：`D:\projectcode\llm-ops-assistant`
- 分支：`feature/stage-7-deployment`
- 起始基线：`cc2f99f88c5f7f087d003cafaa05641749850c7b`
- 自动化：隔离 SQLite + Mock Dify；未连接真实 MySQL 或写入真实 Dify。
- Alembic check：连接既有 MySQL，仅做 schema 对比；未执行 migration、downgrade 或数据修改。
- Windows 人工验收：真实 MySQL + Dify Cloud；只创建 `WO-000005`、`KE-2` 和两条闭环问答记录，不清理历史数据。

## 自动化测试与构建

| 命令 | 退出码 | 真实结果 |
| --- | ---: | --- |
| `backend/.venv/Scripts/python.exe -m pytest -q` | 0 | `154 passed, 1 warning in 17.75s` |
| `backend/.venv/Scripts/python.exe -m alembic check` | 0 | `No new upgrade operations detected.`，MySQLImpl |
| `npm test` | 0 | `19 passed, 0 failed` |
| `npm run build` | 0 | Vite 7.3.6 构建成功，1700 modules transformed |

非阻塞 warning：后端存在既有 `TestClient`/httpx deprecation warning；前端构建存在 Rollup PURE 注释位置和单个 chunk 超过 500 kB warning。本阶段未新增依赖，也未扩大范围处理性能优化。

阶段 7 静态托管测试通过 HTTP 公共接口验证状态码、Content-Type 和必要内容，测试 dist 全部来自 Pytest 临时目录，不读取或生成仓库真实 `frontend/dist`。

## 代表性人工用例

| 模块 | 代表性用例 | Windows 真实结果 |
| --- | --- | --- |
| 认证 | admin/operator 分别登录 | 两个角色均登录成功；角色菜单正确。相同 Chrome profile 的 LocalStorage Token 会互相覆盖，因此验收按角色退出后重新登录。 |
| 智能问答 | operator 发起真实问答并查看来源 | 开发问答成功并显示 4 个来源；生产首次问题明确未覆盖，索引后同义复问成功命中 1 个来源。 |
| 工单 | 未覆盖问答转工单并闭环 | `WO-000005` 完成 `pending -> processing -> resolved -> closed`。 |
| 候选知识 | admin 复核并首次同步 | `KE-2` 按用户确认内容唯一同步，状态 `synced`，无 sync error。 |
| 统计/健康 | admin 打开统计看板与健康信息 | 问答、工单、候选统计可读；API/MySQL 正常，Dify App/Dataset 配置完整。 |

## Windows 开发模式代表性回归

链路：Chrome -> Vite `127.0.0.1:5173` -> FastAPI `127.0.0.1:8000` -> MySQL -> Dify Cloud。

- operator 与 admin 登录成功；首页显示前端已加载、FastAPI `0.3.0`、MySQL 连接正常。
- operator 真实提问“Linux 主机的 `/var/log` 使用率超过 85%……”成功，展示 4 个来源；工单列表可访问。
- admin 工单管理、候选知识、统计看板和健康信息均可访问。
- Console 检查无 error/warning；已捕获的 `/auth/me`、工单列表等关键 XHR 返回 `200`。
- 本轮未创建工单或同步知识；开发问答按现有行为新增一条问答记录。

## Windows 生产模式完整闭环

停止 Vite 后只保留 FastAPI/Uvicorn，访问 `http://127.0.0.1:8000`。

### 静态托管

| 路径 | 真实结果 |
| --- | --- |
| `/`、`/chat` | `200 text/html` |
| 构建后的 `/assets/index-CPZkdQWE.js` | `200 application/javascript` |
| `/api/v1/health` | `200 application/json` |
| `/api`、`/api/v1`、未知 `/api/v1/*` | `404 application/json`，未回退 |
| `/assets`、`/assets/`、缺失 asset | `404 application/json`，未回退 |

浏览器直接进入并刷新 `/chat` 后页面和登录态均正常，证明深层路由由 SPA index 回退。

### 业务闭环

1. operator 提问 `S7A-20260810-C9F2` 模拟故障；回答明确资料未覆盖，虽然展示 1 个既有来源，但没有确定性 AcmeAgent 方案。
2. 创建 `WO-000005`；admin 开始处理、保存确定性解决方案并标记已解决；operator 确认关闭。
3. 关闭事务生成 `KE-2`。同步前向用户展示实际标题、完整 Markdown 正文和唯一标识，取得明确授权。
4. 只点击一次“审核并同步”。`POST /api/v1/knowledge-entries/2/sync` 返回 `200 OK application/json`；无自动重试。
5. 页面和只读 ORM 均确认 `KE-2=synced`，Dify 文档 ID `209f5d75-c6df-4b97-b463-6c23f7582b94`，同步时间页面显示 `2026-08-10 20:38`，`sync_error=null`。
6. 人工登录间隔后，以不含唯一标识或 `[KE-2]` 的同义问法复问；`POST /api/v1/chat/messages` 返回 `200 OK application/json`。
7. 回答实际使用配置基线、`AcmeAgent.exe --verify-config`、`CONFIG_OK` 和 `Running`；展开的唯一来源标题包含 `S7A-20260810-C9F2` 与 `[KE-2]`。
8. 只读 ORM 确认复问为 `qa_records.id=14`，唯一 `source_names` 即上述 `[KE-2]` 文档；不是仅凭回答内容判定命中。

生产闭环 Console 无 error/warning。未创建或同步第二条 Dify 文档。

## 缺陷、修复与遗留

- TDD RED：新测试收集失败，原因是 `create_app` 尚不存在。
- 首次 GREEN：`3 passed, 1 failed`；Windows 将 `.js` 标记为 `application/javascript`，测试原先只接受 `text/javascript`。修正为接受两个合法 MIME type 后 `4 passed`。
- 现有 Dify Chatflow 回答会把 `<think>...</think>` 推理文本直接展示给用户。修改 Chatflow 配置超出阶段 7A 范围，未处理。
- 现有 operator 演示账号的显示名称在页面中含问号乱码。任务禁止清理或修改历史业务数据，未处理。
- CDP Network 对开发问答未捕获到已完成的 POST 事件；生产同步和索引后复问均取得明确 `200` Network 证据，数据库记录用于交叉核验。
- CentOS 阶段 7B 已完成部署目录、依赖、测试构建、MySQL 逻辑备份、Systemd、Windows 外部访问和整机重启自恢复验证。
- 远端 `alembic check` 报“删除 6 个 CHECK 约束”（`user_role`、`qa_record_feedback`、`work_order_status`、`work_order_log_from_status`、`work_order_log_to_status`、`knowledge_entry_status`）。经核实这些约束在模型与 migration 中均存在且语义一致，仅 model 中 `SqlEnum` 带 `length=8` 而 migration 未带的元数据差异，属 Alembic + MySQL 8 对 `native_enum=False` 约束的 autogenerate 误报；数据库已是 `20260807_05 (head)`，未执行任何迁移或约束修改。

## CentOS 阶段 7B 实测结果

- CentOS Stream 9、Python 3.11、Node.js 22、npm、MySQL client 和项目依赖安装完成。
- 精确部署 `cb7c346`；旧原型、旧 `.env` 和 MySQL 逻辑备份均在仓库外保留。
- 后端 `154 passed`、静态托管专项 `4 passed`、前端 `19 passed`，Vite 生产构建成功。
- `llm-ops-assistant.service` 已安装并处于 active/enabled；正式监听 `0.0.0.0:8000`。
- CentOS 本机和 Windows 外部访问 `/api/v1/health`、`/`、`/chat` 均返回 200。
- 整机重启后 MySQL 与应用服务自动恢复，8000 重新监听，内外部 HTTP 复验通过。
- 未新增 Dify 文档，未修改 MySQL 授权或业务数据，未执行 Alembic migration。
- 最终 commit/merge/tag 待 Git 收尾授权。完整命令与原因见 [`deployment/stage-7b-deployment-record.md`](../deployment/stage-7b-deployment-record.md)。
