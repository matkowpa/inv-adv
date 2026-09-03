"""F1 — metryki wydajności i ryzyka z historii snapshotów (reports/history.csv)."""
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

HISTORY_PATH = Path("reports/history.csv")
MIN_POINTS = 3  # < 3 punktów => brak miar ryzyka (protokół pokazuje adnotację)


@dataclass
class SideMetrics:
    total_return: float        # łączny wynik za okres (ułamek)
    annualized_return: float   # annualizowany (ułamek)
    vol_annualized: float      # zmienność roczna (ułamek)
    sharpe: float | None       # (ann - rf) / vol; None gdy vol = 0
    max_drawdown: float        # maks. obsunięcie od szczytu (ułamek, <= 0)


@dataclass
class Metrics:
    n_points: int
    days: float                # dni od pierwszego do ostatniego punktu
    portfolio: SideMetrics
    benchmark: SideMetrics
    risk_free_annual: float


def read_history(path: Path = HISTORY_PATH) -> pd.DataFrame:
    return pd.read_csv(path)


def _side_metrics(values: list[float], intervals_per_year: float, days: float,
                  risk_free_annual: float) -> SideMetrics:
    if values[0] <= 0 or len(values) < 2:
        raise ValueError("seria musi mieć >= 2 punkty i start > 0")
    rets = [values[i] / values[i - 1] - 1.0 for i in range(1, len(values))]
    total = values[-1] / values[0] - 1.0

    peak = values[0]
    dd = 0.0
    for v in values:
        peak = max(peak, v)
        dd = min(dd, v / peak - 1.0)

    mean_r = sum(rets) / len(rets)
    variance = sum((r - mean_r) ** 2 for r in rets) / (len(rets) - 1)
    vol = math.sqrt(variance) * math.sqrt(intervals_per_year)

    base = 1.0 + total
    ann = base ** (365.0 / days) - 1.0 if base > 0 else -1.0
    sharpe = (ann - risk_free_annual) / vol if vol > 0 else None
    return SideMetrics(total, ann, vol, sharpe, dd)


def compute_metrics(history: pd.DataFrame, risk_free_annual: float = 0.0,
                    value_col: str = "total_value",
                    bench_col: str = "benchmark_value") -> Metrics | None:
    """Metryki portfela i benchmarku z historii snapshotów.

    Zwraca None, gdy punktów < MIN_POINTS lub okres < 1 dzień. Annualizacja
    z rzeczywistych odstępów czasu (365 / średnia długość interwału), więc
    nieregularny rytm biegów nie zniekształca wyniku.
    """
    if len(history) < MIN_POINTS:
        return None
    h = history.copy()
    h["date"] = pd.to_datetime(h["date"])
    h = h.sort_values("date").reset_index(drop=True)
    days = (h["date"].iloc[-1] - h["date"].iloc[0]).total_seconds() / 86400.0
    if days < 1:
        return None
    intervals_per_year = 365.0 / (days / (len(h) - 1))
    portfolio = _side_metrics(h[value_col].astype(float).tolist(),
                              intervals_per_year, days, risk_free_annual)
    benchmark = _side_metrics(h[bench_col].astype(float).tolist(),
                              intervals_per_year, days, risk_free_annual)
    return Metrics(n_points=len(h), days=days, portfolio=portfolio,
                   benchmark=benchmark, risk_free_annual=risk_free_annual)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="inv-adv F1: metryki z historii")
    parser.add_argument("--history", default=str(HISTORY_PATH))
    parser.add_argument("--risk-free", type=float, default=0.0)
    args = parser.parse_args(argv)

    m = compute_metrics(read_history(Path(args.history)), args.risk_free)
    if m is None:
        print(f"za mało danych — metryki od {MIN_POINTS} punktów historii")
        return 0
    print(f"n={m.n_points} pkt | okres {m.days:.0f} dni (orientacyjnie przy małym n)")
    for name, s in [("portfel", m.portfolio), ("benchmark", m.benchmark)]:
        sh = "n/d" if s.sharpe is None else f"{s.sharpe:.2f}"
        print(f"  {name:9s} wynik {s.total_return:+.1%} | ann {s.annualized_return:+.1%} "
              f"| vol {s.vol_annualized:.1%} | sharpe {sh} | maxDD {s.max_drawdown:.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
