from pathlib import Path

PRICING_PAGE = Path(__file__).parents[1] / "complylens" / "web" / "static" / "pricing.html"


def test_pricing_page_exposes_hosted_checkout_states() -> None:
    html = PRICING_PAGE.read_text(encoding="utf-8")

    assert 'id="paymentStatus"' in html
    assert 'id="paymentStatus" class="info"' in html
    assert 'fetch("/api/payment-mode")' in html
    assert "data.payment_method === \"stripe\"" in html
    assert "data.checkout_url" in html
    assert 'query.get("payment")' in html
    assert 'paymentState !== "success"' in html
    assert 'paymentState === "cancel"' in html
    assert "Try again or use the invoice option below." in html
    assert "Payment method is temporarily unavailable." in html
    assert "submitButton.disabled = true" in html
    assert "Payment received. Verifying your order..." in html
    assert "Payment return is missing an order reference." in html
    assert "Payment confirmation failed:" in html
    assert "Payment in BTC." not in html
