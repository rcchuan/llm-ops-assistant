# Vue 3 前端

阶段 5 前端在工单页面基础上增加 admin-only 的候选知识单页。界面继续使用现有 Element Plus，不引入第二套 UI 框架。

## 配置与启动

```powershell
cd frontend
Copy-Item .env.example .env.local
npm install
npm run dev
```

默认页面：`http://127.0.0.1:5173/`

生产构建：

```powershell
npm run build
```

`VITE_API_BASE_URL` 只保存公开的后端 API 地址。数据库凭证、JWT Secret、用户密码和 Dify Key 不得放入前端配置。

## 认证流程

- 未登录访问受保护页面会转到 `/login`。
- 登录后通过 `/auth/me` 恢复用户状态。
- `must_change_password=true` 时只能进入 `/change-password`。
- 管理员可访问 `/admin/users`，普通运维人员会被送回安全首页。
- 退出、401 或改密成功后清除 Access Token。
- 403 + `PASSWORD_CHANGE_REQUIRED` 会转到强制改密页。

## 智能问答

- `/chat` 在进入时恢复最近一次已保存会话，快捷问题只填入输入框，不自动发送。
- “新对话”清空当前页面，下一次提问才创建新会话，不删除旧历史。
- 回答和来源均使用 Vue 文本绑定，不使用 Markdown 或 `v-html`。
- 只有已持久化回答可反馈；保存失败的回答会锁定当前对话，点击“新对话”后恢复。
- `/chat/history` 只读展示当前用户最近 50 条记录，管理员也不能查看其他用户数据。

## 工单页面

- `/work-orders`：我的工单或管理员工单管理。
- `/work-orders/new/:qaRecordId`：普通用户补充三个字段后创建工单。
- `/work-orders/:id`：管理员处理或普通用户确认结果。

管理员问答不显示转单入口；普通用户在处理阶段看不到管理员草稿。页面不提供搜索、筛选、删除、归档或日志时间线。

## 候选知识页面

- `/admin/knowledge-entries`：管理员查看、编辑并首次同步工单候选知识；普通用户无菜单且路由会被拦截。
- `pending` 和 `sync_failed` 可编辑标题及 Markdown 纯文本正文；`synced` 永久只读。
- 同步失败后只对账一次本地状态并保留原错误；timeout 提示先按 `[KE-{id}]` 到 Dify 控制台核对。
- 页面不解析 Markdown，不使用 `v-html`，不提供上传、搜索、筛选、删除、分类、版本、Dify 跳转或索引状态。

完整边界和当前验收状态见 [`docs/knowledge-deposition.md`](../docs/knowledge-deposition.md)。

## Token 存储风险

阶段 2 使用 LocalStorage 保存 2 小时 Access Token，适合本地毕设演示，但 LocalStorage 会受到 XSS（跨站脚本）风险影响。当前不实现 Cookie、Refresh Token 或服务端撤销列表；后续正式部署可结合完整威胁模型重新设计认证存储。

## 桌面端范围

- 最低验收分辨率：`1280×720`
- 推荐分辨率：`1920×1080`
- 本阶段不承诺小于 1280px 的完整操作体验，不实现移动端布局。
