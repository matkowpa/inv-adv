"""M3 — protokół decyzji (audyt) i historia snapshotów."""
from __future__ import annotations

from typing import TYPE_CHECKING

import datetime as dt
from pathlib import Path

import pandas as pd

from .data import bench_value_column
from .rebalance import Trade
from .review import Snapshot

if TYPE_CHECKING:  # uniknięcie importu cyklicznego — tylko do adnotacji typów
    from .metrics import Metrics

DECISIONS_DIR = Path("reports/decisions")
HISTORY_PATH = Path("reports/history.csv")


def write_protocol(snapshot: Snapshot, trades: list[Trade], fired_rules: list[str],
                   prices_meta: str, base_currency: str = "",
                   out_dir: Path = DECISIONS_DIR,
                   metrics: "Metrics | None" = None,
                   benchmarks: dict | None = None) -> Path:
    """Protokół decyzji w markdown: dane wejściowe, migawka, metryki, reguły, transakcje."""
    now = dt.datetime.now()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{now:%Y-%m-%d-%H%M%S}-protokol.md"

    ccy = f" {base_currency}" if base_currency else ""
    lines = [
        f"# Protokół decyzji — {now:%Y-%m-%d %H:%M}",
        "",
        "## Dane wejściowe",
        f"- źródło cen: {prices_meta}",
        f"- wartość portfela: {snapshot.total_value:,.2f}{ccy}",
    ]
    if benchmarks:
        for key, spec in benchmarks.items():
            lines.append(f"- benchmark {spec.get('name', key)} (1 jedn.): "
                         f"{snapshot.benchmark_values[key]:,.2f}{ccy}")
    else:
        lines.append(f"- benchmark (1 jedn.): {snapshot.benchmark_value:,.2f}{ccy}")
    lines += [
        "",
        "## Pozycje (M1)",
        "",
        "| ticker | klasa | ilość | cena | waluta | kurs FX | wartość |",
        "|---|---|---|---|---|---|---|",
    ]
    for _, r in snapshot.positions.iterrows():
        lines.append(f"| {r['ticker']} | {r['asset_class']} | {r['quantity']:g} "
                     f"| {r['price']:,.4f} | {r['currency']} | {r['fx_rate']:.4f} "
                     f"| {r['value_base']:,.2f}{ccy} |")

    lines += [
        "",
        "## Migawka klas (M1)",
        "",
        "| klasa | udział | target | dryf [p.p.] |",
        "|---|---|---|---|",
    ]
    for cls, target in snapshot.targets.items():
        lines.append(f"| {cls} | {snapshot.allocation[cls] * 100:.1f}% "
                     f"| {target * 100:.1f}% | {snapshot.drift_pp[cls]:+.1f} |")

    lines += ["", "## Metryki (F1)", ""]
    if metrics is None:
        lines.append("za mało danych w reports/history.csv (potrzeba 3 punktów) — "
                     "metryki pojawią się po kolejnych biegach")
    else:
        qualifier = (f" — dane orientacyjne (małe n, {metrics.days:.0f} dni)"
                     if metrics.n_points < 8 else f" — okres {metrics.days:.0f} dni")
        lines.append(f"n={metrics.n_points} punktów historii{qualifier}")
        names = list(metrics.benchmarks)
        sides = [metrics.portfolio] + [metrics.benchmarks[n] for n in names]
        rf = metrics.risk_free_annual
        rf_label = f"Sharpe (rf={rf:.1%})" if rf > 0 else "Sharpe (rf=0%)"
        row_specs = [
            ("wynik okresu", "total_return", "pct"),
            ("wynik annualizowany", "annualized_return", "pct"),
            ("zmienność roczna", "vol_annualized", "pct"),
            (rf_label, "sharpe", "sharpe"),
            ("max drawdown", "max_drawdown", "pct"),
        ]

        def _cell(x: float | None, kind: str) -> str:
            if x is None:
                return "n/d"
            return f"{x:+.2f}" if kind == "sharpe" else f"{x:+.1%}"

        lines += ["", "| metryka | portfel | " + " | ".join(names) + " |",
                  "|---|---|" + "---|" * len(names)]
        for label, attr, kind in row_specs:
            cells = " | ".join(_cell(None if s is None else getattr(s, attr), kind)
                               for s in sides)
            lines.append(f"| {label} | {cells} |")

    lines += ["", "## Reguły (M2)", ""]
    if fired_rules:
        lines += [f"- {r}" for r in fired_rules]
    else:
        lines.append("- żadna reguła nie odpaliła — portfel w paśmie progowym")

    lines += ["", "## Proponowane transakcje (M2)", ""]
    if trades:
        lines += ["| # | kierunek | klasa | ticker | kwota | ~jednostki | reguła |",
                  "|---|---|---|---|---|---|---|"]
        for i, t in enumerate(trades, 1):
            lines.append(f"| {i} | {t.direction} | {t.asset_class} | {t.ticker} "
                         f"| {t.amount:,.2f}{ccy} | {t.units:,.4f} | {t.rule} |")
        turnover = sum(t.amount for t in trades)
        lines += ["", f"Obrót łączny: {turnover:,.2f}{ccy} "
                      f"({turnover / snapshot.total_value * 100:.1f}% portfela)"]
    else:
        lines.append("brak — portfel w paśmie progowym")

    lines += [
        "",
        "## Wyjątki ręczne (D3)",
        "",
        "brak — system zawsze wykonuje regułę; wyjątek tylko ręcznie, z wpisem w logu.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def append_history(snapshot: Snapshot, path: Path = HISTORY_PATH) -> None:
    """Dopisuje wiersz migawki (buduje serię pod metryki w F1).

    Obsługuje ewolucję schematu: gdy wiersz zawiera nowe kolumny (np. dodany
    benchmark), plik jest przepisywany ze scalonym nagłówkiem — stare wiersze
    dostają NaN w nowych kolumnach. Benchmark główny trafia do legacy kolumny
    benchmark_value (kryterium D1, kompatybilność wstecz).
    """
    bench_values = snapshot.benchmark_values
    primary = next(iter(bench_values))
    row = {
        "date": dt.datetime.now().isoformat(timespec="seconds"),
        "total_value": snapshot.total_value,
        "benchmark_value": bench_values[primary],
    }
    for key, value in bench_values.items():
        if key != primary:
            row[bench_value_column(key, primary)] = value
    for cls in snapshot.targets:
        row[f"share_{cls}"] = round(snapshot.allocation[cls], 6)

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        old = pd.read_csv(path)
        merged = pd.concat([old, pd.DataFrame([row])], ignore_index=True)
        merged.to_csv(path, index=False)
    else:
        pd.DataFrame([row]).to_csv(path, index=False, header=True)
