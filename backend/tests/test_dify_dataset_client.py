import json

import httpx
import pytest

from app.integrations.dify.dataset_client import DifyDatasetClient
from app.integrations.dify.dataset_exceptions import (
    DifyDatasetConfigurationError,
    DifyDatasetInvalidResponseError,
    DifyDatasetRequestError,
    DifyDatasetUncertainError,
)


def test_dataset_client_creates_text_document_with_verified_contract() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == (
            "https://api.dify.ai/v1/datasets/dataset-1/document/create-by-text"
        )
        assert request.headers["Authorization"] == "Bearer dataset-key"
        assert json.loads(request.content) == {
            "name": "连接池超时 [KE-7]",
            "text": "## 故障现象\n连接超时",
            "indexing_technique": "high_quality",
        }
        return httpx.Response(
            200,
            json={"document": {"id": "document-1"}, "batch": "batch-1"},
        )

    with DifyDatasetClient(
        base_url="https://api.dify.ai/v1/",
        api_key="dataset-key",
        dataset_id="dataset-1",
        timeout_seconds=60,
        transport=httpx.MockTransport(handler),
    ) as client:
        result = client.create_text_document(
            name="连接池超时 [KE-7]",
            text="## 故障现象\n连接超时",
        )

    assert result.document_id == "document-1"


@pytest.mark.parametrize("status_code", [401, 403])
def test_dataset_client_maps_authentication_errors(status_code: int) -> None:
    with DifyDatasetClient(
        base_url="https://api.dify.ai/v1",
        api_key="dataset-key",
        dataset_id="dataset-1",
        timeout_seconds=60,
        transport=httpx.MockTransport(
            lambda _request: httpx.Response(status_code, json={"message": "secret"})
        ),
    ) as client:
        with pytest.raises(DifyDatasetConfigurationError) as captured:
            client.create_text_document(name="标题", text="正文")

    assert "secret" not in str(captured.value)


@pytest.mark.parametrize("status_code", [400, 422, 500, 503])
def test_dataset_client_maps_explicit_http_failures_without_retry(
    status_code: int,
) -> None:
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status_code, json={"message": "internal detail"})

    with DifyDatasetClient(
        base_url="https://api.dify.ai/v1",
        api_key="dataset-key",
        dataset_id="dataset-1",
        timeout_seconds=60,
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(DifyDatasetRequestError) as captured:
            client.create_text_document(name="标题", text="正文")

    assert calls == 1
    assert "internal detail" not in str(captured.value)


@pytest.mark.parametrize(
    "transport_error",
    [httpx.ReadTimeout("timeout"), httpx.ConnectError("network")],
)
def test_dataset_client_marks_timeout_and_network_as_uncertain(
    transport_error: httpx.HTTPError,
) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        transport_error.request = request
        raise transport_error

    with DifyDatasetClient(
        base_url="https://api.dify.ai/v1",
        api_key="dataset-key",
        dataset_id="dataset-1",
        timeout_seconds=60,
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(DifyDatasetUncertainError):
            client.create_text_document(name="标题", text="正文")

    assert calls == 1


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, content=b"not-json"),
        httpx.Response(200, json={}),
        httpx.Response(200, json={"document": {}}),
        httpx.Response(200, json={"document": {"id": " "}}),
    ],
)
def test_dataset_client_rejects_invalid_success_response(
    response: httpx.Response,
) -> None:
    with DifyDatasetClient(
        base_url="https://api.dify.ai/v1",
        api_key="dataset-key",
        dataset_id="dataset-1",
        timeout_seconds=60,
        transport=httpx.MockTransport(lambda _request: response),
    ) as client:
        with pytest.raises(DifyDatasetInvalidResponseError):
            client.create_text_document(name="标题", text="正文")
