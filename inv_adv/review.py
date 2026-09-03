"""M1 — przegląd portfela: migawka, alokacja per klasa, dryf vs targety."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .data import fx_rate


@dataclass
class Snapshot:
    positions: pd.DataFrame        # ticker, quantity, currency, asset_class, price, fx_rate, value_base
    total_value: float             # wartość portfela w walucie bazowej
    allocation: dict               # klasa -> udział (0..1)
    drift_pp: dict                 # klasa -> dryf w p.p. = (udział - target) * 100
    benchmark_value: float         # wartość 1 jednostki benchmarku w walucie bazowej
    targets: dict                  # klasa -> target udziału


def build_snapshot(portfolio: pd.DataFrame, prices: pd.DataFrame, cfg: dict) -> Snapshot:
    base = cfg["base_currency"]
    price_of = dict(zip(prices["ticker"].astype(str), prices["price"].astype(float)))

    pos = portfolio.copy()
    pos["ticker"] = pos["ticker"].astype(str)
    pos["currency"] = pos["currency"].astype(str).str.upper()
    pos["price"] = pos["ticker"].map(price_of)
    if pos["price"].isna().any():
        missing = sorted(pos.loc[pos["price"].isna(), "ticker"])
        raise ValueError(f"brak cen dla pozycji: {missing}")
    pos["fx_rate"] = pos["currency"].apply(lambda c: fx_rate(c, base, prices))
    pos["value_base"] = pos["price"] * pos["quantity"] * pos["fx_rate"]

    total = float(pos["value_base"].sum())
    if total <= 0:
        raise ValueError("wartość portfela musi być > 0")

    targets = cfg["targets"]
    unknown = set(pos["asset_class"]) - set(targets)
    if unknown:
        raise ValueError(f"klasy aktywów bez targetu w config.yaml: {sorted(unknown)}")

    allocation = (pos.groupby("asset_class")["value_base"].sum() / total) \
        .reindex(targets.keys(), fill_value=0.0).astype(float)

    bench = cfg["benchmark"]
    bench_price = price_of[str(bench["ticker"])]
    bench_fx = fx_rate(str(bench["currency"]).upper(), base, prices)

    drift_pp = {cls: (allocation[cls] - targets[cls]) * 100 for cls in targets}
    return Snapshot(positions=pos, total_value=total, allocation=allocation.to_dict(),
                    drift_pp=drift_pp, benchmark_value=bench_price * bench_fx,
                    targets=dict(targets))
