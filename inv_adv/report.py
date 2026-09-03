"""M3 — protokół decyzji (audyt) i historia snapshotów."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import pandas as pd

from .rebalance import Trade
from .review import Snapshot

DECISIONS_DIR = Path("reports/decisions")
HISTORY_PATH = Path("reports/history.csv")


def write_protocol(snapshot: Snapshot, trades: list[Trade], fired_rules: list[str],
                   prices_meta: str, base_currency: str = "",
                   out_dir: Path = DECISIONS_DIR) -> Path:
    """Protokół decyzji w markdown: dane wejściowe, migawka, reguły, transakcje."""
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
        f"- benchmark (1 jedn.): {snapshot.benchmark_value:,.2f}{ccy}",
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
    """Dopisuje wiersz migawki (buduje serię pod metryki w F1)."""
    row = {
        "date": dt.datetime.now().isoformat(timespec="seconds"),
        "total_value": snapshot.total_value,
        "benchmark_value": snapshot.benchmark_value,
    }
    for cls in snapshot.targets:
        row[f"share_{cls}"] = round(snapshot.allocation[cls], 6)
    df = pd.DataFrame([row])
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, mode="a", header=not path.exists(), index=False)
