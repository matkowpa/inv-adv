# G1 — test wieloagentowego komitetu inwestycyjnego na realnej migawce portfela

## Kontekst

Projekt inv-adv — osobisty system wsparcia decyzji inwestycyjnych z twardym rdzeniem
rebalancingu (reguły, audyt, zero dyskrecji). Rozważamy dodanie warstwy eksperymentalnej:
**wieloagentowy komitet inwestycyjny (LLM)**, który cyklicznie dyskutuje alokację
portfela i proponuje zmiany. Warstwa miałaby charakter wyłącznie doradczy — system nigdy
nie wykonuje zleceń automatycznie, a komitet nie ma furtki w silniku reguł.

Ten test (gate G1) odpowiada na pytanie: **czy komitet LLM wytwarza użyteczną, liczbowa,
rozbieżną treść — czy jest tylko „teatrem multi-agentowym"?** Debata rady modeli
(pomysł inv-adv) wskazała to jako główne ryzyko warstwy LLM.

## Migawka portfela (2026-09-04, waluta bazowa PLN, wartość 1 411 641 PLN)

| klasa | udział | target | dryf [p.p.] | instrumenty (Yahoo) |
|---|---|---|---|---|
| equity_us | 57,3% | 55% | +2,3 | iShares Core S&P 500 (SXR8.DE), Vanguard S&P 500 Acc (VUAA.DE), UBS Nasdaq 100 (BCFP.DE), iShares Nasdaq 100 T30 (HX60.DE), SPDR US Financials (ZPDF.DE), iShares Nasdaq US Biotech (2B70.DE), iShares S&P Consumer Discretionary (IUCD.L) |
| equity_pl | 14,9% | 15% | −0,1 | Beta ETF mWIG40TR (ETFBM40TR.WA) |
| equity_thematic | 10,4% | 10% | +0,4 | iShares Automation & Robotics (RBOT.MI) |
| equity_em | 8,0% | 8% | −0,0 | EMQQ Emerging Markets Internet (EMQQ.DE + EMQQ.L) |
| equity_single | 1,0% | 2% | −1,0 | Intrum AB (INTRUM.ST, pojedyncza akcja) |
| crypto | 8,4% | 10% | −1,6 | CoinShares Physical Bitcoin (BITC.AS), WisdomTree Physical Ethereum (WETH.PA) |

Reguły R1/R2 nie odpaliły (portfel w paśmie ±5 p.p.) — transakcje: 0.

## Wyniki historyczne (rekonstrukcja przy statycznym składzie, 2026-01-08 → 2026-09-04)

| metryka | portfel | S&P 500 (PLN) | Nasdaq-100 (PLN) |
|---|---|---|---|
| wynik okresu | −1,1% | +15,4% | +19,2% |
| zmienność roczna | 18,2% | 16,4% | 23,2% |
| Sharpe (rf=0%) | −0,09 | 1,50 | 1,33 |
| max drawdown | −13,2% | −7,0% | −9,2% |

Kryterium porażki projektu (decyzja właściciela, D1): Sharpe portfela < Sharpe S&P 500
po 12 miesiącach paper tradingu ⇒ koniec projektu. Profil właściciela: 100% akcje +
krypto (bez obligacji), horyzont długi, tolerancja na zmienność umiarkowana.

## Zasady twarde systemu (niepodlegające dyskusji)

- Silnik rebalancingu czysto regułowy: \|dryf\| > 5 p.p. ⇒ transakcja do targetu; limit obrotu 20%/cykl.
- Zero automatycznej egzekucji (jednomyślna decyzja rady przy powstaniu projektu).
- Zero dyskrecji w silniku; wyjątki tylko ręcznie, z wpisem w audycie.

## Pytanie do komitetu

Każdy z Was ocenia obecną alokację i wyniki vs benchmarki, a następnie proponuje
**KONKRETNE docelowe targety** — procenty dla każdej z 6 klas (equity_us, equity_pl,
equity_thematic, equity_em, equity_single, crypto; suma = 100%), krótkie uzasadnienie
oraz najważniejsze ryzyko swej propozycji. Liczby są obowiązkowe — bez nich rekomendacja
nie wchodzi do pomiaru gate'a.

## Pomiar gate'a G1 (zdefiniowany PRZED debatą — bez retroakcji)

- Z pierwszej rundy ekstrahowany zostaje wektor targetów od każdego agenta
  (brak liczb = „brak rekomendacji").
- **Rozbieżność** = średnia parowa odległość L1 między wektorami targetów agentów
  (w punktach procentowych; L1 = suma bezwzględnych różnic wag per klasa).
- **G1 PRZEJŚCIE:** ≥ 2/3 agentów podaje liczby ORAZ rozbieżność ≥ 30 p.p.
- **G1 PORAŻKA:** poniżej progu ⇒ M4 (komitet agentów) porzucamy jako „teatr
  multi-agentowy"; warstwa LLM nie powstanie.