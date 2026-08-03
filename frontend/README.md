# Vue 3 前端

阶段 2 前端提供登录、强制/主动修改密码、基础首页和管理员用户管理。界面使用现有 Element Plus，按桌面端企业运维平台的信息密度重新设计，不使用后台模板或第二套 UI 框架。

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

## Token 存储风险

阶段 2 使用 LocalStorage 保存 2 小时 Access Token，适合本地毕设演示，但 LocalStorage 会受到 XSS（跨站脚本）风险影响。当前不实现 Cookie、Refresh Token 或服务端撤销列表；后续正式部署可结合完整威胁模型重新设计认证存储。

## 桌面端范围

- 最低验收分辨率：`1280×720`
- 推荐分辨率：`1920×1080`
- 本阶段不承诺小于 1280px 的完整操作体验，不实现移动端布局。
