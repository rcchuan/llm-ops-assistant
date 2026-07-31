# Vue 3 前端

阶段 1 前端只展示正式后端与 MySQL 的健康状态，不包含登录、问答、工单或数据看板。

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

`VITE_API_BASE_URL` 只保存公开的后端 API 地址。数据库凭证和 Dify Key 不得放入前端配置。

开发环境由浏览器直接访问 FastAPI，后端 CORS 仅允许配置的前端地址；本阶段不同时配置 Vite proxy。
