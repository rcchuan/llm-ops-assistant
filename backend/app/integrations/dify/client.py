import httpx

from app.integrations.dify.exceptions import (
    DifyConfigurationError,
    DifyInvalidResponseError,
    DifyTimeoutError,
    DifyUnavailableError,
)
from app.integrations.dify.schemas import DifyChatResult, RetrieverResource


RESOURCE_CONTENT_LIMIT = 400


class DifyClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: int,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not base_url.strip() or not api_key or timeout_seconds <= 0:
            raise DifyConfigurationError("问答服务配置无效")
        self._client = httpx.Client(
            base_url=f"{base_url.rstrip('/')}/",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout_seconds,
            transport=transport,
        )

    def __enter__(self) -> "DifyClient":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def chat(
        self,
        *,
        question: str,
        user_id: int,
        conversation_id: str | None,
    ) -> DifyChatResult:
        try:
            response = self._client.post(
                "chat-messages",
                json={
                    "inputs": {},
                    "query": question,
                    "response_mode": "blocking",
                    "conversation_id": conversation_id or "",
                    "user": f"user-{user_id}",
                },
            )
        except httpx.TimeoutException:
            raise DifyTimeoutError("问答服务请求超时") from None
        except httpx.HTTPError:
            raise DifyUnavailableError("问答服务暂时不可用") from None

        if response.status_code in {401, 403}:
            raise DifyConfigurationError("问答服务配置或认证失败")
        if response.is_error:
            raise DifyUnavailableError("问答服务暂时不可用")
        try:
            payload = response.json()
        except ValueError:
            raise DifyInvalidResponseError("问答服务返回数据无效") from None
        if not isinstance(payload, dict):
            raise DifyInvalidResponseError("问答服务返回数据无效")

        answer = payload.get("answer")
        dify_conversation_id = payload.get("conversation_id")
        if not isinstance(answer, str) or not answer.strip():
            raise DifyInvalidResponseError("问答服务未返回有效回答")
        if not isinstance(dify_conversation_id, str) or not dify_conversation_id.strip():
            raise DifyInvalidResponseError("问答服务返回数据不完整")
        message_id = payload.get("message_id")
        if message_id is not None and not isinstance(message_id, str):
            raise DifyInvalidResponseError("问答服务返回数据无效")
        return DifyChatResult(
            answer=answer.strip(),
            conversation_id=dify_conversation_id.strip(),
            message_id=message_id.strip() or None if isinstance(message_id, str) else None,
            resources=_parse_resources(payload),
        )


def _parse_resources(payload: object) -> list[RetrieverResource]:
    if not isinstance(payload, dict):
        return []
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        return []
    raw_resources = metadata.get("retriever_resources")
    if not isinstance(raw_resources, list):
        return []

    resources = []
    for item in raw_resources:
        if not isinstance(item, dict):
            continue
        name = next(
            (
                value.strip()
                for key in ("document_name", "name", "title")
                if isinstance((value := item.get(key)), str) and value.strip()
            ),
            "未命名文档",
        )
        content = item.get("content")
        resources.append(
            RetrieverResource(
                document_name=name,
                content=content.strip()[:RESOURCE_CONTENT_LIMIT]
                if isinstance(content, str)
                else "",
            )
        )
    return resources
