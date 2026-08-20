"""LLM 게이트웨이 — 멀티프로바이더 라우팅, 비-PRC 가드, 환각 게이트."""
from __future__ import annotations

import logging
import os
import re
from collections.abc import Callable
from dataclasses import dataclass

from openai import APIConnectionError, APIError, APITimeoutError, OpenAIError
from openai import OpenAI

_logger = logging.getLogger(__name__)

_UPSTREAM_EXCS: tuple[type[BaseException], ...] = (
    TimeoutError,
    ConnectionError,
    OSError,
    APIConnectionError,
    APITimeoutError,
    APIError,
    OpenAIError,
)

_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")


@dataclass(frozen=True)
class Provider:
    name: str
    base_url: str
    api_key_env: str
    model: str
    jurisdiction: str


class HallucinationDetected(ValueError):
    """LLM 출력에 숫자 리터럴이 포함됨 — 수치는 템플릿에서만 주입."""


class NoProviderAvailable(RuntimeError):
    """활성 프로바이더가 없거나 전부 실패."""


class LLMGateway:
    def __init__(
        self,
        providers: list[Provider],
        order: list[str] | None = None,
        client_factory: Callable[[str, str], OpenAI] | None = None,
    ) -> None:
        self._providers = providers
        self._order = order or [p.name for p in providers]
        factory = client_factory or (lambda base, key: OpenAI(base_url=base, api_key=key))
        self._clients: dict[str, OpenAI] = {}
        for p in providers:
            key = os.environ.get(p.api_key_env)
            if key:
                self._clients[p.name] = factory(p.base_url, key)

    def _active(self, sensitive: bool) -> list[Provider]:
        if sensitive:
            return [p for p in self._providers if p.jurisdiction == "non_prc"]
        return self._providers

    def configured_provider_names(self, sensitive: bool = False) -> tuple[str, ...]:
        """Return configured provider names without exposing keys or making calls."""
        return tuple(
            provider.name
            for provider in self._active(sensitive)
            if provider.name in self._clients
        )

    def complete(self, prompt: str, sensitive: bool = False, max_retries: int = 2) -> str:
        active = [p for p in self._active(sensitive) if p.name in self._clients]
        if not active:
            raise NoProviderAvailable("no client configured for active providers")
        for p in active[: max_retries + 1]:
            client = self._clients[p.name]
            try:
                resp = client.chat.completions.create(
                    model=p.model,
                    messages=[{"role": "user", "content": prompt}],
                )
                return resp.choices[0].message.content or ""
            except _UPSTREAM_EXCS as exc:
                _logger.warning("provider %s failed: %s", p.name, exc)
                continue
        raise NoProviderAvailable("all active providers failed")

    def generate_narrative(self, prompt: str, sensitive: bool = False) -> str:
        text = self.complete(prompt, sensitive=sensitive)
        if _NUMBER_RE.search(text):
            raise HallucinationDetected(
                "LLM output contains numeric literals; numbers must come from the audit JSON"
            )
        return text


def render_report(template: str, numbers: dict[str, object]) -> str:
    for key, value in numbers.items():
        template = template.replace("{{" + key + "}}", str(value))
    if "{{" in template:
        raise ValueError(f"unfilled template placeholders remain: {template[template.index('{{'):][:40]}")
    return template
