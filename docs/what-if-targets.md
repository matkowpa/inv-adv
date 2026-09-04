# Analiza what-if: warianty targetów alokacji (wsparcie decyzji D5)

> Wygenerowana **prawdziwym silnikiem M2** (`propose_trades`, reguły R1/R2) na migawce
> z **2026-09-04 09:13** (ceny z cache offline, pełna reprodukowalność: `python scripts/whatif_targets.py`).
> Parametry: próg R1 = 5 p.p., limit obrotu R2 = 20%, koszt transakcyjny 0,2%.
> Analiza nie zmienia `config.yaml` ani mappingu — to materiał decyzyjny.

> **AKTUALIZACJA 2026-09-04, popołudnie:** właściciel zlikwidował pozycję ETH
> (WETH.PA, 615 jedn.; akcja ręczna — wpis audytowy per D3). Portfel: **13 pozycji,
> 1 370 079 PLN**; krypto = tylko BITC.AS (4,7%). Liczby w tabelach poniżej są
> **historyczne** (stan poranny). Skutki dla wariantów: **W0** — R1 już odpala
> (krypto −5,3 p.p. → propozycja BUY BITC.AS 72 787 PLN do targetu 10%, protokół
> `2026-09-04-140402`); **W2** (krypto 3%) — wróciłoby w pasmo (+1,7 p.p., 0 transakcji).
> Decyzja D5 zyskuje na wadze: utrzymanie targetu krypto 10% oznacza dziś
> **podwojenie ekspozycji BTC** — a decyzja o tym należy do właściciela (egzekucja ręczna).

## Motywacja (skąd ta decyzja)

Obecny skład w ostatnich ~8 miesiącach: **−1,1% / Sharpe −0,09 / maxDD −13,2%**
vs S&P 500 (PLN) **+15,4% / 1,50 / −7,0%** i Nasdaq-100 (PLN) **+19,2% / 1,33 / −9,2%**.
Portfel nie dawał premii za ryzyko — pytanie D5 brzmi: jaka struktura worków ma to zmienić
(czy świadomie zostajemy pasywni)?

## Podsumowanie porównawcze (stan: 1 411 641 PLN, us 57,3 / pl 14,9 / thematic 10,4 / em 8,0 / single 1,0 / crypto 8,4)

| Wariant | Targety | Klasy | Transakcje dziś | Obrót | Est. koszt | Uwagi |
|---|---|---|---|---|---|---|
| **W0 status quo** | us 55 / pl 15 / th 10 / em 8 / sg 2 / cr 10 | 6 | **0** | 0 | 0 PLN | pasywny; najbliżej progu: us (2,7 p.p.), crypto (3,4) |
| **W1 konsolidacja** | us 67 / pl 15 / em 8 / cr 10 | **4** | **0** | 0 | 0 PLN | czysta zmiana strukturalna (RBOT+INTRUM→us); wymaga zmiany w mappingu |
| **W2 krypto 3%** | us 62 / pl 15 / th 10 / em 8 / sg 2 / cr **3** | 6 | SELL krypto **76 045 PLN** | 5,4% | 152 PLN | sprzedaż bez automatycznego dokupienia (patrz niżej) |
| **W3 tilt US** | us **70** / pl 10 / th 10 / em **0** / sg 0 / cr 10 | 6 (2 puste) | BUY US **173 273** (7 tickerów) + SELL EMQQ **109 055** | **20,0% — limit R2!** | 565 PLN | odpala R2; bilans +64 217 wymaga gotówki zewn. |

## W0 — status quo (55/15/10/8/2/10)

Dryfy: us +2,3 · pl −0,1 · th +0,4 · em −0,0 · sg −1,0 · cr −1,6 — wszystko w paśmie,
**0 transakcji**. Rebalancing pozostaje teoretyczny: R1 odpali dopiero, gdy któraś klasa
przesunie się o kolejne 2,7–5,0 p.p. (np. krypto +3,4 p.p. w górę, albo us +2,7 w górę).
To opcja „system czeka i pilnuje" — bez świadomej zmiany struktury.

## W1 — konsolidacja 4-klasowa (us 67 / pl 15 / em 8 / crypto 10)

Po włączeniu RBOT i INTRUM do worka `equity_us` (łącznie 68,7% vs target 67) — **0 transakcji**:
+1,7 / −0,1 / −0,0 / −1,6 p.p. — portfel w paśmie pod nową taksonomią.

**Co daje:** prostsza struktura (4 worki), rzadsze i tańsze rebalancingi, mniejsza wrażliwość
na szum pojedynczych klas (1% INTRUM przestaje „migotać" we własnym worku).
**Koszt:** utrata odrębnej kontroli nad ekspozycją tematyczną (robotyka) i pojedynczą akcją —
jeśli chcesz kiedyś ograniczyć RBOT niezależnie od S&P, klasa jest potrzebna.
**Wdrożenie (gdy wybierzesz):** edycja `data/ibkr_mapping.yaml` (RBOT.MI→equity_us,
INTRUM.ST→equity_us) + `config.yaml` targets → re-import → `run.py`. Zmiana czysto deklaratywna.

## W2 — krypto pod kontrolą (crypto 3%)

R1 crypto (+5,4 p.p.) → **SELL BITC.AS 41 308 + SELL WETH.PA 34 737 = 76 045 PLN**
(koszt est. 152 PLN). Brak dokupień: us jest pod targetem (−4,7 p.p.), ale **w paśmie** —
silnik nie rusza klas w paśmie (R1 prowadzi tylko klasy ponad próg, każda dokładnie do targetu).

**Operacyjnie:** 76 tys. PLN zostaje w gotówce, której system nie śledzi (portfolio.csv = pozycje).
Drogi wyjścia: (1) ręczne ulokowanie gotówki = wyjątek D3 z wpisem w protokole, (2) czekanie —
po sprzedaży udział us wzrośnie do ~60,6% (dryf −1,4), więc dokupienie US wypali dopiero przy
pogorszeniu; realnie to decyzja ręczna właściciela.
**Uwaga:** us jest dziś tylko **0,3 p.p. od progu** — przy W2 jeden słabszy miesiąc US odpali
automatyczne dokupienie z progu.

## W3 — tilt US (us 70 / pl 10 / em 0 / single 0)

Trzy reguły: R1 us (−12,7 → BUY 173 273 na 7 tickerach, z czego ~68,5 tys. w HX60 — Nasdaq 100),
R1 em (+8,0 → SELL EMQQ 109 055), **R2: obrót 20,7% > 20% → przeskalowanie ×0,967**
(obrót dokładnie 282 328 = 20,0% portfela; koszt est. 565 PLN).

**Pułapki:**
1. **Bilans +64 217 PLN** — kupna przewyższają sprzedaże o tyle, ile wynosi łączny dryf klas
   w paśmie (pl +4,9, sg +1,0, th +0,4, cr −1,6). Realizacja wymaga dopłaty gotówki albo
   świadomego pominięcia części zleceń (ręczna ingerencja w propozycję).
2. **To wariant „pościgu za wynikami"** — kierunek US/Nasdaq wyznacza ostatnie 8 miesięcy,
   czyli dokładnie błąd wskazany w debacie G1 jako bias agentów. Okno jest krótkie; jeśli
   wybierasz W3, rób to z tezą strukturalną (np. „chcę prosty portfel indeksowy US+resztka"),
   a nie z tabeli wyników.

## Odległości do progu R1 (dziś, per klasa)

Klasa zapali transakcję „samo", gdy dryf urośnie powyżej 5 p.p. — odległości: W0: us 2,7 ·
crypto 3,4 · sg 4,0 · th 4,6 · pl 4,9 · em 5,0 | W1: us 3,3 · crypto 3,4 · pl 4,9 · em 5,0 |
W2: crypto 0,0 (właśnie odpaliła) · us 0,3 | W3: us 0,0 · em 0,0 · pl 0,1.

## Ograniczenia analizy

- Ceny z cache 2026-09-04 09:13; kolejne bieganie tygodniowe odświeży kontekst.
- **Brak backtestu przyszłych cykli** (symulacji rebalancingów na historii) — to osobny moduł;
  ostateczną weryfikację strategii i tak robi paper trading (G4) i kryterium D1.
- Koszty = obrót × 0,2% (spread, podatki Belki i prowizje brokera nieujęte).
- Gotówka nie jest śledzona w `portfolio.csv` — sprzedaż bez dokupienia zmienia mianownik udziałów.

## Jak podjąć D5

Wybierz wariant (lub podaj własne liczby per klasa — suma = 100%) i wpisz do
[decyzje.md](decyzje.md) jako **D5**. Wdrożenie po decyzji:
- W0: nic (targety już w configu),
- W1: mapping + targets + re-import (ja robię),
- W2/W3: tylko `config.yaml` targets + `run.py` (protokół pokaże transakcje; egzekucja ręczna).