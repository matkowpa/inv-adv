"""Wczytywanie danych wejściowych oraz pobieranie cen (wejście dla M1-M3)."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
import yaml

CONFIG_PATH = Path("config.yaml")
PORTFOLIO_PATH = Path("data/portfolio.csv")
PRICE_CACHE = Path("data/prices/latest.csv")

REQUIRED_COLUMNS = ["ticker", "quantity", "asset_class", "currency"]


def load_config(path: Path = CONFIG_PATH) -> dict:
    """config.yaml z walidacją kluczy i sumy targetów."""
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    for key in ["base_currency", "benchmark", "drift_threshold_pp",
                "max_turnover_pct", "transaction_cost_pct", "targets"]:
        if key not in cfg:
            raise KeyError(f"{path}: brak klucza '{key}'")
    if abs(sum(cfg["targets"].values()) - 1.0) > 1e-9:
        raise ValueError(f"{path}: targety muszą sumować się do 1.0")
    return cfg


def load_portfolio(path: Path = PORTFOLIO_PATH) -> pd.DataFrame:
    """Pozycje portfela z walidacją kolumn i ilości."""
    pf = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in pf.columns]
    if missing:
        raise ValueError(f"{path}: brak kolumn {missing}")
    pf["quantity"] = pd.to_numeric(pf["quantity"], errors="raise")
    if (pf["quantity"] <= 0).any():
        raise ValueError(f"{path}: quantity musi być > 0")
    return pf


def fx_ticker(currency: str, base: str) -> str | None:
    """Ticker pary FX Yahoo dla waluty; None, gdy waluta = bazowa. GBX = 1/100 GBP."""
    if currency.upper() == base.upper():
        return None
    norm = "GBP" if currency.upper() == "GBX" else currency.upper()
    return f"{norm}{base.upper()}=X"


def fx_rate(currency: str, base: str, prices: pd.DataFrame) -> float:
    """Kurs currency -> base z pobranych par FX; GBX = 1/100 GBP; ta sama waluta = 1.0."""
    pair = fx_ticker(currency, base)
    if pair is None:
        return 1.0
    row = prices.loc[prices["ticker"] == pair, "price"]
    if row.empty:
        raise ValueError(f"brak kursu FX dla {currency} ({pair})")
    rate = float(row.iloc[0])
    return rate / 100.0 if currency.upper() == "GBX" else rate


def collect_tickers(portfolio: pd.DataFrame, cfg: dict) -> list[str]:
    """Wszystkie tickery do pobrania: pozycje + benchmark + pary FX."""
    base = cfg["base_currency"]
    tickers = set(portfolio["ticker"].astype(str))
    bench = cfg["benchmark"]
    tickers.add(str(bench["ticker"]))
    currencies = set(portfolio["currency"].astype(str).str.upper())
    currencies.add(str(bench["currency"]).upper())
    for ccy in currencies:
        pair = fx_ticker(ccy, base)
        if pair:
            tickers.add(pair)
    return sorted(tickers)


def fetch_prices(tickers: list[str], offline: bool = False,
                 cache: Path = PRICE_CACHE) -> pd.DataFrame:
    """Ceny (ostatnie zamknięcie) dla tickerów Yahoo.

    Zwraca DataFrame: ticker, price, fetched_at (UTC). Tryb online zapisuje cache
    (podstawa trybu offline i reprodukowalności protokołów); offline czyta cache
    i zgłasza błąd, gdy brakuje tickera.
    """
    if offline:
        if not cache.exists():
            raise FileNotFoundError(f"{cache}: brak cache — uruchom raz w trybie online")
        df = pd.read_csv(cache)
        missing = sorted(set(tickers) - set(df["ticker"]))
        if missing:
            raise ValueError(f"brak cen w cache dla: {missing}")
        return df[df["ticker"].isin(tickers)].reset_index(drop=True)

    import yfinance as yf  # import leniwy — testy nie potrzebują sieci

    raw = yf.download(tickers=tickers, period="5d", progress=False, auto_adjust=True,
                      threads=False)  # sekwencyjnie — omija 'database is locked' cache yfinance
    if isinstance(raw.columns, pd.MultiIndex):
        close = raw["Close"]
    else:  # pojedynczy ticker — kolumny bez poziomu tickera
        close = raw["Close"].to_frame(name=tickers[0])

    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    rows = []
    for t in tickers:
        series = close[t].dropna() if t in close.columns else pd.Series(dtype=float)
        if series.empty:
            raise ValueError(f"Yahoo nie zwróciło ceny dla: {t}")
        rows.append({"ticker": t, "price": float(series.iloc[-1]), "fetched_at": now})

    df = pd.DataFrame(rows)
    cache.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(cache, index=False)
    return df
