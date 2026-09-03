# Plan przedsięwzięcia: inv-adv (Osobisty Komitet Inwestycyjny)

> Dokument realizuje zapis z [TODOs.txt](../TODOs.txt): plan rozwiązania/aplikacji i zarys założeń.
> Uwzględnia werdykt **PIVOT** z debaty Boardroom (idea-orch) — pełna koncepcja z rejestrem ryzyk
> i pytaniami otwartymi: [concept-boardroom.md](concept-boardroom.md) (oryginał: `idea-orch\sessions\inv-adv\`).

## 1. Cel

Zarządzanie własnym kapitałem w płynnych aktywach: pomnażanie majątku przy ograniczaniu ryzyka.
Zgodnie z decyzją D1 właściciela profil portfela to **100% akcje i aktywa ryzykowne (w tym
krypto)** — obligacje nie są częścią targetu; benchmark: S&P 500. System wprowadza **dyscyplinę
i audytowalność**: twarde reguły rebalancingu, ścisłe limity ryzyka, protokół każdej decyzji.

## 2. Kluczowe założenia

1. **Self-use (faza 1)** — decyzje podejmuje właściciel; system doradza i dokumentuje.
2. **Reguły > dyskrecja** — rebalancing na podstawie ścisłych, liczbowych kryteriów.
3. **Sentyment = filtr, nie sygnał** — może modyfikować tempo działań, nigdy nie jest podstawą decyzji.
4. **Bez automatycznej egzekucji** — zlecenia składa człowiek (jednomyślny wniosek rady);
   automatyzacja dopiero po 6–12 mies. paper-tradingu.
5. **Audytowalność** — każda decyzja ma wpis w logu: dane wejściowe → reguła → decyzja.

## 3. Architektura: twardy rdzeń + zawieszony obszar eksperymentów

Werdykt PIVOT wymusza dwuwarstwowy model:

```
[ Dane rynkowe / wyceny portfela ]
        │
        ▼
[ RDZEŃ (MVP, bez LLM) ]
  M1 przegląd portfela   M2 silnik rebalancingu   M3 log/raporty + benchmark S&P 500
        │
        ▼
[ GATE'E walidacyjne ] ── brak przejścia = komponent pozostaje zawieszony
        │
        ▼
[ EKSPERYMENTY (LLM) ]
  M4 komitet agentów (wzorzec idea-orch)   M5 sentyment rynkowy
```

### Moduły rdzenia (MVP)

| Moduł | Zakres | Wyjście |
|---|---|---|
| **M1 Przegląd portfela** | import wycen/pozycji, alokacja per klasa aktywów, dryf od targetów, metryki (Sharpe, max drawdown vs benchmark) | migawka portfela |
| **M2 Silnik rebalancingu** | ścisłe progi (np. dryf ±5 p.p. od targetu), kolejność transakcji, limit kosztów/obrotu; bez furtki dyskrecjonalnej (decyzja D3: NIE) — wyjątek tylko ręcznie, z wpisem w logu | lista proponowanych transakcji |
| **M3 Log i raporty** | protokół decyzji, benchmark S&P 500 (decyzja D1), historia dryfu | raport + audytowalny zapis |

### Gate'e przed komponentami LLM (warunki z werdyktu PIVOT)

| # | Gate | Kryterium przejścia |
|---|---|---|
| G1 | Test rozbieżności komitetu | ≥30% różnicy rekomendacji agentów na identycznych danych; porażka = M4 trwale skasowany |
| G2 | Backtest sentymentu | wykazana moc predykcyjna; porażka = zero linii kodu M5 |
| G3 | Rachunek kosztów | koszty danych+LLM < 0,3–0,5% wartości portfela rocznie — **PRZEJŚCIE (D2)**: 2 000/rok = 0,2% z 1 000 000; sporządzony PRZED dalszym developmentem |
| G4 | Paper trading | 6–12 mies. bezbłędnego działania przed jakąkolwiek automatyzacją egzekucji |

### Moduły eksperymentalne (dopiero po gate'ach)

- **M4 Komitet agentów** — dyrektor inwestycyjny (CIO), szef ryzyka, analityk(-ci); decyzje
  w rundach dyskusji (runda 1: opinie niezależne — anti-groupthink; runda 2: agenci widzą
  opinie pozostałych); zróżnicowane modele LLM per rola. Wzorzec i gotowy kod: repo `idea-orch`
  (LiteLLM + OpenRouter, pliki markdown jako szyna komunikacji, syntezy moderatora, protokół debaty).
- **M5 Sentyment rynkowy** — indeksy sentymentu jako filtr tempa działań; implementacja wyłącznie po G2.

## 4. Stack i dane

- Python 3.12; pandas do obliczeń portfelowych; git jako magazyn raportów i protokołów.
- Dane rynkowe (decyzja D4): benchmarki i dane rynkowe ze źródeł publicznych (Stooq, Yahoo
  i inne) lub API brokera (np. XTB); skład portfela (pozycje i ilości) — z własnych zapisów (CSV).
- Warstwa LLM (tylko M4/M5, po gate'ach): LiteLLM + OpenRouter — jedna konfiguracja z idea-orch.

## 5. Fazy realizacji

| Faza | Zakres | Kryterium zamknięcia |
|---|---|---|
| **F0 — MVP rdzenia** | M1+M2+M3 na danych własnych; pierwszy pełny cykl przegląd → rebalancing → log | protokół decyzji wygenerowany end-to-end |
| **F1 — metryki i paper trading** | metryki ryzyka vs S&P 500; cykliczne decyzje w trybie paper | ≥6 mies. bezbłędnego paper tradingu (G4) |
| **F2 — eksperymenty LLM** | testy G1–G3; warunkowo M4/M5 | wyniki testów: wdrożenie modułu lub trwałe skasowanie |
| **F3 — skalowanie (zamrożona)** | B2C / white-label | wyłącznie po analizie regulacyjnej (MiFID/KNF) |

Próg porażki projektu (decyzja D1): jeśli po 12 mies. paper tradingu Sharpe projektu <
Sharpe S&P 500 — projekt zamykamy. Benchmark 60/40 z rekomendacji rady został nadpisany
decyzją właściciela (profil 100% ryzykowny).

## 6. Ryzyka (z debaty, skrót)

1. „Teatr multi-agentowy” — wysoka korelacja błędów agentów → weryfikacja przez G1.
2. Sentyment bez mocy predykcyjnej (wzmacnianie szumu) → G2.
3. Furtki dyskrecjonalne osłabiające rygor reguł → M2 bez furtki; wyjątki tylko przez log.
4. Ekonomika: szacowane koszty danych/LLM 1,5–15 tys. USD/rok → G3.
5. Regulacje przy skalowaniu (MiFID/KNF) → F3 zamrożona do analizy prawnej.
6. Próg porażki projektu — zdefiniowany (decyzja D1): Sharpe < Sharpe S&P 500 po 12 mies. paper tradingu → koniec projektu.

## 7. Podjęte decyzje właściciela (D1–D4)

> Pełne uzasadnienia i przebieg podejmowania: [decyzje.md](decyzje.md).

| # | Decyzja | Treść | Skutek w planie |
|---|---|---|---|
| D1 | Próg porażki | Portfel 100% akcje + aktywa ryzykowne (krypto); benchmark = S&P 500; jeśli po 12 mies. paper tradingu Sharpe projektu < Sharpe S&P 500 → projekt zamykamy | benchmark 60/40 → S&P 500 (§1, §3, §5); uniwersum aktywów z krypto |
| D2 | Portfel i budżet | Portfel 1 000 000; dane 1 000/rok; LLM 1 000/rok → razem 2 000/rok = 0,2% portfela | **G3: PRZEJŚCIE** — ekonomika nie blokuje developmentu |
| D3 | Obszar dyskrecjonalny | NIE — system zawsze wykonuje regułę; wyjątek tylko ręcznie, z wpisem w logu | M2 bez furtki dyskrecjonalnej |
| D4 | Źródło danych | Źródła publiczne (Stooq, Yahoo i inne) lub API brokera (np. XTB) | §4: dane rynkowe |

Założenie do D2: wszystkie trzy liczby w tej samej walucie.