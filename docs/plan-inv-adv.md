# Plan przedsięwzięcia: inv-adv (Osobisty Komitet Inwestycyjny)

> Dokument realizuje zapis z [TODOs.txt](../TODOs.txt): plan rozwiązania/aplikacji i zarys założeń.
> Uwzględnia werdykt **PIVOT** z debaty Boardroom (idea-orch) — pełna koncepcja z rejestrem ryzyk
> i pytaniami otwartymi: [concept-boardroom.md](concept-boardroom.md) (oryginał: `idea-orch\sessions\inv-adv\`).

## 1. Cel

Zarządzanie własnym kapitałem w płynnych aktywach (akcje, obligacje, ETF-y): pomnażanie majątku
przy ograniczaniu ryzyka. System wprowadza **dyscyplinę i audytowalność**: twarde reguły
rebalancingu, ścisłe limity ryzyka, protokół każdej decyzji.

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
  M1 przegląd portfela   M2 silnik rebalancingu   M3 log/raporty + benchmark 60/40
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
| **M2 Silnik rebalancingu** | ścisłe progi (np. dryf ±5 p.p. od targetu), kolejność transakcji, limit kosztów/obrotu; bez furtki dyskrecjonalnej — wyjątki tylko przez wpis w logu | lista proponowanych transakcji |
| **M3 Log i raporty** | protokół decyzji, benchmark 60/40, historia dryfu | raport + audytowalny zapis |

### Gate'e przed komponentami LLM (warunki z werdyktu PIVOT)

| # | Gate | Kryterium przejścia |
|---|---|---|
| G1 | Test rozbieżności komitetu | ≥30% różnicy rekomendacji agentów na identycznych danych; porażka = M4 trwale skasowany |
| G2 | Backtest sentymentu | wykazana moc predykcyjna; porażka = zero linii kodu M5 |
| G3 | Rachunek kosztów | koszty danych+LLM < 0,3–0,5% wartości portfela rocznie; sporządzony PRZED dalszym developmentem |
| G4 | Paper trading | 6–12 mies. bezbłędnego działania przed jakąkolwiek automatyzacją egzekucji |

### Moduły eksperymentalne (dopiero po gate'ach)

- **M4 Komitet agentów** — dyrektor inwestycyjny (CIO), szef ryzyka, analityk(-ci); decyzje
  w rundach dyskusji (runda 1: opinie niezależne — anti-groupthink; runda 2: agenci widzą
  opinie pozostałych); zróżnicowane modele LLM per rola. Wzorzec i gotowy kod: repo `idea-orch`
  (LiteLLM + OpenRouter, pliki markdown jako szyna komunikacji, syntezy moderatora, protokół debaty).
- **M5 Sentyment rynkowy** — indeksy sentymentu jako filtr tempa działań; implementacja wyłącznie po G2.

## 4. Stack i dane

- Python 3.12; pandas do obliczeń portfelowych; git jako magazyn raportów i protokołów.
- Dane rynkowe: na start wyceny własne (CSV/Excel); kursy benchmarku z darmowego źródła
  (np. Stooq lub yfinance) — wybór źródła do decyzji przy implementacji M1.
- Warstwa LLM (tylko M4/M5, po gate'ach): LiteLLM + OpenRouter — jedna konfiguracja z idea-orch.

## 5. Fazy realizacji

| Faza | Zakres | Kryterium zamknięcia |
|---|---|---|
| **F0 — MVP rdzenia** | M1+M2+M3 na danych własnych; pierwszy pełny cykl przegląd → rebalancing → log | protokół decyzji wygenerowany end-to-end |
| **F1 — metryki i paper trading** | metryki ryzyka vs 60/40; cykliczne decyzje w trybie paper | ≥6 mies. bezbłędnego paper tradingu (G4) |
| **F2 — eksperymenty LLM** | testy G1–G3; warunkowo M4/M5 | wyniki testów: wdrożenie modułu lub trwałe skasowanie |
| **F3 — skalowanie (zamrożona)** | B2C / white-label | wyłącznie po analizie regulacyjnej (MiFID/KNF) |

## 6. Ryzyka (z debaty, skrót)

1. „Teatr multi-agentowy” — wysoka korelacja błędów agentów → weryfikacja przez G1.
2. Sentyment bez mocy predykcyjnej (wzmacnianie szumu) → G2.
3. Furtki dyskrecjonalne osłabiające rygor reguł → M2 bez furtki; wyjątki tylko przez log.
4. Ekonomika: szacowane koszty danych/LLM 1,5–15 tys. USD/rok → G3.
5. Regulacje przy skalowaniu (MiFID/KNF) → F3 zamrożona do analizy prawnej.
6. Brak zdefiniowanego progu porażki projektu → patrz pkt 7.1.

## 7. Pytania otwarte (decyzje właściciela przed F0)

> Odpowiedzi spisuj w [decyzje.md](decyzje.md) — po uzupełnieniu zostaną przeniesione tutaj jako podjęte decyzje.

1. Próg porażki: jaka metryka/benchmark/okres kończy pracę nad projektem?
2. Wielkość portfela i budżet na dane/LLM — dane wejściowe do G3.
3. Czy w ogóle dopuszczamy „obszar dyskrecjonalny”? Jeśli tak — operacyjny podział progi twarde vs dyskrecja (debata nie dopracowała podziału).
4. Źródło danych rynkowych dla M1 i benchmarku.