"""F0 — orkiestracja cyklu: M1 przegląd -> M2 rebalancing -> M3 protokół.

Użycie:
    python run.py             # bieg ręczny (run_kind=manual)
    python run.py --scheduled # bieg cotygodniowy paper tradingu (idempotentny)
    python run.py --offline   # używa cache z data/prices/latest.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path

from inv_adv.data import (benchmarks_of, collect_tickers, fetch_prices,
                          load_config, load_portfolio)
from inv_adv.metrics import (bench_cols_from_cfg, compute_metrics, history_weeks,
                             read_history)
from inv_adv.rebalance import propose_trades
from inv_adv.report import HISTORY_PATH, append_history, write_protocol
from inv_adv.review import build_snapshot
from inv_adv.status import write_status


def _run_kind(args: argparse.Namespace) -> str:
    if args.run_kind:
        return args.run_kind
    return "scheduled" if args.scheduled else "manual"


def run(args: argparse.Namespace) -> dict:
    run_kind = _run_kind(args)
    cfg = load_config(Path(args.config))
    benchmarks = benchmarks_of(cfg)
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
        transaction_cost_pct=float(cfg.get("transaction_cost_pct", 0.0)),
        min_trade_amount=float(cfg.get("min_trade_amount", 0.0)),
        lot_sizes=cfg.get("lot_sizes") or {},
    )
    history_action = append_history(snapshot, run_kind=run_kind)
    history = read_history(HISTORY_PATH)
    paper_weeks = history_weeks(history, run_kinds=("scheduled",))
    paper_target = int(cfg.get("paper_trading_weeks", 12))
    metrics = compute_metrics(
        history,
        risk_free_annual=float(cfg.get("risk_free_annual", 0.0)),
        bench_cols=bench_cols_from_cfg(benchmarks),
        run_kinds=("scheduled",),
        require_weeks=paper_target,
    )
    protocol = write_protocol(snapshot, trades, fired, prices_meta,
                              base_currency=str(cfg["base_currency"]), metrics=metrics,
                              benchmarks=benchmarks, run_kind=run_kind)

    bench_str = " | ".join(f"{spec.get('name', key)}: {snapshot.benchmark_values[key]:,.2f}"
                           for key, spec in benchmarks.items())
    print(f"Portfel: {snapshot.total_value:,.2f} {cfg['base_currency']} "
          f"| benchmarki (1 jedn.): {bench_str}")
    for cls, drift in snapshot.drift_pp.items():
        print(f"  {cls:15s} {snapshot.allocation[cls] * 100:6.1f}% "
              f"(target {cfg['targets'][cls] * 100:4.1f}%, dryf {drift:+.1f} p.p.)")
    print(f"Reguły: {len(fired)} | proponowane transakcje: {len(trades)} "
          f"| koszty: {sum(t.fee for t in trades):,.2f} {cfg['base_currency']}")
    print(f"Paper trading: {paper_weeks}/{paper_target} tygodni "
          f"(metryki: {'gotowe' if metrics is not None else 'za mało danych'})")
    if metrics is not None:
        parts = [f"portfel {metrics.portfolio.total_return:+.1%}"]
        parts += [f"{name} {'n/d' if s is None else format(s.total_return, '+.1%')}"
                  for name, s in metrics.benchmarks.items()]
        print(f"Metryki F1: n={metrics.n_points} | tygodnie={metrics.n_weeks} "
              f"| wynik za okres: " + " vs ".join(parts))
    else:
        print("Metryki F1: za mało danych (potrzeba 3 punktów i "
              f"{paper_target} tygodni scheduled)")
    print(f"Protokół: {protocol}")

    status = write_status(
        status="ok",
        run_kind=run_kind,
        history_action=history_action,
        history_rows=len(history),
        scheduled_weeks=paper_weeks,
        paper_trading_weeks=paper_target,
        metrics_ready=metrics is not None,
        protocol=str(protocol),
    )
    return status


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="inv-adv F0: przegląd + rebalancing + protokół")
    parser.add_argument("--offline", action="store_true",
                        help="użyj cache z data/prices/ zamiast pobierania z Yahoo")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--portfolio", default="data/portfolio.csv")
    parser.add_argument("--scheduled", action="store_true",
                        help="bieg cotygodniowy paper tradingu (run_kind=scheduled)")
    parser.add_argument("--run-kind", choices=("scheduled", "manual", "smoke"),
                        default=None, help="pochodzenie biegu; nadpisuje --scheduled")
    args = parser.parse_args(argv)

    try:
        run(args)
    except Exception as exc:
        write_status(status="error", run_kind=_run_kind(args), step="run.py",
                     error=f"{type(exc).__name__}: {exc}")
        raise


if __name__ == "__main__":
    main()
