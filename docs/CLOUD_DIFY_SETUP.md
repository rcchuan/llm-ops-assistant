# 云端 Dify 配置步骤（cloud.dify.ai）

本项目使用 **云端 Dify**，API 基址固定：`https://api.dify.ai/v1`

## 一、注册与模型

1. 打开 https://cloud.dify.ai 注册登录
2. **设置 → 模型供应商 → 安装 OpenAI-API-compatible**
3. 填写硅基流动：
   - Base URL: `https://api.siliconflow.cn/v1`
   - API Key: 你的硅基流动 Key
4. **添加模型（两次）**：
   - LLM: `Qwen/Qwen2.5-14B-Instruct`
   - Text Embedding: `BAAI/bge-large-zh-v1.5` 或 `BAAI/bge-m3`
5. **系统默认模型设置** 中指定默认 LLM 与 Embedding

## 二、知识库

1. **知识库 → 创建一个空知识库**
2. 名称：`移动运维知识库`，索引：**高质量**
3. **服务 API** 页复制：
   - Dataset ID（或浏览器 URL 中的 UUID）
   - 创建 **知识库 API Key**（`dataset-` 开头）

语料由本项目 `data_clean.py` 通过 API 上传，无需手工传文件。

## 三、应用「通信运维答疑智能体」

1. **工作室 → 创建 Chatflow**
2. 编排：`开始 → 知识检索 → LLM → 直接回复`
3. 知识检索：选 `移动运维知识库`，Top K=3~5，**关闭 Rerank**
4. LLM：选 14B 模型，Temperature≈0.3，Max Tokens≈512
5. SYSTEM 提示词：见 `dify/prompts/qa_system.txt`
6. USER 模板：

```text
【用户问题】
{用户输入 / query}

【参考资料】
{知识检索 / result}
```

7. **发布** → **访问 API** → 创建 **应用 API Key**（`app-` 开头）

## 四、写入 .env

```env
DIFY_BASE_URL=https://api.dify.ai/v1
DIFY_APP_API_KEY=app-xxx
DIFY_DATASET_API_KEY=dataset-xxx
DIFY_DATASET_ID=uuid
```

## 五、API 说明

| 用途 | 接口 | Key |
|------|------|-----|
| 答疑 | POST /v1/chat-messages | 应用 Key |
| 上传语料 | POST /v1/datasets/{id}/document/create-by-text | 知识库 Key |

## 六、常见问题

| 问题 | 处理 |
|------|------|
| Embedding 500 | 换 `bge-large-zh-v1.5` 或检查硅基流动余额 |
| Rerank 不能为空 | 知识检索召回设置里关闭 Rerank |
| 回答乱码复读 | 换 14B、降 Temperature、限制 Max Tokens |
