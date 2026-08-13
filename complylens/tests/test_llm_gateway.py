"""LLM 게이트웨이 테스트 — 라우팅, 비-PRC 가드, 환각 게이트, 템플릿 렌더."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from complylens.llm.gateway import (
    HallucinationDetected,
    LLMGateway,
    NoProviderAvailable,
    Provider,
    render_report,
)


def _providers() -> list[Provider]:
    return [
        Provider("deepinfra", "https://deepinfra.example", "K1", "flash", "non_prc"),
        Provider("deepseek", "https://api.deepseek.example", "K2", "flash", "prc"),
    ]


def _fake_client(replies: dict[str, str]):
    def create(model, messages):
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=replies.get(model, "")))]
        )

    return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))


def test_sensitive_routes_non_prc_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("K1", "k1")
    monkeypatch.setenv("K2", "k2")
    called: list[str] = []

    def factory(base_url: str, key: str):
        client = _fake_client({"flash": "narrative"})
        orig = client.chat.completions.create

        def create(model, messages):
            called.append(model)
            return orig(model, messages)

        client.chat.completions.create = create
        return client

    gw = LLMGateway(_providers(), client_factory=factory)
    gw.complete("prompt", sensitive=True)
    assert called == ["flash"]  # deepinfra만 (deepseek PRC 제외)


def test_prc_guard_blocks_when_only_prc_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("K2", "k2")
    gw = LLMGateway(_providers(), client_factory=lambda base, key: _fake_client({}))
    with pytest.raises(NoProviderAvailable):
        gw.complete("prompt", sensitive=True)


def test_sensitive_requires_explicit_non_prc_jurisdiction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("K3", "k3")
    providers = [Provider("unverified", "https://unknown.example", "K3", "flash", "unknown")]
    gw = LLMGateway(providers, client_factory=lambda base, key: _fake_client({}))

    with pytest.raises(NoProviderAvailable):
        gw.complete("prompt", sensitive=True)


def test_configured_provider_names_never_expose_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("K1", "secret-value")
    gw = LLMGateway(_providers(), client_factory=lambda base, key: _fake_client({}))

    assert gw.configured_provider_names(sensitive=True) == ("deepinfra",)
    assert "secret-value" not in gw.configured_provider_names(sensitive=True)


def test_hallucination_gate_rejects_numbers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("K1", "k1")
    gw = LLMGateway(_providers(), client_factory=lambda base, key: _fake_client({"flash": "rate was 0.42"}))
    with pytest.raises(HallucinationDetected):
        gw.generate_narrative("write narrative")


def test_hallucination_gate_accepts_clean_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("K1", "k1")
    gw = LLMGateway(_providers(), client_factory=lambda base, key: _fake_client({"flash": "No issues found in this review."}))
    assert gw.generate_narrative("write narrative") == "No issues found in this review."


def test_fallback_on_provider_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("K1", "k1")
    monkeypatch.setenv("K2", "k2")

    def factory(base_url: str, key: str):
        client = _fake_client({"flash": "ok"})
        original = client.chat.completions.create

        def create(model, messages):
            if base_url.startswith("https://deepinfra"):
                raise TimeoutError("down")
            return original(model, messages)

        client.chat.completions.create = create
        return client

    gw = LLMGateway(_providers(), client_factory=factory)
    assert gw.complete("prompt") == "ok"


def test_render_report_injects_exact_numbers() -> None:
    template = (
        "Female selection rate is {{female_rate}}; impact ratio {{female_ratio}} "
        "with {{violations}} violations."
    )
    out = render_report(template, {"female_rate": 0.2, "female_ratio": 0.4, "violations": 1})
    assert out == "Female selection rate is 0.2; impact ratio 0.4 with 1 violations."


def test_render_report_rejects_unfilled_placeholders() -> None:
    with pytest.raises(ValueError):
        render_report("rate {{missing}}", {})
