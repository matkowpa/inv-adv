"""Kalibracja progu rozbieżności G1 (krok 2 werdyktu sędziego, g1-wynik.md).

Symuluje 20 par wektorów targetów (10x "sensowny+sensowny", 10x "sensowny+teatralny"),
liczy odległość L1 (suma modułów różnic w p.p.) i wskazuje próg separujący pary.
Zerokosztowa, offline — wsparcie decyzji D6(b): re-test G1 po kalibracji.

Użycie: python scripts/g1_calibration.py
"""
from __future__ import annotations

import random

CLASSES = ["us", "pl", "th", "em", "sg", "cr"]


def l1_pp(a: list[float], b: list[float]) -> float:
    """Odległość L1 dwóch wektorów targetów (ułamki) w punktach procentowych."""
    return sum(abs(x - y) for x, y in zip(a, b)) * 100.0


def sensible(rng: random.Random) -> list[float]:
    """Realistyczny portfel 100% ryzykowny: rdzeń indeksowy + dodatki, krypto 0-15%."""
    us = rng.uniform(0.45, 0.75)
    pl = rng.uniform(0.05, 0.20)
    cr = rng.uniform(0.0, 0.15)
    rest = 1.0 - us - pl - cr
    th, em, sg = (rest * rng.uniform(0, 1) for _ in range(3))
    vec = [us, pl, th, em, sg, cr]
    s = sum(vec)
    return [v / s for v in vec]  # normalizacja do sumy = 1


def theatrical() -> list[float]:
    """Portfel teatralny: wszystko w jedną klasę (lub krypto maksymalne)."""
    return [0.0, 0.0, 0.0, 0.0, 0.0, 1.0]


def main() -> None:
    rng = random.Random(42)  # deterministycznie — reprodukowalność
    pairs = []
    for _ in range(10):
        pairs.append(("sens-sens", l1_pp(sensible(rng), sensible(rng))))
    for _ in range(10):
        pairs.append(("sens-teatr", l1_pp(sensible(rng), theatrical())))

    sens = sorted(v for tag, v in pairs if tag == "sens-sens")
    teatr = sorted(v for tag, v in pairs if tag == "sens-teatr")
    print(f"{'typ pary':12s} {'L1 [p.p.]':>10s}")
    for tag, v in pairs:
        print(f"{tag:12s} {v:10.1f}")
    print(f"\nsens-sens:  min {sens[0]:.1f} | max {sens[-1]:.1f} p.p.")
    print(f"sens-teatr: min {teatr[0]:.1f} | max {teatr[-1]:.1f} p.p.")
    # Próg: minimum par teatralnych musi przewyższać maksimum par sensownych,
    # inaczej L1 nie separuje i trzeba innej miary rozbieżności.
    if sens[-1] < teatr[0]:
        thr = (sens[-1] + teatr[0]) / 2
        print(f"\nSeparacja OK. Proponowany próg G1: {thr:.1f} p.p.")
    else:
        print("\nBRAK separacji — miara L1 nie rozróżnia; przemyśleć metrykę przed re-testem.")


if __name__ == "__main__":
    main()
