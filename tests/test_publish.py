"""Dashboard HTML — render offline na fixture'ach."""
import pandas as pd

from inv_adv.publish import _svg_chart, build_page

CFG = {
    "base_currency": "PLN",
    "targets": {"equity": 0.6, "crypto": 0.4},
    "benchmarks": {
        "spx": {"name": "S&P 500 (PLN)", "ticker": "^GSPC", "currency": "USD"},
        "nasdaq": {"name": "Nasdaq-100 (PLN)", "ticker": "^NDX", "currency": "USD"},
    },
}
PORTFOLIO = pd.DataFrame({
    "ticker": ["SPY", "BTC-USD"],
    "quantity": [1.0, 2.0],
    "asset_class": ["equity", "crypto"],
    "currency": ["USD", "USD"],
})
PRICES = pd.DataFrame({
    "ticker": ["SPY", "BTC-USD", "^GSPC", "^NDX", "USDPLN=X"],
    "price": [100.0, 50000.0, 5000.0, 20000.0, 4.0],
})


def make_series():
    return pd.DataFrame({
        "date": ["2026-01-05T00:00:00", "2026-01-06T00:00:00",
                 "2026-01-07T00:00:00"],
        "total_value": [420.0, 430.0, 425.0],
        "benchmark_value": [20000.0, 20100.0, 20050.0],
        "benchmark_nasdaq_value": [50000.0, 50500.0, 50300.0],
    })


def test_build_page_contains_sections_and_data():
    html = build_page(CFG, PORTFOLIO, PRICES, make_series(), "2026-09-04 12:00")
    for fragment in ["Pozycje", "Alokacja", "Metryki", "base 100", "<svg",
                     "SPY", "BTC-USD", "400,400.00 PLN", "Nie publikuj",
                     "Nasdaq-100 (PLN)"]:
        assert fragment in html, fragment
    assert html.count("<polyline") == 3  # portfel + 2 benchmarki
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
