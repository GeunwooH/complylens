"""랜딩 페이지 + SEO 테스트 — 메타/OG/JSON-LD, robots/sitemap, 블로그."""
from __future__ import annotations

from fastapi.testclient import TestClient

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


def test_robots_and_sitemap_served() -> None:
    robots = client.get("/robots.txt")
    assert robots.status_code == 200 and "Sitemap:" in robots.text
    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200 and "html.npopo.com" in sitemap.text


def test_blog_cites_comptroller_findings() -> None:
    resp = client.get("/blog/ll144-enforcement-2026.html")
    assert resp.status_code == 200
    for needle in ["17 instances of potential non-compliance", "2024-N-6", "ineffective"]:
        assert needle in resp.text
