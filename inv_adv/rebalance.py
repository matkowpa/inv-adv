"""M2 — silnik rebalancingu: twarde reguły, zero dyskrecji (decyzja D3)."""
from __future__ import annotations

from dataclasses import dataclass

from .review import Snapshot

RULE_BAND = "R1"   # próg dryfu
RULE_CAP = "R2"    # limit obrotu


@dataclass
class Trade:
    direction: str      # BUY / SELL
    asset_class: str
    ticker: str
    amount: float       # kwota w walucie bazowej (dodatnia)
    units: float        # szacunkowa liczba jednostek
    rule: str           # ID reguły, która wygenerowała transakcję
    detail: str         # np. "crypto: dryf +7.2 p.p."


def propose_trades(snapshot: Snapshot, threshold_pp: float,
                   max_turnover_pct: float) -> tuple[list[Trade], list[str]]:
    """Deterministyczne reguły (kolejność wg malejącego |dryf|):

    R1: |udział - target| > próg [p.p.] -> transakcja dokładnie do targetu klasy;
        kwota klasy dzielona na tickery proporcjonalnie do ich wartości w klasie.
    R2: jeśli obrót > max_turnover_pct -> proporcjonalne przeskalowanie kwot.

    Zwraca (trades, fired_rules).
    """
    fired: list[str] = []
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
        cls_total = float(cls_pos["value_base"].sum())
        for _, row in cls_pos.iterrows():
            part = amount * float(row["value_base"]) / cls_total
            unit_price = float(row["price"]) * float(row["fx_rate"])
            trades.append(Trade(
                direction="BUY" if part >= 0 else "SELL",
                asset_class=cls,
                ticker=str(row["ticker"]),
                amount=abs(part),
                units=abs(part) / unit_price,
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

    return trades, fired
