import json

import httpx
import pytest

from app.integrations.dify.client import DifyClient
from app.integrations.dify.exceptions import (
    DifyConfigurationError,
    DifyInvalidResponseError,
    DifyTimeoutError,
    DifyUnavailableError,
)


def test_dify_client_sends_blocking_chat_and_normalizes_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url == "https://api.dify.ai/v1/chat-messages"
        assert request.headers["Authorization"] == "Bearer test-dify-key"
        assert request.headers["Content-Type"] == "application/json"
        assert json.loads(request.content) == {
            "inputs": {},
            "query": "MySQL 主从延迟怎么排查？",
            "response_mode": "blocking",
            "conversation_id": "",
            "user": "user-7",
        }
        return httpx.Response(
            200,
            json={
                "answer": "先检查复制线程状态。",
                "conversation_id": "conversation-1",
                "message_id": "message-1",
                "metadata": {"retriever_resources": []},
            },
        )

    with DifyClient(
        base_url="https://api.dify.ai/v1/",
        api_key="test-dify-key",
        timeout_seconds=60,
        transport=httpx.MockTransport(handler),
    ) as client:
        result = client.chat(
            question="MySQL 主从延迟怎么排查？",
            user_id=7,
            conversation_id=None,
        )

    assert result.answer == "先检查复制线程状态。"
    assert result.conversation_id == "conversation-1"
    assert result.message_id == "message-1"
    assert result.resources == []


def test_dify_client_passes_conversation_and_simplifies_resources() -> None:
    long_content = "片段" * 250

    def handler(request: httpx.Request) -> httpx.Response:
        assert json.loads(request.content)["conversation_id"] == "conversation-1"
        return httpx.Response(
            200,
            json={
                "answer": "继续检查 relay log。",
                "conversation_id": "conversation-1",
                "metadata": {
                    "retriever_resources": [
                        {
                            "document_name": "MySQL 运维手册",
                            "content": long_content,
                            "dataset_id": "must-not-leak",
                            "score": 0.99,
                        },
                        {"title": "复制排障清单", "content": "检查 SQL 线程。"},
                        {"content": "检查网络。"},
                    ]
                },
            },
        )

    with DifyClient(
        base_url="https://api.dify.ai/v1",
        api_key="test-dify-key",
        timeout_seconds=60,
        transport=httpx.MockTransport(handler),
    ) as client:
        result = client.chat(
            question="下一步看什么？",
            user_id=7,
            conversation_id="conversation-1",
        )

    assert result.message_id is None
    assert [(item.document_name, item.content) for item in result.resources] == [
        ("MySQL 运维手册", long_content[:400]),
        ("复制排障清单", "检查 SQL 线程。"),
        ("未命名文档", "检查网络。"),
    ]


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, json={"answer": " ", "conversation_id": "c-1"}),
        httpx.Response(200, json={"answer": "有效回答"}),
        httpx.Response(200, json={"answer": [], "conversation_id": "c-1"}),
        httpx.Response(200, json={"answer": "有效回答", "conversation_id": 1}),
        httpx.Response(200, content=b"not-json"),
    ],
)
def test_dify_client_rejects_invalid_success_response(response: httpx.Response) -> None:
    with DifyClient(
        base_url="https://api.dify.ai/v1",
        api_key="test-dify-key",
        timeout_seconds=60,
        transport=httpx.MockTransport(lambda _request: response),
    ) as client:
        with pytest.raises(DifyInvalidResponseError):
            client.chat(question="问题", user_id=7, conversation_id=None)


@pytest.mark.parametrize(
    ("status_code", "expected_error"),
    [
        (401, DifyConfigurationError),
        (403, DifyConfigurationError),
        (500, DifyUnavailableError),
        (503, DifyUnavailableError),
    ],
)
def test_dify_client_maps_http_errors_without_leaking_details(
    status_code: int,
    expected_error: type[Exception],
) -> None:
    secret = "super-secret-dify-key"
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status_code, json={"message": "raw-internal-error"})

    with DifyClient(
        base_url="https://api.dify.ai/v1",
        api_key=secret,
        timeout_seconds=60,
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(expected_error) as captured:
            client.chat(question="问题", user_id=7, conversation_id=None)

    assert calls == 1
    assert secret not in str(captured.value)
    assert "raw-internal-error" not in str(captured.value)


@pytest.mark.parametrize(
    ("transport_error", "expected_error"),
    [
        (httpx.ReadTimeout("timeout"), DifyTimeoutError),
        (httpx.ConnectError("network"), DifyUnavailableError),
    ],
)
def test_dify_client_maps_transport_errors(
    transport_error: httpx.HTTPError,
    expected_error: type[Exception],
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        transport_error.request = request
        raise transport_error

    with DifyClient(
        base_url="https://api.dify.ai/v1",
        api_key="test-dify-key",
        timeout_seconds=60,
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(expected_error):
            client.chat(question="问题", user_id=7, conversation_id=None)
