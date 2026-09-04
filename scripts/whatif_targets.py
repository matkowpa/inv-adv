"""What-if targetow D5 — konsekwencje wariantow alokacji dzisiaj (silnik M2, offline).

Uruchomienie (z katalogu projektu lub dowolnego):
    python scripts/whatif_targets.py

Uzywa cache cen data/prices/latest.csv i biezacego data/portfolio.csv. Nie zmienia
config.yaml ani mappingu — warianty liczone w pamieci. Kolejne uruchomienia po
swiezym `python run.py` odswieza analize do aktualnych cen.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
os.chdir(BASE)

from inv_adv.data import collect_tickers, fetch_prices, load_config, load_portfolio  # noqa: E402
from inv_adv.rebalance import propose_trades  # noqa: E402
from inv_adv.review import build_snapshot  # noqa: E402

# (nazwa, targety — suma = 1.0, remap klas: z -> do)
VARIANTS = [
    ("W0 — status quo (obecny szkic)",
     {"equity_us": 0.55, "equity_pl": 0.15, "equity_thematic": 0.10,
      "equity_em": 0.08, "equity_single": 0.02, "crypto": 0.10},
     {}),
    ("W1 — konsolidacja 4-klasowa (thematic+single -> equity_us)",
     {"equity_us": 0.67, "equity_pl": 0.15, "equity_em": 0.08, "crypto": 0.10},
     {"equity_thematic": "equity_us", "equity_single": "equity_us"}),
    ("W2 — krypto pod kontrola (3%)",
     {"equity_us": 0.62, "equity_pl": 0.15, "equity_thematic": 0.10,
      "equity_em": 0.08, "equity_single": 0.02, "crypto": 0.03},
     {}),
    ("W3 — tilt US (PL 10%, EM 0, single 0)",
     {"equity_us": 0.70, "equity_pl": 0.10, "equity_thematic": 0.10,
      "equity_em": 0.00, "equity_single": 0.00, "crypto": 0.10},
     {}),
]


def main() -> None:
    cfg = load_config(BASE / "config.yaml")
    portfolio = load_portfolio(BASE / "data/portfolio.csv")
    prices, manual = fetch_prices(collect_tickers(portfolio, cfg), offline=True)
    threshold = float(cfg["drift_threshold_pp"])
    cap = float(cfg["max_turnover_pct"])
    cost_rate = float(cfg["transaction_cost_pct"]) / 100.0
    ccy = cfg["base_currency"]

    print(f"Waluta bazowa: {ccy} | ceny: cache offline"
          + (f" (reczne nadpisania: {', '.join(manual)})" if manual else ""))
    print(f"Prog R1: {threshold:.0f} p.p. | limit obrotu R2: {cap:.0f}% "
          f"| koszt transakcyjny: {cost_rate:.2%}\n")

    for name, targets, remap in VARIANTS:
        assert abs(sum(targets.values()) - 1.0) < 1e-9, f"{name}: suma targetow != 1.0"
        pf = portfolio.copy()
        if remap:
            pf["asset_class"] = pf["asset_class"].replace(remap)
        snap = build_snapshot(pf, prices, dict(cfg, targets=targets))
        trades, fired = propose_trades(snap, threshold_pp=threshold, max_turnover_pct=cap)

        print("=" * 76)
        print(name)
        print("  targety: " + " / ".join(f"{k} {v:.0%}" for k, v in targets.items()))
        print("  dryfy (udzial vs target; odleglosc do progu R1):")
        for cls, target in targets.items():
            drift = snap.drift_pp[cls]
            headroom = max(threshold - abs(drift), 0.0)
            print(f"    {cls:16s} {snap.allocation[cls] * 100:5.1f}% vs {target * 100:4.1f}%"
                  f"  -> {drift:+5.1f} p.p.  (do progu: {headroom:4.1f} p.p.)")
        print(f"  odpalone reguly: {len(fired)}")
        for r in fired:
            print(f"    {r}")
        if trades:
            turnover = sum(t.amount for t in trades)
            for t in trades:
                print(f"    {t.direction} {t.ticker:14s} {t.amount:>12,.2f} {ccy}"
                      f"  (~{t.units:,.4f} jedn.)  [{t.rule} | {t.detail}]")
            print(f"  obrot laczny: {turnover:,.2f} {ccy} ({turnover / snap.total_value:.1%})"
                  f" | est. koszt: {turnover * cost_rate:,.2f} {ccy}")
            buys = sum(t.amount for t in trades if t.direction == "BUY")
            sells = sum(t.amount for t in trades if t.direction == "SELL")
            if abs(buys - sells) > 1:
                print(f"  bilans: BUY {buys:,.0f} vs SELL {sells:,.0f} -> roznica "
                      f"{abs(buys - sells):,.0f} {ccy} (klasy w pasmie nie sa ruszane)")
        else:
            print("  transakcje: brak — portfel w pasmie progowym")
        print()


if __name__ == "__main__":
    main()