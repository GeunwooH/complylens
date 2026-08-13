from __future__ import annotations

from fastapi.testclient import TestClient

from complylens.web.app import app

client = TestClient(app)


def test_kmong_offer_page_exposes_sanitized_csv_cta() -> None:
    response = client.get("/kmong-csv-profile.html")

    assert response.status_code == 200
    assert "300,000원" in response.text
    assert "개인정보 제거 CSV" in response.text
    assert 'id="sanitizedData"' in response.text
    assert 'fetch("/api/leads"' in response.text


def test_kmong_offer_propagates_homepage_attribution() -> None:
    response = client.get("/kmong-csv-profile.html")

    assert response.status_code == 200
    assert 'new URLSearchParams(location.search).get("source")' in response.text
    assert 'source: source.slice(0, 80)' in response.text
    assert 'product: "kmong-csv-profile"' in response.text
    assert 'consent: "customer-confirmed"' in response.text


def test_pricing_page_links_to_kmong_offer() -> None:
    response = client.get("/pricing.html")

    assert response.status_code == 200
    assert '/kmong-csv-profile.html?source=pricing&amp;product=kmong-csv-profile' in response.text
