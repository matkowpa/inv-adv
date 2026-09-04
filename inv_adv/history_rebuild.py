"""F1 — historyczne metryki portfela przy założeniu statycznego składu.

Rekonstruuje dzienną serię wartości portfela z bieżących ilości pozycji
(data/portfolio.csv) i historycznych notowań Yahoo (auto_adjust=True — dane
po uwzględnieniu dywidend i splitów). Założenie właściciela: skład portfela
nie zmieniał się w okresie — wynik jest aproksymacją (pomija przeszłe
transakcje i dopłaty).

Użycie:
    python -m inv_adv.history_rebuild --period 1y
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from inv_adv.data import (bench_value_column, benchmarks_of, fx_ticker,
                          load_config, load_portfolio)
from inv_adv.metrics import bench_cols_from_cfg, compute_metrics

REBUILT_PATH = Path("reports/history_rebuilt.csv")
MIN_DIRECT_FRACTION = 0.5  # para bezpośrednia użyteczna, gdy pokrywa >= 50% wierszy


def fetch_history_prices(tickers: list[str], period: str) -> pd.DataFrame:
    """Historyczne close (adjusted) z Yahoo: kolumny = tickery, indeks = data."""
    import yfinance as yf  # leniwy import — testy nie potrzebują sieci

    raw = yf.download(tickers=tickers, period=period, interval="1d",
                      progress=False, auto_adjust=True, threads=False)
    close = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) \
        else raw["Close"].to_frame(name=tickers[0])
    missing = sorted(set(tickers) - set(close.columns))
    if missing:
        raise ValueError(f"Yahoo nie zwróciło historii dla: {missing}")
    # kalendarze giełd się różnią (krypto notowane 7 dni w tygodniu) —
    # unia dat + forward-fill; wiodące NaN obetnie dropna w build_series
    return close.sort_index().ffill()


def collect_history_tickers(portfolio: pd.DataFrame, cfg: dict) -> list[str]:
    """Tickery do pobrania: pozycje + benchmarki + pary FX (bezpośrednie i krzyże USD)."""
    base = str(cfg["base_currency"]).upper()
    tickers: set[str] = set(portfolio["ticker"].astype(str))
    currencies = set(portfolio["currency"].astype(str).str.upper())
    for spec in benchmarks_of(cfg).values():
        tickers.add(str(spec["ticker"]))
        currencies.add(str(spec["currency"]).upper())
    currencies.discard(base)
    for ccy in currencies:
        direct = fx_ticker(ccy, base)
        if direct:
            tickers.add(direct)
        if ccy != "USD":          # krzyż przez USD (fallback przy braku historii pary)
            tickers.add(f"USD{ccy}=X")
        if base != "USD":
            tickers.add(f"USD{base}=X")
    return sorted(tickers)


def _fx_series(currency: str, base: str, close: pd.DataFrame) -> pd.Series:
    """Historyczny kurs currency -> base.

    Preferuje parę bezpośrednią; gdy Yahoo nie ma jej historii lub jest
    szczątkowa (np. SEKPLN=X: 1 dzień) — kurs krzyżowy przez USD:
    CCY->BASE = (BASE/USD) / (CCY/USD).
    """
    if currency == base:
        return pd.Series(1.0, index=close.index)
    direct = fx_ticker(currency, base)
    if direct and direct in close.columns:
        s = close[direct].dropna()
        if len(s) >= MIN_DIRECT_FRACTION * len(close):
            out = close[direct]
            return out / 100.0 if currency == "GBX" else out
    if base == "USD":
        cross = 1.0 / close[f"USD{currency}=X"]
    else:
        cross = close[f"USD{base}=X"] / close[f"USD{currency}=X"]
    if cross.dropna().empty:
        raise ValueError(f"brak historii kursu dla {currency} ({direct})")
    return cross


def build_series(portfolio: pd.DataFrame, close: pd.DataFrame,
                 cfg: dict) -> pd.DataFrame:
    """Dzienna wartość portfela i benchmarku (waluta bazowa), statyczny skład."""
    base = str(cfg["base_currency"]).upper()
    benchmarks = benchmarks_of(cfg)
    primary = next(iter(benchmarks))
    comps: dict[str, pd.Series] = {}
    for _, row in portfolio.iterrows():
        ticker, ccy = str(row["ticker"]), str(row["currency"]).upper()
        comps[f"pos_{ticker}_{ccy}"] = (close[ticker] * _fx_series(ccy, base, close)
                                        * float(row["quantity"]))
    for key, spec in benchmarks.items():
        comps[bench_value_column(key, primary)] = (
            close[str(spec["ticker"])]
            * _fx_series(str(spec["currency"]).upper(), base, close))
    df = pd.DataFrame(comps).dropna()  # wspólne okno czasowe wszystkich serii
    if df.empty:
        raise ValueError("brak wspólnego okna czasowego dla pozycji")
    data = {"date": df.index.strftime("%Y-%m-%dT%H:%M:%S"),
            "total_value": df[[c for c in df.columns if c.startswith("pos_")]].sum(axis=1)}
    for key in benchmarks:
        col = bench_value_column(key, primary)
        data[col] = df[col]
    return pd.DataFrame(data).reset_index(drop=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="inv-adv F1: historyczne metryki portfela (założenie statycznego składu)")
    parser.add_argument("--period", default="1y", help="okres Yahoo: 6mo / 1y / 2y / max")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--portfolio", default="data/portfolio.csv")
    parser.add_argument("--out", default=str(REBUILT_PATH))
    parser.add_argument("--risk-free", type=float, default=0.0)
    args = parser.parse_args(argv)

    cfg = load_config(Path(args.config))
    benchmarks = benchmarks_of(cfg)
    portfolio = load_portfolio(Path(args.portfolio))
    close = fetch_history_prices(collect_history_tickers(portfolio, cfg), args.period)
    series = build_series(portfolio, close, cfg)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    series.to_csv(out, index=False)

    m = compute_metrics(series, risk_free_annual=args.risk_free,
                        bench_cols=bench_cols_from_cfg(benchmarks))
    print(f"Okres: {series['date'].iloc[0][:10]} -> {series['date'].iloc[-1][:10]} "
          f"({len(series)} sesji; założenie: statyczny skład)")
    print(f"Wartość: {series['total_value'].iloc[0]:,.0f} -> "
          f"{series['total_value'].iloc[-1]:,.0f} {cfg['base_currency']}")
    if m is None:
        print("za mało danych")
        return 0
    print(f"n={m.n_points} | {m.days:.0f} dni | rf={args.risk_free:.1%}")
    sides = [("portfel", m.portfolio)] + list(m.benchmarks.items())
    for name, s in sides:
        if s is None:
            print(f"  {name:18s} brak danych (potrzeba 3 punktów)")
            continue
        sh = "n/d" if s.sharpe is None else f"{s.sharpe:.2f}"
        print(f"  {name:18s} wynik {s.total_return:+.1%} | ann {s.annualized_return:+.1%} "
              f"| vol {s.vol_annualized:.1%} | sharpe {sh} | maxDD {s.max_drawdown:.1%}")
    print(f"Seria zapisana: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
