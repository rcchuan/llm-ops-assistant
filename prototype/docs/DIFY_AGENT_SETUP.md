# Dify 智能体配置说明 · 通信运维答疑

## 应用信息

| 项 | 值 |
|----|-----|
| 应用名称 | 通信运维答疑智能体 |
| 类型 | Chatflow |
| 知识库 | 移动运维知识库 |
| 模型 | Qwen/Qwen2.5-14B-Instruct |

## 编排拓扑

```
[开始] → [知识检索] → [LLM] → [直接回复]
```

## 知识检索节点

- 知识库：移动运维知识库
- 查询变量：sys.query
- Top K：5
- Rerank：关闭
- 引用与归属：开启

## LLM 节点

### 系统提示词（SYSTEM）

见项目文件 `dify/prompts/qa_system.txt`，核心规则：

1. 仅根据参考资料回答
2. 结构：结论 → 排查步骤 → 升级条件
3. 末尾标注引用编号
4. 资料不足时说明「资料中未覆盖」

### 用户消息（USER）

```text
【用户问题】
{{query}}

【参考资料】
{{知识检索.result}}
```

### 推荐参数

| 参数 | 值 |
|------|-----|
| Temperature | 0.2 ~ 0.3 |
| Max Tokens | 512 |
| 记忆 | 开启 |
| 视觉 | 关闭 |

## 知识库语料（4 类）

由 `data_clean.py --upload` 自动上传：

1. 服务器故障 → `data/corpus/server_fault.md`
2. 数据库报错 → `data/corpus/database_error.md`
3. 基站运维 → `data/corpus/base_station.md`
4. 工单流程 → `data/corpus/ticket_workflow.md`

## Python 调用示例

```python
from dify_api import chat_and_log

result = chat_and_log("MySQL主从延迟告警怎么处理？")
print(result["answer"])
```

日志自动写入 MySQL `qa_logs` 表。

## 工单辅助（可选 Workflow）

提示词见 `dify/prompts/ticket_system.txt`，输出 JSON 结构化分析。

Python 侧 `work_order_sql.py` 已实现正则分类，Workflow 为加分项。
