"""M3 — protokół decyzji i historia + smoke pełnego cyklu (offline)."""
import pandas as pd
import pytest

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


CFG2 = {
    "base_currency": "PLN",
    "targets": {"equity": 0.6, "crypto": 0.4},
    "benchmarks": {
        "spx": {"name": "S&P 500 (PLN)", "ticker": "^GSPC", "currency": "USD"},
        "nasdaq": {"name": "Nasdaq-100 (PLN)", "ticker": "^NDX", "currency": "USD"},
    },
}
PRICES2 = pd.DataFrame({
    "ticker": ["SPY", "BTC-USD", "^GSPC", "^NDX", "USDPLN=X"],
    "price": [100.0, 50000.0, 5000.0, 20000.0, 4.0],
})


def test_append_history_schema_evolution(tmp_path):
    """Nowa kolumna benchmarku -> scalony nagłówek, stare wiersze z NaN."""
    hist = tmp_path / "history.csv"
    append_history(build_snapshot(PORTFOLIO, PRICES, CFG), hist)    # legacy schemat
    append_history(build_snapshot(PORTFOLIO, PRICES2, CFG2), hist)  # + nasdaq
    df = pd.read_csv(hist)
    assert len(df) == 2
    assert list(df.columns)[:3] == ["date", "total_value", "benchmark_value"]
    assert "benchmark_nasdaq_value" in df.columns
    assert pd.isna(df["benchmark_nasdaq_value"].iloc[0])
    assert df["benchmark_nasdaq_value"].iloc[1] == pytest.approx(80_000.0)  # 20000*4


def test_protocol_lists_all_benchmarks(tmp_path):
    snap = build_snapshot(PORTFOLIO, PRICES2, CFG2)
    trades, fired = propose_trades(snap, threshold_pp=5.0, max_turnover_pct=100.0)
    path = write_protocol(snap, trades, fired, "fixtures", base_currency="PLN",
                          out_dir=tmp_path / "decisions",
                          benchmarks=CFG2["benchmarks"])
    text = path.read_text(encoding="utf-8")
    assert "S&P 500 (PLN)" in text
    assert "Nasdaq-100 (PLN)" in text
    assert "80,000.00" in text  # ^NDX * USDPLN w danych wejściowych
