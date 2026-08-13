from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from complylens.web import app as app_module
from complylens.web.orders import PRODUCTS, OrderStore

ROOT = Path(__file__).resolve().parents[1]


def test_soc2_playbook_is_catalogued_with_gated_asset() -> None:
    product = PRODUCTS["p6-soc2"]
    product_page = (
        ROOT / "complylens" / "web" / "products" / product["file"]
    ).read_text(encoding="utf-8")

    assert product["name"] == "SOC2 Under $5k Startup Playbook"
    assert product["price_usd"] == 49
    assert product["file"] == "p6-soc2-playbook.html"
    assert (ROOT / "complylens" / "web" / "products" / product["file"]).is_file()
    assert "Startup Evidence Binder v1" in product_page
    assert "not an attestation" in product_page


def test_pricing_page_exposes_soc2_playbook() -> None:
    pricing = (
        ROOT / "complylens" / "web" / "static" / "pricing.html"
    ).read_text(encoding="utf-8")

    assert 'value="p6-soc2"' in pricing
    assert "SOC2 Under $5k Startup Playbook" in pricing
    assert '<main>' in pricing
    assert '<label for="product">Product</label>' in pricing


def test_pricing_result_is_announced_and_checklist_has_og_metadata() -> None:
    pricing = (
        ROOT / "complylens" / "web" / "static" / "pricing.html"
    ).read_text(encoding="utf-8")
    checklist = (
        ROOT
        / "complylens"
        / "web"
        / "static"
        / "blog"
        / "soc2-evidence-gap-check.html"
    ).read_text(encoding="utf-8")

    assert '<div id="result" aria-live="polite"></div>' in pricing
    for property_name in ("og:title", "og:description", "og:type", "og:url"):
        assert f'<meta property="{property_name}"' in checklist


def test_soc2_acquisition_page_is_indexed() -> None:
    blog = (
        ROOT / "complylens" / "web" / "static" / "blog" / "soc2-under-5k.html"
    ).read_text(encoding="utf-8")
    sitemap = (
        ROOT / "complylens" / "web" / "static" / "sitemap.xml"
    ).read_text(encoding="utf-8")

    assert "SOC 2 Under $5k" in blog
    assert (
        'data-preserve-tracking href="/blog/soc2-evidence-gap-check.html"'
        in blog
    )
    assert "https://html.npopo.com/blog/soc2-under-5k.html" in sitemap


def test_evidence_gap_check_routes_to_binder() -> None:
    page = (
        ROOT
        / "complylens"
        / "web"
        / "static"
        / "blog"
        / "soc2-evidence-gap-check.html"
    ).read_text(encoding="utf-8")
    sitemap = (
        ROOT / "complylens" / "web" / "static" / "sitemap.xml"
    ).read_text(encoding="utf-8")

    assert "<main>" in page
    assert "Free SOC 2 Evidence Gap Checklist" in page
    assert (
        'data-preserve-tracking href="/pricing.html?source=evidence-gap-check&product=p6-soc2"'
        in page
    )
    assert (
        "https://html.npopo.com/blog/soc2-evidence-gap-check.html" in sitemap
    )


def test_soc2_campaign_ctas_preselect_binder_on_pricing() -> None:
    pricing = (
        ROOT / "complylens" / "web" / "static" / "pricing.html"
    ).read_text(encoding="utf-8")
    evidence_gap = (
        ROOT
        / "complylens"
        / "web"
        / "static"
        / "blog"
        / "soc2-evidence-gap-check.html"
    ).read_text(encoding="utf-8")
    startup_guide = (
        ROOT
        / "complylens"
        / "web"
        / "static"
        / "blog"
        / "soc2-under-5k.html"
    ).read_text(encoding="utf-8")

    assert (
        'href="/pricing.html?source=evidence-gap-check&product=p6-soc2"'
        in evidence_gap
    )
    assert (
        'href="/pricing.html?source=soc2-under-5k&product=p6-soc2"'
        in startup_guide
    )
    assert 'const requestedProduct = query.get("product");' in pricing
    assert "productSelect.value = requestedProduct;" in pricing


def test_order_persists_source_attribution(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("COMPLYLENS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("BTC_ADDRESS", "bc1qexample")

    response = TestClient(app_module.app).post(
        "/api/orders",
        json={
            "email": "founder@example.com",
            "product_id": "p6-soc2",
            "attribution": {
                "source": "evidence-gap-check",
                "utm_source": "founder",
                "utm_medium": "direct",
                "utm_campaign": "soc2-v1",
            },
        },
    )

    assert response.status_code == 200
    order = OrderStore(tmp_path).get(response.json()["order_id"])
    assert order["attribution"] == {
        "source": "evidence-gap-check",
        "utm_source": "founder",
        "utm_medium": "direct",
        "utm_campaign": "soc2-v1",
    }


def test_order_attribution_rejects_unknown_and_caps_values(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.setenv("COMPLYLENS_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("BTC_ADDRESS", "bc1qexample")
    oversized = "x" * 100

    response = TestClient(app_module.app).post(
        "/api/orders",
        json={
            "email": "founder@example.com",
            "product_id": "p6-soc2",
            "attribution": {
                "utm_source": f"  {oversized}  ",
                "utm_content": oversized,
                "ignored": "not-stored",
            },
        },
    )

    assert response.status_code == 200
    order = OrderStore(tmp_path).get(response.json()["order_id"])
    assert order["attribution"] == {
        "utm_source": oversized[:80],
        "utm_content": oversized[:80],
    }
