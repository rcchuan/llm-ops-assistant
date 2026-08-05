# Vue 3 前端

阶段 3 前端在认证与用户管理页面之外，提供单页连续智能问答和最近 50 条个人问答历史。界面继续使用现有 Element Plus，不引入第二套 UI 框架。

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

## Token 存储风险

阶段 2 使用 LocalStorage 保存 2 小时 Access Token，适合本地毕设演示，但 LocalStorage 会受到 XSS（跨站脚本）风险影响。当前不实现 Cookie、Refresh Token 或服务端撤销列表；后续正式部署可结合完整威胁模型重新设计认证存储。

## 桌面端范围

- 最低验收分辨率：`1280×720`
- 推荐分辨率：`1920×1080`
- 本阶段不承诺小于 1280px 的完整操作体验，不实现移动端布局。
