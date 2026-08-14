# 阶段 7 截图索引

以下 PNG 均来自 2026-08-10 Windows 真实浏览器操作，并已检查未显示密码、JWT、Dify API Key、数据库密码、`.env` 或完整敏感连接信息。现有演示账号显示名称中的问号乱码属于历史数据，未执行未授权清理。

| 编号与文件名 | 来源 | 功能与操作 | 论文建议位置 | 答辩建议环节 | 复现与替换方法 |
| --- | --- | --- | --- | --- | --- |
| S7-WIN-DEV-01 `win-dev-chat.png` | Windows 开发模式 | 真实 Dify 问答与 4 个来源入口 | 智能问答实现 | 核心问答 | Vite 5173 登录 operator，新对话发送脱敏问题后重拍 |
| S7-WIN-DEV-02 `win-dev-work-orders.png` | Windows 开发模式 | operator 已有工单列表 | 工单模块实现 | 工单概览 | operator 打开“我的工单”后重拍 |
| S7-WIN-DEV-03 `win-dev-statistics-health.png` | Windows 开发模式 | admin 统计看板与健康状态 | 系统测试 | 健康与统计 | admin 打开统计看板，等待数据加载后重拍 |
| S7-WIN-DEV-04 `win-dev-knowledge.png` | Windows 开发模式 | admin 查看既有已同步候选 | 知识沉淀设计 | 候选知识 | admin 打开候选知识后重拍 |
| S7-WIN-PROD-01 `win-prod-home.png` | Windows 生产模式 | FastAPI 同源托管 Vue 首页 | 部署设计 | 部署形态 | 停止 Vite，只启动 Uvicorn，登录 8000 后重拍 |
| S7-WIN-PROD-02 `win-prod-chat-before.png` | Windows 生产模式 | 唯一模拟故障首次问答，知识未覆盖 | 闭环验收 | 问答转工单 | 使用同等脱敏新案例首次提问后重拍 |
| S7-WIN-PROD-03 `win-prod-work-order.png` | Windows 生产模式 | `WO-000005` 已解决及确定性方案 | 闭环验收 | 工单处理 | admin 完成处理并标记已解决后重拍 |
| S7-WIN-PROD-04 `win-prod-knowledge-review.png` | Windows 生产模式 | `KE-2` 同步前标题与 Markdown 复核 | 知识沉淀设计 | 同步前确认 | 停在未同步候选编辑区并脱敏后重拍 |
| S7-WIN-PROD-05 `win-prod-knowledge-synced.png` | Windows 生产模式 | `KE-2` 已同步、文档 ID 和同步时间 | 知识沉淀验收 | 同步结果 | 经授权完成唯一同步并收到真实文档 ID 后重拍 |
| S7-WIN-PROD-06 `win-prod-chat-after.png` | Windows 生产模式 | 同义问法命中新知识，展开来源显示 `[KE-2]` | 知识复用验收 | 闭环结果 | 等待索引后用不含唯一标识的同义问法，展开来源后重拍 |

| S7-CENTOS-01 `centos-login.png` | CentOS 正式环境 | Systemd 重启自恢复后的登录页 | 系统部署与测试 | 部署完成 | `http://192.168.100.42:8000` 无登录态访问；截图本身不含地址栏，地址由浏览器 URL 与外部 curl 200 交叉核验 |
| S7-CENTOS-02 `centos-health.png` | CentOS 正式环境 | health 显示 API/MySQL up、Dify App/Dataset configured | 系统测试 | 健康检查 | 访问 `/api/v1/health`；截图本身不含地址栏，来源由浏览器 URL 与 curl 200 交叉核验 |

后续替换截图时必须使用新的脱敏案例，不能重复同步 `KE-2` 或新增阶段 7 第二条 Dify 文档。CentOS 登录页和健康检查已实测追加；如需 CentOS 知识检索截图，应复用现有 `KE-2` 检索结果，不新增 Dataset 文档。
