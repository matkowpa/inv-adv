"""F1 — metryki: wartości policzone ręcznie + sekcja w protokole (offline)."""
import pandas as pd
import pytest

from inv_adv.metrics import compute_metrics
from inv_adv.rebalance import propose_trades
from inv_adv.report import write_protocol
from inv_adv.review import build_snapshot

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


def make_history(values, bench, start="2026-01-01", freq_days=7):
    dates = pd.to_datetime(start) + pd.to_timedelta(
        [i * freq_days for i in range(len(values))], unit="D")
    return pd.DataFrame({
        "date": dates.strftime("%Y-%m-%dT%H:%M:%S"),
        "total_value": values,
        "benchmark_value": bench,
    })


def test_metrics_hand_calculated():
    # portfel [100, 110, 99, 104.5], tygodniowo (21 dni):
    # total +4.5%, maxDD -10% (99/110), vol_ann = 0.1050181*sqrt(365/7) = 0.758336,
    # ann = 1.045^(365/21) - 1 = 1.149113, sharpe = 1.149113 / 0.758336 = 1.515309
    hist = make_history([100.0, 110.0, 99.0, 104.5], [200.0, 204.0, 200.0, 208.0])
    m = compute_metrics(hist, risk_free_annual=0.0)
    assert m is not None and m.n_points == 4
    assert m.days == pytest.approx(21.0)
    p = m.portfolio
    assert p.total_return == pytest.approx(0.045)
    assert p.max_drawdown == pytest.approx(-0.10)
    assert p.vol_annualized == pytest.approx(0.758336, rel=1e-4)
    assert p.annualized_return == pytest.approx(1.149113, rel=1e-4)
    assert p.sharpe == pytest.approx(1.515309, rel=1e-4)
    # benchmark [200, 204, 200, 208]: total +4%, maxDD -1.9608% (200/204)
    b = m.benchmark
    assert b.total_return == pytest.approx(0.04)
    assert b.max_drawdown == pytest.approx(200.0 / 204.0 - 1.0)


def test_too_few_points_returns_none():
    assert compute_metrics(make_history([100.0, 102.0], [200.0, 201.0])) is None


def test_protocol_includes_metrics_section(tmp_path):
    snap = build_snapshot(PORTFOLIO, PRICES, CFG)
    trades, fired = propose_trades(snap, threshold_pp=5.0, max_turnover_pct=100.0)
    m = compute_metrics(make_history([100.0, 110.0, 99.0, 104.5],
                                     [200.0, 204.0, 200.0, 208.0]))
    path = write_protocol(snap, trades, fired, "fixtures", base_currency="PLN",
                          out_dir=tmp_path / "decisions", metrics=m)
    text = path.read_text(encoding="utf-8")
    assert "Metryki (F1)" in text
    assert "n=4" in text
    assert "Sharpe" in text
    assert "+4.5%" in text  # wynik okresu portfela


def test_protocol_metrics_none_note(tmp_path):
    snap = build_snapshot(PORTFOLIO, PRICES, CFG)
    trades, fired = propose_trades(snap, threshold_pp=5.0, max_turnover_pct=100.0)
    path = write_protocol(snap, trades, fired, "fixtures", base_currency="PLN",
                          out_dir=tmp_path / "decisions", metrics=None)
    text = path.read_text(encoding="utf-8")
    assert "za mało danych" in text
