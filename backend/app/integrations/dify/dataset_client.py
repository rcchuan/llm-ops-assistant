import httpx

from app.integrations.dify.dataset_exceptions import (
    DifyDatasetConfigurationError,
    DifyDatasetInvalidResponseError,
    DifyDatasetRequestError,
    DifyDatasetUncertainError,
)
from app.integrations.dify.dataset_schemas import DifyDatasetDocumentResult


class DifyDatasetClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        dataset_id: str,
        timeout_seconds: int,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not base_url.strip() or timeout_seconds <= 0:
            raise DifyDatasetConfigurationError("知识同步配置无效")
        self._dataset_id = dataset_id.strip()
        api_key = api_key.strip()
        self._configured = bool(api_key and self._dataset_id)
        self._client = httpx.Client(
            base_url=f"{base_url.rstrip('/')}/",
            headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
            timeout=timeout_seconds,
            transport=transport,
        )

    def __enter__(self) -> "DifyDatasetClient":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def create_text_document(
        self, *, name: str, text: str
    ) -> DifyDatasetDocumentResult:
        if not self._configured:
            raise DifyDatasetConfigurationError("知识同步配置无效")
        try:
            response = self._client.post(
                f"datasets/{self._dataset_id}/document/create-by-text",
                json={
                    "name": name,
                    "text": text,
                    "indexing_technique": "high_quality",
                },
            )
        except httpx.TimeoutException:
            raise DifyDatasetUncertainError("知识同步结果不确定") from None
        except httpx.HTTPError:
            raise DifyDatasetUncertainError("知识同步结果不确定") from None

        if response.status_code in {401, 403}:
            raise DifyDatasetConfigurationError("知识同步配置或认证失败")
        if response.is_error:
            raise DifyDatasetRequestError("Dify 未接受知识文档")
        try:
            payload = response.json()
        except ValueError:
            raise DifyDatasetInvalidResponseError("知识同步返回数据无效") from None
        if not isinstance(payload, dict):
            raise DifyDatasetInvalidResponseError("知识同步返回数据无效")
        document = payload.get("document")
        document_id = document.get("id") if isinstance(document, dict) else None
        if not isinstance(document_id, str) or not document_id.strip():
            raise DifyDatasetInvalidResponseError("知识同步未返回文档 ID")
        return DifyDatasetDocumentResult(document_id=document_id.strip())
