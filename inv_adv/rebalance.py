"""M2 — silnik rebalancingu: twarde reguły, zero dyskrecji (decyzja D3)."""
from __future__ import annotations

import math
from dataclasses import dataclass

from .review import Snapshot

RULE_BAND = "R1"   # próg dryfu
RULE_CAP = "R2"    # limit obrotu
RULE_MIN = "Rmin"  # minimalna kwota pojedynczego zlecenia (koszt operacyjny)


@dataclass
class Trade:
    direction: str      # BUY / SELL
    asset_class: str
    ticker: str
    amount: float       # kwota brutto w walucie bazowej (dodatnia)
    units: float        # szacunkowa liczba jednostek
    rule: str           # ID reguły, która wygenerowała transakcję
    detail: str         # np. "crypto: dryf +7.2 p.p."
    fee: float = 0.0    # szacunkowy koszt transakcyjny w walucie bazowej

    @property
    def net_amount(self) -> float:
        """Gotówka potrzebna (BUY) lub otrzymana (SELL) po kosztach."""
        return self.amount + self.fee if self.direction == "BUY" else self.amount - self.fee


def propose_trades(snapshot: Snapshot, threshold_pp: float,
                   max_turnover_pct: float,
                   transaction_cost_pct: float = 0.0,
                   min_trade_amount: float = 0.0,
                   lot_sizes: dict[str, float] | None = None) -> tuple[list[Trade], list[str]]:
    """Deterministyczne reguły (kolejność wg malejącego |dryf|):

    R1: |udział - target| > próg [p.p.] -> transakcja dokładnie do targetu klasy;
        kwota klasy dzielona na tickery proporcjonalnie do ich wartości w klasie.
    R2: jeśli obrót > max_turnover_pct -> proporcjonalne przeskalowanie kwot.
    Rmin: pojedyncze zlecenie poniżej `min_trade_amount` jest pomijane z wpisem
        w protokole (nie ma sensu ekonomicznego).

    `transaction_cost_pct` to koszt w procentach (0.2 = 0,2%). `lot_sizes`
    opcjonalnie wymusza wielokrotność jednostek per ticker (np. ETF na GPW);
    bez wpisu silnik dopuszcza jednostki ułamkowe. Klasa z targetem, ale bez
    pozycji, nie znika po cichu — dostaje wpis `BRAK POZYCJI`.

    Zwraca (trades, fired_rules).
    """
    fired: list[str] = []
    lot_sizes = lot_sizes or {}
    class_amounts: list[tuple[str, float, float]] = []  # (klasa, kwota ±, dryf p.p.)

    for cls, target in snapshot.targets.items():
        share = snapshot.allocation[cls]
        drift = snapshot.drift_pp[cls]
        if abs(drift) > threshold_pp:
            class_amounts.append((cls, (target - share) * snapshot.total_value, drift))
            fired.append(
                f"{RULE_BAND}: {cls} — dryf {drift:+.1f} p.p. > {threshold_pp:.1f} p.p. "
                f"(udział {share * 100:.1f}%, target {target * 100:.1f}%)")

    class_amounts.sort(key=lambda x: -abs(x[2]))

    trades: list[Trade] = []
    pos = snapshot.positions
    for cls, amount, drift in class_amounts:
        cls_pos = pos[pos["asset_class"] == cls]
        if cls_pos.empty:
            fired.append(
                f"{RULE_BAND}: {cls} — dryf {drift:+.1f} p.p.; BRAK POZYCJI w klasie "
                f"— dodaj ticker/proxy do portfela, transakcja niemożliwa")
            continue
        cls_total = float(cls_pos["value_base"].sum())
        if cls_total <= 0:
            fired.append(f"{RULE_BAND}: {cls} — zerowa wartość pozycji; transakcja niemożliwa")
            continue
        for _, row in cls_pos.iterrows():
            part = amount * float(row["value_base"]) / cls_total
            unit_price = float(row["price"]) * float(row["fx_rate"])
            if unit_price <= 0:
                fired.append(f"{RULE_BAND}: {row['ticker']} — cena <= 0; transakcja niemożliwa")
                continue
            raw_units = abs(part) / unit_price
            lot = float(lot_sizes.get(str(row["ticker"]), 0.0) or 0.0)
            units = math.floor(raw_units / lot) * lot if lot > 0 else raw_units
            if units <= 0:
                fired.append(
                    f"{RULE_MIN}: {row['ticker']} — {abs(part):,.2f} to mniej niż "
                    f"jedna jednostka (lot {lot:g}); pominięto")
                continue
            trade_amount = units * unit_price
            trades.append(Trade(
                direction="BUY" if part >= 0 else "SELL",
                asset_class=cls,
                ticker=str(row["ticker"]),
                amount=trade_amount,
                units=units,
                rule=RULE_BAND,
                detail=f"{cls}: dryf {drift:+.1f} p.p."))

    if trades:
        turnover_pct = sum(t.amount for t in trades) / snapshot.total_value * 100
        if turnover_pct > max_turnover_pct:
            scale = max_turnover_pct / turnover_pct
            for t in trades:
                t.amount *= scale
                t.units *= scale
            fired.append(
                f"{RULE_CAP}: obrót {turnover_pct:.1f}% > {max_turnover_pct:.1f}% — "
                f"proporcjonalne przeskalowanie kwot ×{scale:.3f}")

    if min_trade_amount > 0:
        kept: list[Trade] = []
        for t in trades:
            if t.amount < min_trade_amount:
                fired.append(
                    f"{RULE_MIN}: {t.ticker} — {t.amount:,.2f} < minimum "
                    f"{min_trade_amount:,.2f}; pominięto")
                continue
            kept.append(t)
        trades = kept

    if transaction_cost_pct:
        for t in trades:
            t.fee = round(t.amount * transaction_cost_pct / 100.0, 2)

    return trades, fired
