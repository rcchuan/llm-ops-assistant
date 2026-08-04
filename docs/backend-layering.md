# 后端轻量分层架构

## 分层与依赖方向

```text
Router / API
    -> Service
        -> Repository
            -> SQLAlchemy / MySQL

未来阶段 3：
Service
    -> Integration
        -> Dify Cloud
```

正式后端只允许依赖由上向下流动。Schema 和 Model 是数据结构，Core 提供配置、安全工具、输入校验和与 HTTP 无关的领域异常。

## 各层职责

### Router / API

- 解析 HTTP 参数并声明依赖、响应模型和状态码；
- 使用数据库 Session 构造 Repository；
- 调用 Service，并把领域异常映射为现有 HTTP 状态码和中文错误；
- 不编写 SQLAlchemy 查询，不提交事务，不修改 User，不处理密码和业务规则，不调用外部服务。

### Service

- 执行登录、Token 状态校验、改密、权限检查、用户创建、启停、密码重置和初始管理员规则；
- 通过 Repository 访问用户数据，通过 Core 安全工具处理密码和 JWT；
- 不依赖 FastAPI，不编写 SQLAlchemy 查询，不决定 HTTP 响应，不调用外部服务。

### Repository

- 封装用户按 ID/用户名查询、分页搜索、新增、保存、提交、失败回滚和刷新；
- 不判断角色、强制改密、密码规则和 `token_version` 递增；
- 不依赖 FastAPI 或 Schema，不抛 `HTTPException`，不调用外部服务。

### Core、Model 与 Schema

- Core 提供配置、安全工具、共享输入校验和领域异常；
- Model 只维护 SQLAlchemy 数据库映射；
- Schema 只维护请求、响应结构及 HTTP 输入格式校验，不访问数据库和 Service。

### Integration

`app/integrations/` 是阶段 3 外部系统适配层的唯一入口。本阶段不包含 Dify Client、接口基类、配置或占位业务代码。

## 实际调用链

```text
POST /auth/login
-> auth Router
-> login_user
-> UserRepository
-> MySQL

受保护接口
-> API dependency
-> resolve_current_user / ensure_password_changed / ensure_admin
-> UserRepository
-> MySQL

用户查询、创建、启停、重置密码
-> users Router
-> user_service
-> UserRepository
-> MySQL

应用启动
-> bootstrap_initial_admin
-> UserRepository
-> MySQL
```

阶段 3 的智能问答应由 Chat Service 同时协调业务 Repository 和 Dify Integration；Router 不得直接调用 Dify。

## 轻量设计取舍

当前规模只有一个 SQLAlchemy 用户数据实现，因此不增加 Repository Interface/Implementation 双层、Unit of Work、Repository Factory 或依赖注入容器。系统也不采用 DDD、微服务、CQRS、领域事件和事件总线。需要新增这些模式时，必须先出现当前结构无法解决的真实需求。

## 后续模块规则

1. 新业务先确定 Router 可观察的外部行为和 Service 测试 seam；
2. SQLAlchemy 查询与事务只写在 Repository；
3. 业务规则和跨 Repository/Integration 协调只写在 Service；
4. HTTP 状态、请求依赖和响应 Schema 只写在 Router；
5. 第三方调用只写在 Integration，并由 Service 调用；
6. 不为单一实现预建接口、工厂或容器；
7. 新增行为先写失败测试，再做最小实现，并保持 API 与数据库兼容。
