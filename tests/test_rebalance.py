"""M2 — reguła progowa R1 i limit obrotu R2 (deterministyczne, offline)."""
import pandas as pd
import pytest

from inv_adv.rebalance import RULE_BAND, RULE_CAP, propose_trades
from inv_adv.review import Snapshot


def make_snapshot(allocation, targets, total=100_000.0):
    positions = pd.DataFrame({
        "ticker": list(allocation),
        "quantity": [1.0] * len(allocation),
        "asset_class": list(allocation),
        "currency": ["PLN"] * len(allocation),
        "price": [1.0] * len(allocation),
        "fx_rate": [1.0] * len(allocation),
        "value_base": [allocation[k] * total for k in allocation],
    })
    drift = {k: (allocation[k] - targets[k]) * 100 for k in targets}
    return Snapshot(positions=positions, total_value=total, allocation=dict(allocation),
                    drift_pp=drift, benchmark_value=0.0, targets=dict(targets))


def test_no_trade_within_band():
    snap = make_snapshot({"a": 0.54, "b": 0.46}, {"a": 0.5, "b": 0.5})
    trades, fired = propose_trades(snap, threshold_pp=5.0, max_turnover_pct=20.0)
    assert trades == []
    assert fired == []


def test_trade_to_target_when_breached():
    snap = make_snapshot({"a": 0.56, "b": 0.44}, {"a": 0.5, "b": 0.5})
    trades, fired = propose_trades(snap, threshold_pp=5.0, max_turnover_pct=20.0)
    assert any(r.startswith(RULE_BAND) for r in fired)
    assert len(trades) == 2
    sell = [t for t in trades if t.direction == "SELL"][0]
    buy = [t for t in trades if t.direction == "BUY"][0]
    # a: 0.56 -> 0.50 => sprzedaż 0.06 * 100000 = 6000; b: kupno 6000
    assert sell.amount == pytest.approx(6_000.0)
    assert buy.amount == pytest.approx(6_000.0)
    assert sell.asset_class == "a" and buy.asset_class == "b"


def test_order_by_abs_drift():
    snap = make_snapshot({"a": 0.68, "b": 0.30, "c": 0.02},
                         {"a": 0.6, "b": 0.4, "c": 0.0})
    trades, fired = propose_trades(snap, threshold_pp=5.0, max_turnover_pct=100.0)
    assert [t.asset_class for t in trades][0] == "b"  # dryf -10 p.p. przed +8 p.p.
    assert sum(r.startswith(RULE_BAND) for r in fired) == 2


def test_turnover_cap_scales_proportionally():
    snap = make_snapshot({"a": 0.6, "b": 0.4}, {"a": 0.4, "b": 0.6})
    trades, fired = propose_trades(snap, threshold_pp=5.0, max_turnover_pct=10.0)
    assert any(r.startswith(RULE_CAP) for r in fired)
    # obrót 40% > limit 10% -> przeskalowanie x0.25 => razem 10% wartości portfela
    assert sum(t.amount for t in trades) == pytest.approx(0.10 * 100_000.0)


def test_deterministic():
    snap = make_snapshot({"a": 0.60, "b": 0.40}, {"a": 0.4, "b": 0.6})
    t1, f1 = propose_trades(snap, 5.0, 100.0)
    t2, f2 = propose_trades(snap, 5.0, 100.0)
    assert [(t.ticker, t.direction, round(t.amount, 9)) for t in t1] == \
           [(t.ticker, t.direction, round(t.amount, 9)) for t in t2]
    assert f1 == f2
