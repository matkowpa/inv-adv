"""M3 — protokół decyzji i historia + smoke pełnego cyklu (offline)."""
import pandas as pd

from inv_adv.rebalance import propose_trades
from inv_adv.report import append_history, write_protocol
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


def test_full_cycle_offline(tmp_path):
    snap = build_snapshot(PORTFOLIO, PRICES, CFG)
    trades, fired = propose_trades(snap, threshold_pp=5.0, max_turnover_pct=100.0)

    path = write_protocol(snap, trades, fired, "fixtures testowe",
                          base_currency="PLN", out_dir=tmp_path / "decisions")
    text = path.read_text(encoding="utf-8")
    for fragment in ["Protokół decyzji", "Pozycje (M1)", "Migawka klas (M1)",
                     "Reguły (M2)", "Proponowane transakcje (M2)", "Wyjątki ręczne (D3)"]:
        assert fragment in text, fragment

    hist = tmp_path / "history.csv"
    append_history(snap, hist)
    append_history(snap, hist)  # drugi run dopisuje wiersz
    df = pd.read_csv(hist)
    assert len(df) == 2
    assert {"date", "total_value", "benchmark_value",
            "share_equity", "share_crypto"} <= set(df.columns)
    assert df["total_value"].iloc[0] == df["total_value"].iloc[1]
