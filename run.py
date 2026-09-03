"""F0 — orkiestracja cyklu: M1 przegląd -> M2 rebalancing -> M3 protokół.

Użycie:
    python run.py             # pobiera ceny z Yahoo (zapisuje cache)
    python run.py --offline   # używa cache z data/prices/latest.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

from inv_adv.data import collect_tickers, fetch_prices, load_config, load_portfolio
from inv_adv.metrics import compute_metrics, read_history
from inv_adv.rebalance import propose_trades
from inv_adv.report import HISTORY_PATH, append_history, write_protocol
from inv_adv.review import build_snapshot


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="inv-adv F0: przegląd + rebalancing + protokół")
    parser.add_argument("--offline", action="store_true",
                        help="użyj cache z data/prices/ zamiast pobierania z Yahoo")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--portfolio", default="data/portfolio.csv")
    args = parser.parse_args(argv)

    cfg = load_config(Path(args.config))
    portfolio = load_portfolio(Path(args.portfolio))
    prices, manual_overrides = fetch_prices(collect_tickers(portfolio, cfg),
                                            offline=args.offline)
    prices_meta = ("cache data/prices/latest.csv (offline)" if args.offline
                   else "Yahoo Finance (online; zapis do cache data/prices/latest.csv)")
    if manual_overrides:
        prices_meta += ("; ceny ręczne (data/prices_manual.csv): "
                        + ", ".join(manual_overrides))

    snapshot = build_snapshot(portfolio, prices, cfg)
    trades, fired = propose_trades(
        snapshot,
        threshold_pp=float(cfg["drift_threshold_pp"]),
        max_turnover_pct=float(cfg["max_turnover_pct"]),
    )
    append_history(snapshot)
    metrics = compute_metrics(read_history(HISTORY_PATH),
                              risk_free_annual=float(cfg.get("risk_free_annual", 0.0)))
    protocol = write_protocol(snapshot, trades, fired, prices_meta,
                              base_currency=str(cfg["base_currency"]), metrics=metrics)

    print(f"Portfel: {snapshot.total_value:,.2f} {cfg['base_currency']} "
          f"| benchmark (1 jedn.): {snapshot.benchmark_value:,.2f}")
    for cls, drift in snapshot.drift_pp.items():
        print(f"  {cls:15s} {snapshot.allocation[cls] * 100:6.1f}% "
              f"(target {cfg['targets'][cls] * 100:4.1f}%, dryf {drift:+.1f} p.p.)")
    print(f"Reguły: {len(fired)} | proponowane transakcje: {len(trades)}")
    if metrics is not None:
        print(f"Metryki F1: n={metrics.n_points} | portfel {metrics.portfolio.total_return:+.1%} "
              f"vs benchmark {metrics.benchmark.total_return:+.1%} (za okres)")
    else:
        print("Metryki F1: za mało danych (potrzeba 3 punktów historii)")
    print(f"Protokół: {protocol}")


if __name__ == "__main__":
    main()
