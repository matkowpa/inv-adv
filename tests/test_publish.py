"""Dashboard HTML — render offline na fixture'ach."""
import pandas as pd

from inv_adv.publish import _svg_chart, build_page

CFG = {
    "base_currency": "PLN",
    "targets": {"equity": 0.6, "crypto": 0.4},
    "benchmark": {"ticker": "^GSPC", "currency": "USD"},
}
PORTFOLIO = pd.DataFrame({
    "ticker": ["SPY", "BTC-USD"],
    "quantity": [1.0, 2.0],
    "asset_class": ["equity", "crypto"],
    "currency": ["USD", "USD"],
})
PRICES = pd.DataFrame({
    "ticker": ["SPY", "BTC-USD", "^GSPC", "USDPLN=X"],
    "price": [100.0, 50000.0, 5000.0, 4.0],
})


def make_series():
    return pd.DataFrame({
        "date": ["2026-01-05T00:00:00", "2026-01-06T00:00:00",
                 "2026-01-07T00:00:00"],
        "total_value": [420.0, 430.0, 425.0],
        "benchmark_value": [20000.0, 20100.0, 20050.0],
    })


def test_build_page_contains_sections_and_data():
    html = build_page(CFG, PORTFOLIO, PRICES, make_series(), "2026-09-04 12:00")
    for fragment in ["Pozycje", "Alokacja", "Metryki", "base 100", "<svg",
                     "SPY", "BTC-USD", "400,400.00 PLN", "Nie publikuj"]:
        assert fragment in html, fragment
    # samowystarczalność: zero zewnętrznych skryptów/stylów (działa offline)
    assert "<script" not in html.lower()
    assert "<link " not in html.lower()
    assert "cdn" not in html.lower()


def test_svg_chart_structure_and_bounds():
    svg = _svg_chart(["2026-01-05", "2026-01-06", "2026-01-07"],
                     {"P": [100.0, 110.0, 105.0], "B": [100.0, 101.0, 99.0]})
    assert svg.startswith("<svg")
    assert 'viewBox="0 0 960 340"' in svg
    assert 'points="' in svg
    assert svg.count("<polyline") == 2


def test_svg_chart_empty_dates():
    assert _svg_chart([], {"P": []}) == "<p>brak danych do wykresu</p>"
