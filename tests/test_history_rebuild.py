"""F1 — rekonstrukcja serii historycznej (offline, fixture'y)."""
import pandas as pd
import pytest

from inv_adv.history_rebuild import build_series

CFG = {
    "base_currency": "PLN",
    "targets": {"equity_us": 1.0},
    "benchmark": {"ticker": "^GSPC", "currency": "USD"},
}
PORTFOLIO = pd.DataFrame({
    "ticker": ["A", "B"],
    "quantity": [1.0, 2.0],
    "asset_class": ["equity_us", "equity_us"],
    "currency": ["USD", "PLN"],
})


def make_close(leading_gap: bool = False):
    idx = pd.date_range("2026-01-05", periods=4, freq="D")
    a = [100.0, 110.0, 99.0, 104.5]
    if leading_gap:
        a = [None] + a[:3]  # brak kwotowania w pierwszym dniu
    return pd.DataFrame({
        "A": a,
        "B": [10.0, 10.0, 11.0, 11.0],
        "^GSPC": [5000.0, 5100.0, 4950.0, 5020.0],
        "USDPLN=X": [4.0, 4.0, 4.0, 4.0],
    }, index=idx)


def test_build_series_values_and_fx():
    series = build_series(PORTFOLIO, make_close(), CFG)
    # A*USDPLN + 2*B: [400+20, 440+20, 396+22, 418+22] = [420, 460, 418, 440]
    assert series["total_value"].tolist() == pytest.approx(
        [420.0, 460.0, 418.0, 440.0])
    # benchmark: ^GSPC * USDPLN
    assert series["benchmark_value"].tolist() == pytest.approx(
        [20000.0, 20400.0, 19800.0, 20080.0])
    assert series["date"].iloc[0] == "2026-01-05T00:00:00"


def test_leading_gap_trims_common_window():
    series = build_series(PORTFOLIO, make_close(leading_gap=True), CFG)
    assert len(series) == 3
    # B w drugim rzędzie = 11: [100*4+20, 110*4+22, 99*4+22]
    assert series["total_value"].tolist() == pytest.approx([420.0, 462.0, 418.0])


def test_fx_cross_via_usd_when_direct_pair_missing():
    from inv_adv.history_rebuild import _fx_series
    idx = pd.date_range("2026-01-05", periods=3, freq="D")
    close = pd.DataFrame({
        "USDPLN=X": [4.0, 4.0, 4.0],
        "USDSEK=X": [10.0, 10.5, 11.0],
    }, index=idx)
    s = _fx_series("SEK", "PLN", close)
    # SEK->PLN = (PLN/USD) / (SEK/USD)
    assert s.tolist() == pytest.approx([0.4, 4.0 / 10.5, 4.0 / 11.0])


def test_build_series_sek_via_cross():
    idx = pd.date_range("2026-01-05", periods=3, freq="D")
    close = pd.DataFrame({
        "INTRUM.ST": [10.0, 10.5, 11.0],
        "USDPLN=X": [4.0, 4.0, 4.0],
        "USDSEK=X": [10.0, 10.5, 11.0],
        "^GSPC": [5000.0, 5000.0, 5000.0],
    }, index=idx)
    pf = pd.DataFrame({
        "ticker": ["INTRUM.ST"], "quantity": [1.0],
        "asset_class": ["equity_single"], "currency": ["SEK"],
    })
    series = build_series(pf, close, CFG)
    # 10*0.4 = 4; 10.5*(4/10.5) = 4; 11*(4/11) = 4
    assert series["total_value"].tolist() == pytest.approx([4.0, 4.0, 4.0])
    assert series["benchmark_value"].tolist() == pytest.approx([20000.0, 20000.0, 20000.0])


def test_rebuilt_series_feeds_metrics():
    from inv_adv.metrics import compute_metrics
    series = build_series(PORTFOLIO, make_close(), CFG)
    m = compute_metrics(series)
    assert m is not None and m.n_points == 4
    assert m.portfolio.total_return == pytest.approx(440.0 / 420.0 - 1.0)
    assert m.portfolio.max_drawdown == pytest.approx(418.0 / 460.0 - 1.0)
    assert m.benchmark.total_return == pytest.approx(0.004)
