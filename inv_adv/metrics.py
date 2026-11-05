"""F1 — metryki wydajności i ryzyka z historii snapshotów (reports/history.csv)."""
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .data import bench_value_column

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
    benchmarks: dict           # nazwa wyświetlana -> SideMetrics | None (brak danych)
    risk_free_annual: float
    n_weeks: int = 0           # unikalne tygodnie ISO po filtry run_kind
    run_kinds: tuple[str, ...] = ()

    @property
    def benchmark(self) -> SideMetrics:
        """Benchmark główny (pierwszy w configu) — kompatybilność z wcześniejszym API."""
        return next(iter(self.benchmarks.values()))


def bench_cols_from_cfg(benchmarks: dict) -> dict[str, str]:
    """Nazwa wyświetlana benchmarku -> kolumna w historii (pierwszy = główny)."""
    primary = next(iter(benchmarks))
    return {str(spec.get("name", key)): bench_value_column(key, primary)
            for key, spec in benchmarks.items()}


def _auto_bench_cols(history: pd.DataFrame) -> dict[str, str]:
    """Kolumny benchmarków wykryte z danych (gdy nie podano configu, np. w CLI)."""
    names: dict[str, str] = {}
    if "benchmark_value" in history.columns:
        names["Benchmark"] = "benchmark_value"
    for c in history.columns:
        if c.startswith("benchmark_") and c.endswith("_value") and c != "benchmark_value":
            names[c.removeprefix("benchmark_").removesuffix("_value")] = c
    return names


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


def _prepare_history(history: pd.DataFrame,
                     run_kinds: tuple[str, ...] | None = None) -> pd.DataFrame:
    """Normalizuje daty i opcjonalnie filtruje serię po pochodzeniu biegu.

    Stare pliki bez kolumny `run_kind` traktujemy jako `legacy` — nie wchodzą
    do paper tradingu, ale nadal można na nich liczyć metryki ręcznie.
    """
    h = history.copy()
    h["date"] = pd.to_datetime(h["date"], errors="coerce")
    h = h.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    if "run_kind" in h.columns:
        h["run_kind"] = h["run_kind"].fillna("legacy").astype(str)
    else:
        h["run_kind"] = "legacy"
    if run_kinds is not None:
        h = h[h["run_kind"].isin(tuple(run_kinds))].reset_index(drop=True)
    return h


def history_weeks(history: pd.DataFrame,
                  run_kinds: tuple[str, ...] | None = None) -> int:
    """Liczba unikalnych tygodni ISO w (opcjonalnie filtrowanej) historii."""
    h = _prepare_history(history, run_kinds)
    if h.empty:
        return 0
    return int(h["date"].dt.to_period("W").nunique())


def compute_metrics(history: pd.DataFrame, risk_free_annual: float = 0.0,
                    value_col: str = "total_value",
                    bench_cols: dict[str, str] | None = None,
                    run_kinds: tuple[str, ...] | None = None,
                    require_weeks: int = 0) -> Metrics | None:
    """Metryki portfela i benchmarków z historii snapshotów.

    bench_cols: nazwa wyświetlana -> kolumna wartości benchmarku; None = wykrycie
    z danych. Każda strona liczona jest na własnym podzbiorze wierszy bez NaN,
    więc dana kolumna benchmarku może zaczynać się później niż reszta historii
    (stare wiersze bez dodanej kolumny nie blokują pozostałych serii).

    run_kinds: opcjonalny filtr pochodzenia (`("scheduled",)` dla paper
    tradingu); None = wszystkie wiersze. require_weeks: minimalna liczba
    unikalnych tygodni ISO, zanim metryki w ogóle powstają (0 = bez progu).

    Zwraca None, gdy punktów < MIN_POINTS, okres < 1 dzień albo wymagany
    próg tygodni nie jest spełniony. Annualizacja z rzeczywistych odstępów
    czasu (365 / średnia długość interwału), więc nieregularny rytm biegów
    nie zniekształca wyniku.
    """
    h = _prepare_history(history, run_kinds)
    if len(h) < MIN_POINTS:
        return None
    weeks = int(h["date"].dt.to_period("W").nunique())
    if require_weeks and weeks < require_weeks:
        return None
    cols = bench_cols if bench_cols is not None else _auto_bench_cols(h)

    def side(col: str) -> SideMetrics | None:
        if col not in h.columns:  # kolumna benchmarku jeszcze nie istnieje w historii
            return None
        sub = h[["date", col]].dropna()
        if len(sub) < MIN_POINTS:
            return None
        days = (sub["date"].iloc[-1] - sub["date"].iloc[0]).total_seconds() / 86400.0
        if days < 1:
            return None
        intervals_per_year = 365.0 / (days / (len(sub) - 1))
        return _side_metrics(sub[col].astype(float).tolist(),
                             intervals_per_year, days, risk_free_annual)

    portfolio = side(value_col)
    if portfolio is None:
        return None
    benchmarks = {name: side(col) for name, col in cols.items()}
    days = (h["date"].iloc[-1] - h["date"].iloc[0]).total_seconds() / 86400.0
    return Metrics(n_points=len(h), days=days, portfolio=portfolio,
                   benchmarks=benchmarks, risk_free_annual=risk_free_annual,
                   n_weeks=weeks, run_kinds=tuple(run_kinds or ()))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="inv-adv F1: metryki z historii")
    parser.add_argument("--history", default=str(HISTORY_PATH))
    parser.add_argument("--risk-free", type=float, default=0.0)
    parser.add_argument("--run-kinds", default=None,
                        help="filtr pochodzenia, np. scheduled (domyślnie wszystkie)")
    parser.add_argument("--require-weeks", type=int, default=0,
                        help="minimalna liczba unikalnych tygodni ISO")
    args = parser.parse_args(argv)

    run_kinds = tuple(x.strip() for x in args.run_kinds.split(",") if x.strip()) \
        if args.run_kinds else None
    history = read_history(Path(args.history))
    m = compute_metrics(history, args.risk_free, run_kinds=run_kinds,
                        require_weeks=args.require_weeks)
    if m is None:
        weeks = history_weeks(history, run_kinds)
        need = f" (jest {weeks}, potrzeba {args.require_weeks})" if args.require_weeks else ""
        print(f"za mało danych — metryki od {MIN_POINTS} punktów i "
              f"{args.require_weeks or 0} tygodni{need}")
        return 0
    print(f"n={m.n_points} pkt | tygodnie={m.n_weeks} | okres {m.days:.0f} dni "
          f"(orientacyjnie przy małym n)")
    sides = [("portfel", m.portfolio)] + list(m.benchmarks.items())
    for name, s in sides:
        if s is None:
            print(f"  {name:15s} brak danych (potrzeba {MIN_POINTS} punktów)")
            continue
        sh = "n/d" if s.sharpe is None else f"{s.sharpe:.2f}"
        print(f"  {name:15s} wynik {s.total_return:+.1%} | ann {s.annualized_return:+.1%} "
              f"| vol {s.vol_annualized:.1%} | sharpe {sh} | maxDD {s.max_drawdown:.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
