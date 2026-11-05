"""M3b — ręczny log faktycznych wykonań (fill).

System nadal nie składa zleceń automatycznie (D3), więc po wykonaniu transakcji
u właściciela trzeba zapisać fakt. Ten moduł dopisuje fill do miesięcznego CSV
w `reports/executions/`; nie modyfikuje propozycji M2 ani historii wyceny.

Użycie:
    python -m inv_adv.execution --ticker SXR8.DE --side BUY \
        --quantity 10 --price 520.50 --fee 2.60 --note "IBKR fill"
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
from pathlib import Path

EXECUTIONS_DIR = Path("reports/executions")
FIELDS = ["executed_at", "ticker", "side", "quantity", "price", "fee", "currency", "note"]


def record_execution(ticker: str, side: str, quantity: float, price: float,
                     fee: float = 0.0, currency: str = "PLN", note: str = "",
                     executed_at: dt.datetime | None = None,
                     out_dir: Path = EXECUTIONS_DIR) -> Path:
    """Dopisuje pojedynczy fill; zwraca ścieżkę pliku miesięcznego."""
    side = side.upper().strip()
    if side not in {"BUY", "SELL"}:
        raise ValueError("side musi być BUY albo SELL")
    if not ticker.strip():
        raise ValueError("ticker nie może być pusty")
    if quantity <= 0 or price <= 0:
        raise ValueError("quantity i price muszą być > 0")
    if fee < 0:
        raise ValueError("fee nie może być ujemne")

    ts = executed_at or dt.datetime.now()
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{ts:%Y-%m}.csv"
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            writer.writeheader()
        writer.writerow({
            "executed_at": ts.isoformat(timespec="seconds"),
            "ticker": ticker.strip().upper(),
            "side": side,
            "quantity": f"{quantity:g}",
            "price": f"{price:g}",
            "fee": f"{fee:g}",
            "currency": currency.upper().strip() or "PLN",
            "note": note.strip(),
        })
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="inv-adv: zapis faktycznego wykonania (fill)")
    parser.add_argument("--ticker", required=True)
    parser.add_argument("--side", required=True, choices=("BUY", "SELL"))
    parser.add_argument("--quantity", type=float, required=True)
    parser.add_argument("--price", type=float, required=True)
    parser.add_argument("--fee", type=float, default=0.0)
    parser.add_argument("--currency", default="PLN")
    parser.add_argument("--note", default="")
    args = parser.parse_args(argv)

    path = record_execution(args.ticker, args.side, args.quantity, args.price,
                            fee=args.fee, currency=args.currency, note=args.note)
    print(f"Zapisano fill -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
