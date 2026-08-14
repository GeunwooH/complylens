"""랜딩 페이지 + SEO 테스트 — 메타/OG/JSON-LD, robots/sitemap, 블로그."""
from __future__ import annotations

from starlette.testclient import TestClient

from complylens.web.app import app

client = TestClient(app)


def test_landing_serves_with_key_marketing_elements() -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.text
    for needle in [
        "LL144 Bias Audit",
        "$1,500",
        "72 hours",
        "Start your audit",
        "automated employment decision tool",
    ]:
        assert needle in body


def test_landing_links_directly_to_sanitized_csv_offer() -> None:
    body = client.get("/").text
    assert (
        'href="/kmong-csv-profile.html?source=homepage&amp;product=kmong-csv-profile"'
        in body
    )
    assert "개인정보 제거 CSV" in body
    assert "300,000원" in body


def test_landing_has_seo_meta_and_structured_data() -> None:
    body = client.get("/").text
    for needle in [
        '<meta name="description"',
        'property="og:title"',
        'property="og:description"',
        'application/ld+json',
        "ProfessionalService",
        'rel="canonical"',
    ]:
        assert needle in body


def test_landing_has_target_keywords() -> None:
    body = client.get("/").text.casefold()
    for keyword in ["ll144 bias audit", "aedt bias audit", "nyc ai hiring law compliance"]:
        assert keyword in body


def test_internal_plan_is_not_public() -> None:
    assert client.get("/plan.html").status_code in (404, 410)
    assert 'href="/plan.html"' not in client.get("/").text


def test_landing_canonical_and_scope_are_production_safe() -> None:
    body = client.get("/").text
    assert 'rel="canonical" href="https://html.npopo.com/"' in body
    assert "complylens.example" not in body
    assert "Independent auditor sign-off" in body
    assert "compliant analysis starting at $299" not in body


def test_quiz_success_copy_makes_no_email_promise() -> None:
    body = client.get("/quiz.html").text
    assert "checklist is on its way" not in body
    assert "/aedt-compliance-checklist.html" in body


def test_privacy_discloses_leads_and_analytics() -> None:
    body = client.get("/privacy.html").text.casefold()
    for needle in ["page paths", "referrer", "lead", "quiz result"]:
        assert needle in body


def test_robots_and_sitemap_served() -> None:
    robots = client.get("/robots.txt")
    assert robots.status_code == 200
    assert "Sitemap: https://html.npopo.com/sitemap.xml" in robots.text
    assert "complylens.example" not in robots.text
    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200 and "html.npopo.com" in sitemap.text
    assert "/plan.html" not in sitemap.text


def test_blog_cites_comptroller_findings() -> None:
    resp = client.get("/blog/ll144-enforcement-2026.html")
    assert resp.status_code == 200
    for needle in ["17 instances of potential non-compliance", "2024-N-6", "ineffective"]:
        assert needle in resp.text


def test_csv_profile_page_has_conversion_elements() -> None:
    resp = client.get("/kmong-csv-profile.html")
    assert resp.status_code == 200
    body = resp.text
    for needle in [
        "1. CSV 제출",          # 3단계 프로세스
        "2. 프로파일 작성",
        "3. 납품",
        "크몽 리뷰",             # 신뢰 신호
        "보내지 마세요",          # PII 경계
        "주민등록번호",
    ]:
        assert needle in body
