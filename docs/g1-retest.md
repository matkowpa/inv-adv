# G1 re-test — protokół kalibracji (D6b, przygotowanie 2026-09-10)

> Odpowiedź na 5 kroków werdyktu sędziego z [g1-wynik.md](g1-wynik.md). Decyzja D6
> (opcja b) wymaga wykonania kalibracji PRZED re-testem. Status poszczególnych kroków
> poniżej; wykonanie re-testu (sesja idea-orch) dopiero po domknięciu kroku 1 i decyzji
> właściciela.

## Krok 1 — baseline niedeterminizmu: DO WYKONANIA (przed re-testem)

5–10 uruchomień jednego agenta (ten sam prompt, bez person) → rozkład L1 między
odpowiedziami tego samego modelu. Zerokosztowe pomijając tokeny (~$0.01–0.02).
**Kryterium:** skalibrowany próg musi przewyższać górny kwantyl szumu wewnątrz-agenta,
inaczej re-test nie ma sensu (rozbieżność międzysystemowa ≈ szum).

## Krok 2 — symulacja 20 par → kalibracja progu: ✅ WYKONANA

`python scripts/g1_calibration.py` (seed=42, reprodukowalna). Wynik:

| typ pary | L1 min | L1 max |
|---|---|---|
| sens-sens (10 par) | 25,7 p.p. | 82,4 p.p. |
| sens-teatr (10 par) | 174,1 p.p. | 197,5 p.p. |

Separacja pełna → **skalibrowany próg G1: 128 p.p.** (punkt środkowy przedziału
bezparowego 82,4–174,1). Potwierdza Goodharta: oryginalny próg 30 p.p. leżał PONIŻEJ
typowej odległości między dwoma sensownymi portfelami (median ~46 p.p.), więc nagradzał
teatralność — dokładnie jak sfalsyfikowano w debacie G1.

## Krok 3 — prompty bez tabeli Sharpe: ✅ ZAPROJEKTOWANE

Wejście re-testu zastępuje 8-miesięczną tabelę wyników profilem inwestora i horyzontem:
- profil: 100% aktywa ryzykowne, tolerancja wysoka, brak potrzeby wypłaty (D1),
- horyzont: >10 lat; benchmark odniesienia: S&P 500 (D1),
- **bez** danych wynikowych za jakikolwiek przeszły okres,
- wymóg twardy (j.w. jak w G1 v1): wektor 6 liczb sumujący się do 1.0 w KAŻDEJ rundzie.

## Krok 4 — rozdzielenie oceny D1 od komitetu: ✅ PRZYJĘTE

Re-test odpowiada wyłącznie na pytanie G1 (czy agenci różnią się między sobą bardziej,
niż różni się agent sam od siebie — kroki 1–2). Zgodność/wektory agentów NIE są porównywane
z portfelem właściciela ani z kryterium Sharpe (D1) — to osobne pytanie, oceniane osobno.

## Krok 5 — liczbowy protokół furtki: ✅ PRZYJĘTE

Gdyby komitet przeszedł re-test, jego rekomendacje mogą jedynie modyfikować tilt:
max 1 tilt na kwartał, max ±5 p.p. odchylania targetów klasy, zawsze z protokołem
i ręczną egzekucją (D3). Twarde reguły R1/R2 pozostają nienaruszone.

## Kryterium zakończenia (wierna furtka z g1-wynik.md)

Jeśli po kalibracji (krok 1 + 2) rozbieżność między agentami nadal nie przewyższa szumu
wewnątrz-agenta (krok 1) — **M4 zamykamy jako „teatr multi-agentowy", bez dalszych debat**.
Koszt re-testu: ~$0.21 (skala sesji G1 v1).
