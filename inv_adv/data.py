"""Wczytywanie danych wejściowych oraz pobieranie cen (wejście dla M1-M3)."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd
import yaml

CONFIG_PATH = Path("config.yaml")
PORTFOLIO_PATH = Path("data/portfolio.csv")
PRICE_CACHE = Path("data/prices/latest.csv")
MANUAL_PRICES = Path("data/prices_manual.csv")

REQUIRED_COLUMNS = ["ticker", "quantity", "asset_class", "currency"]


def benchmarks_of(cfg: dict) -> dict:
    """Benchmarki z configu: nowy schemat 'benchmarks' lub legacy 'benchmark'.

    Pierwszy wpis = benchmark główny (kryterium D1, kolumna benchmark_value
    w historii); kolejne są porównawcze. Klucz 'name' opcjonalny (domyślnie
    klucz konfiguracji).
    """
    b = cfg.get("benchmarks")
    if b:
        for key, spec in b.items():
            if not {"ticker", "currency"} <= set(spec):
                raise KeyError(f"benchmark '{key}': wymagane klucze ticker, currency")
        return b
    if "benchmark" in cfg:
        return {"bench": {"name": "Benchmark", **cfg["benchmark"]}}
    raise KeyError("brak sekcji 'benchmarks' (lub legacy 'benchmark') w configu")


def bench_value_column(key: str, primary_key: str) -> str:
    """Kolumna wartości benchmarku w historii; główny = benchmark_value (kompatybilność)."""
    return "benchmark_value" if key == primary_key else f"benchmark_{key}_value"


def load_config(path: Path = CONFIG_PATH) -> dict:
    """config.yaml z walidacją kluczy i sumy targetów."""
    with open(path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    for key in ["base_currency", "drift_threshold_pp",
                "max_turnover_pct", "transaction_cost_pct", "targets"]:
        if key not in cfg:
            raise KeyError(f"{path}: brak klucza '{key}'")
    benchmarks_of(cfg)
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
    """Wszystkie tickery do pobrania: pozycje + benchmarki + pary FX."""
    base = cfg["base_currency"]
    tickers = set(portfolio["ticker"].astype(str))
    currencies = set(portfolio["currency"].astype(str).str.upper())
    for spec in benchmarks_of(cfg).values():
        tickers.add(str(spec["ticker"]))
        currencies.add(str(spec["currency"]).upper())
    for ccy in currencies:
        pair = fx_ticker(ccy, base)
        if pair:
            tickers.add(pair)
    return sorted(tickers)


def apply_manual_overrides(prices: pd.DataFrame,
                           manual: Path = MANUAL_PRICES) -> tuple[pd.DataFrame, list[str]]:
    """Nadpisuje cenę tickerów z opcjonalnego pliku ręcznego (ticker,price).

    Dla pozycji, gdzie Yahoo bywa nieaktualne (np. ETF-y z GPW). Cache zostaje
    nietknięty — nadpisanie działa również w trybie offline. Zwraca (df, nadpisane).
    """
    if not manual.exists():
        return prices, []
    man = pd.read_csv(manual)
    if not {"ticker", "price"} <= set(man.columns):
        raise ValueError(f"{manual}: wymagane kolumny ticker, price")
    prices = prices.copy()
    touched: list[str] = []
    for _, r in man.iterrows():
        mask = prices["ticker"].astype(str) == str(r["ticker"])
        if mask.any():
            prices.loc[mask, "price"] = float(r["price"])
            touched.append(str(r["ticker"]))
    return prices, touched


def fetch_prices(tickers: list[str], offline: bool = False, cache: Path = PRICE_CACHE,
                 manual: Path = MANUAL_PRICES) -> tuple[pd.DataFrame, list[str]]:
    """Ceny (ostatnie zamknięcie) dla tickerów Yahoo.

    Zwraca (DataFrame: ticker, price, fetched_at; lista tickerów z ręcznym
    nadpisaniem ceny). Tryb online zapisuje cache (podstawa trybu offline
    i reprodukowalności protokołów); offline czyta cache i zgłasza błąd,
    gdy brakuje tickera.
    """
    if offline:
        if not cache.exists():
            raise FileNotFoundError(f"{cache}: brak cache — uruchom raz w trybie online")
        df = pd.read_csv(cache)
        missing = sorted(set(tickers) - set(df["ticker"]))
        if missing:
            raise ValueError(f"brak cen w cache dla: {missing}")
        df = df[df["ticker"].isin(tickers)].reset_index(drop=True)
        return apply_manual_overrides(df, manual)

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
    return apply_manual_overrides(df, manual)
