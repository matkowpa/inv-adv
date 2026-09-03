"""M1 — matematyka migawki, alokacji i dryfu (offline, fixture'y)."""
import pandas as pd
import pytest

from inv_adv.data import fx_rate
from inv_adv.review import build_snapshot

CFG = {
    "base_currency": "PLN",
    "targets": {"equity": 0.6, "crypto": 0.4},
    "benchmark": {"ticker": "^GSPC", "currency": "USD"},
}


def make_portfolio():
    return pd.DataFrame({
        "ticker": ["SPY", "BTC-USD"],
        "quantity": [1.0, 2.0],
        "asset_class": ["equity", "crypto"],
        "currency": ["USD", "USD"],
    })


def make_prices():
    return pd.DataFrame({
        "ticker": ["SPY", "BTC-USD", "^GSPC", "USDPLN=X"],
        "price": [100.0, 50000.0, 5000.0, 4.0],
    })


def test_fx_rate():
    prices = pd.DataFrame({"ticker": ["GBPPLN=X", "USDPLN=X"], "price": [5.0, 4.0]})
    assert fx_rate("PLN", "PLN", prices) == 1.0
    assert fx_rate("USD", "PLN", prices) == pytest.approx(4.0)
    assert fx_rate("GBX", "PLN", prices) == pytest.approx(0.05)  # GBX = 1/100 GBP


def test_snapshot_values_and_fx():
    snap = build_snapshot(make_portfolio(), make_prices(), CFG)
    # SPY: 100 * 1 * 4 = 400; BTC: 50000 * 2 * 4 = 400000 -> total 400400
    assert snap.total_value == pytest.approx(400_400.0)
    assert snap.allocation["equity"] == pytest.approx(400.0 / 400_400.0)
    assert snap.allocation["crypto"] == pytest.approx(400_000.0 / 400_400.0)
    assert snap.benchmark_value == pytest.approx(20_000.0)  # 5000 USD * 4
    assert snap.drift_pp["equity"] == pytest.approx((400.0 / 400_400.0 - 0.6) * 100)


def test_missing_class_gets_zero_share():
    pf = make_portfolio().drop(index=1)  # tylko equity, target crypto = 0.4
    snap = build_snapshot(pf, make_prices(), CFG)
    assert snap.allocation["crypto"] == pytest.approx(0.0)
    assert snap.drift_pp["crypto"] == pytest.approx(-40.0)


def test_unknown_class_raises():
    pf = make_portfolio()
    pf.loc[0, "asset_class"] = "gold"
    with pytest.raises(ValueError, match="gold"):
        build_snapshot(pf, make_prices(), CFG)


def test_missing_price_raises():
    with pytest.raises(ValueError, match="SPY"):
        build_snapshot(make_portfolio(), make_prices().iloc[1:], CFG)
