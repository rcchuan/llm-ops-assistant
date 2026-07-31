# Dify 运维智能体 · 手把手配置教程

> 配合岗位「熟悉 Dify」：在 Dify 里完成知识库 + 两个应用（一线答疑、工单辅助）。  
> 硅基流动 Key 已在 `D:\Dify_agent\.env`，在 Dify 里再填一次即可。

---

## 第 0 步：安装并启动 Dify

### 0.1 安装 Docker Desktop（若还没有）

1. 若 winget 已在安装，等 **Docker Desktop** 装完并**重启电脑**（安装程序通常会提示）。
2. 从开始菜单打开 **Docker Desktop**，等到左下角/托盘显示 **Engine running**。
3. 验证：

```powershell
docker --version
docker compose version
```

### 0.2 下载 Dify 并启动

**方式 A（推荐，网络正常时）：**

```powershell
cd D:\Dify_agent\dify
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned -Force
.\install-dify.ps1
```

**方式 B（GitHub 连不上时）：**

1. 用浏览器下载（可试手机热点）：  
   https://github.com/langgenius/dify/archive/refs/heads/main.zip  
2. 解压到 `D:\dify`（保证存在 `D:\dify\docker` 文件夹）。
3. 执行：

```powershell
cd D:\dify\docker
copy .env.example .env
docker compose up -d
```

### 0.3 初始化管理员

浏览器打开：**http://localhost/install**

- 设置管理员邮箱、密码（自己记住）
- 完成后登录：**http://localhost**

---

## 第 1 步：配置硅基流动模型

1. 右上角头像 → **设置** → **模型供应商**
2. 找到 **OpenAI-API-compatible**（或「OpenAI 兼容」）→ **添加**
3. 填写：

| 项 | 值 |
|----|-----|
| 名称 | 硅基流动 |
| API Key | 从 `D:\Dify_agent\.env` 复制 `OPENAI_API_KEY` |
| API Base URL | `https://api.siliconflow.cn/v1` |

4. 保存后，在 **系统模型设置** 里：
   - **LLM** 选：`Qwen/Qwen2.5-7B-Instruct`（或控制台里标「免费」的模型）
   - **Embedding**（向量模型）：选硅基流动提供的 embedding 模型；若没有，可用 Dify 默认 / `BAAI/bge-m3` 等（以控制台可选列表为准）

5. 点击 **测试连接**，显示成功即可。

---

## 第 2 步：创建知识库「运维知识库」

1. 左侧 **知识库** → **创建知识库**
2. 名称：`运维知识库`
3. **上传文件**（都在你电脑里）：

```
D:\Dify_agent\data\corpus\faq.md
D:\Dify_agent\data\corpus\runbook_host.md
D:\Dify_agent\data\corpus\runbook_db.md
D:\Dify_agent\data\corpus\tickets_history.md
```

4. **分段设置**（与项目一致）：
   - 分段模式：按段落 或 自定义
   - 分段长度：**400**
   - 重叠：**80**

5. 保存并等待 **索引完成**（状态为可用）。

---

## 第 3 步：应用一「运维一线答疑」（Chatflow）

1. **工作室** → **创建应用** → 类型选 **Chatflow**（或「聊天助手」+ 开启知识库）
2. 名称：`运维一线答疑`
3. 进入 **编排**：

```
[开始] → [知识检索] → [LLM] → [直接回复]
```

### 节点配置

**知识检索**

- 知识库：`运维知识库`
- Top K：**5**
- 开启「引用与归属」

**LLM**

- 模型：`Qwen/Qwen2.5-7B-Instruct`
- **系统提示词**：打开 `D:\Dify_agent\dify\prompts\qa_system.txt`，全文复制粘贴
- **用户提示词**（上下文变量）示例：

```
【用户问题】
{{#sys.query#}}

【参考资料】
{{#context#}}
```

（若界面是「查询」变量，用 `{{query}}` 等，以 Dify 当前版本右侧变量面板为准，把检索结果变量拖进提示词。）

4. **发布** → **运行**，测试问题：

   - `业务平台登录超时应该先查什么？`
   - `MySQL 主从延迟告警怎么处理？`

5. 看回答是否带 **引用来源**（faq.md / runbook 等）。

---

## 第 4 步：应用二「运维工单辅助」（Workflow）

1. **创建应用** → 类型 **Workflow**
2. 名称：`运维工单辅助`
3. 编排：

```
[开始] 输入变量 symptom（文本）
    → [知识检索] 运维知识库 TopK=5
    → [LLM]
    → [结束]
```

**LLM 系统提示词**：复制 `dify\prompts\ticket_system.txt`

**用户提示词**：

```
【现象描述】
{{symptom}}

【参考资料】
{{#context#}}
```

4. 发布后在「运行」输入：

   `多个网点反馈登录页面转圈后超时，约 10:30 开始`

5. 输出应为 **JSON**（分类、原因、步骤等）。

---

## 第 5 步：评测（可选，写简历用）

打开 `D:\Dify_agent\data\eval_qa.jsonl`，把里面的问题在「运维一线答疑」里逐条问一遍，看是否命中关键词。

---

## 常见问题

| 问题 | 处理 |
|------|------|
| `docker` 不是命令 | 安装并启动 Docker Desktop，重启终端 |
| `localhost` 打不开 | `docker compose ps` 看容器是否 Up；等 2 分钟再试 |
| 模型测试失败 | 检查 API Key、余额；Base URL 必须带 `/v1` |
| 知识库一直索引中 | 看 Embedding 模型是否配好 |
| 不想装 Docker | 用 **Dify 云端** https://cloud.dify.ai 注册，步骤 1～4 相同，仅无需 `docker compose` |

---

## 简历一句话（Dify 版）

> 基于 **Dify** 构建运营商运维知识库与 **Chatflow/Workflow** 应用，实现可溯源的一线答疑与结构化工单辅助，语料来自 FAQ/手册/历史工单，大模型对接硅基流动 API。

---

## 本目录文件说明

| 文件 | 用途 |
|------|------|
| `install-dify.ps1` | 一键克隆 + docker compose up |
| `SETUP_手把手教程.md` | 本文档 |
| `prompts/qa_system.txt` | 答疑提示词 |
| `prompts/ticket_system.txt` | 工单提示词 |
| `DIFY_IMPORT.md` | 简要迁移说明 |
