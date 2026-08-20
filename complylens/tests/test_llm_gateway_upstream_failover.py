"""회귀: 업스트림이 OpenAI SDK 예외로 실패해도 다음 provider로 failover 되어야 한다.

배경: 게이트웨이가 TimeoutError/ConnectionError/OSError만 잡으면
OpenAI SDK가 던지는 APIConnectionError / APITimeoutError / APIError 등은
잡히지 않아 단일 업스트림 장애가 전체 요청 실패(500)로 번진다.
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import MagicMock

from httpx import Request
from openai import APIConnectionError, APIError, APITimeoutError

from complylens.llm.gateway import LLMGateway, Provider


def _provider(name: str) -> Provider:
    return Provider(
        name=name,
        base_url="https://x.example",
        api_key_env="TEST_GATEWAY_KEY",
        model="m",
        jurisdiction="non_prc",
    )


def _req() -> Request:
    return Request("POST", "https://x.example/v1/chat/completions")


def test_api_connection_error_fails_over() -> None:
    os.environ["TEST_GATEWAY_KEY"] = "dummy"
    req = _req()
    calls: dict[str, int] = {"n": 0}

    def factory(base_url: str, key: str) -> MagicMock:
        m = MagicMock()

        def create(*, model: str, messages: list[dict[str, str]]):  # noqa: ARG001
            calls["n"] += 1
            if calls["n"] == 1:
                raise APIConnectionError(request=req)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok-2"))])

        m.chat.completions.create = create
        return m

    gw = LLMGateway([_provider("p1"), _provider("p2")], client_factory=factory)  # type: ignore[arg-type]
    assert gw.complete("hi") == "ok-2"
    assert calls["n"] == 2


def test_api_timeout_error_fails_over() -> None:
    os.environ["TEST_GATEWAY_KEY"] = "dummy"
    req = _req()
    calls: dict[str, int] = {"n": 0}

    def factory(base_url: str, key: str) -> MagicMock:
        m = MagicMock()

        def create(*, model: str, messages: list[dict[str, str]]):  # noqa: ARG001
            calls["n"] += 1
            if calls["n"] == 1:
                raise APITimeoutError(request=req)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok-2"))])

        m.chat.completions.create = create
        return m

    gw = LLMGateway([_provider("p1"), _provider("p2")], client_factory=factory)  # type: ignore[arg-type]
    assert gw.complete("hi") == "ok-2"


def test_api_error_fails_over() -> None:
    os.environ["TEST_GATEWAY_KEY"] = "dummy"
    req = _req()
    calls: dict[str, int] = {"n": 0}

    def factory(base_url: str, key: str) -> MagicMock:
        m = MagicMock()

        def create(*, model: str, messages: list[dict[str, str]]):  # noqa: ARG001
            calls["n"] += 1
            if calls["n"] == 1:
                raise APIError("upstream 500", request=req, body=None)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok-2"))])

        m.chat.completions.create = create
        return m

    gw = LLMGateway([_provider("p1"), _provider("p2")], client_factory=factory)  # type: ignore[arg-type]
    assert gw.complete("hi") == "ok-2"


def test_non_upstream_error_is_not_swallowed() -> None:
    os.environ["TEST_GATEWAY_KEY"] = "dummy"

    def factory(base_url: str, key: str) -> MagicMock:
        m = MagicMock()

        def create(*, model: str, messages: list[dict[str, str]]):  # noqa: ARG001
            raise ValueError("not an upstream error")

        m.chat.completions.create = create
        return m

    gw = LLMGateway([_provider("p1")], client_factory=factory)  # type: ignore[arg-type]
    try:
        gw.complete("hi")
        raise AssertionError("ValueError should propagate")
    except ValueError as exc:
        assert "not an upstream error" in str(exc)
