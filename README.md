# inv-adv

System wspierania decyzji inwestycyjnych: **twardy rdzeń rebalancingu** (reguły, audyt, brak dyskrecji) + docelowo warstwa eksperymentalna LLM (komitet agentów, sentyment) — uruchamiana dopiero po przejściu gate'ów walidacyjnych.

## Status projektu

| Faza | Zakres | Status |
|---|---|---|
| **F0 — rdzeń MVP** | przegląd portfela (M1), silnik rebalancingu (M2), protokół decyzji (M3) | ✅ ukończona — działa na realnym portfelu z IBKR |
| **F1 — metryki i paper trading** | Sharpe/vol/drawdown vs benchmarki (S&P 500, Nasdaq-100), historia biegów (→ G4), cotygodniowy `run_kind=scheduled` | 🔄 metryki gotowe; paper trading wymaga ciągłego biegu (12 tygodni do metryk D1) |
| **F2 — eksperymenty LLM** | M4 komitet agentów (gate G1), M5 sentyment (gate G2) | 🔄 G1 wykonany → **FAIL**: M4 zawieszony (decyzja D6); G2 niewykonane |
| **F3 — skalowanie** | B2C / white-label | ⛔ zamrożona (analiza regulacyjna KNF/MiFID) |

Werdykt debaty rady modeli (Boardroom/idea-orch): **PIVOT** — rdzeń reguł budujemy od razu, warstwa LLM dopiero po walidacji. Pełna koncepcja: [docs/concept-boardroom.md](docs/concept-boardroom.md).

## Architektura

```
[Dane: eksport IBKR + Yahoo (akcje/ETF/krypto/FX)]
   → M1 przegląd portfela (wycena PLN, alokacja, dryf)
   → M2 silnik rebalancingu (R1: próg dryfu; R2: limit obrotu; zero dyskrecji)
   → M3 protokół decyzji (audyt) + historia snapshotów
   → [GATE'E G1–G4] → M4 komitet agentów / M5 sentyment (po walidacji)
```

## Funkcje (co działa)

- **Import z IBKR** — eksport `.xlsx` → `data/portfolio.csv` (mapowanie: `data/ibkr_mapping.yaml`)
- **Przegląd portfela (M1)** — wycena w PLN (kursy FX z Yahoo), alokacja per klasa, dryf vs targety
- **Silnik rebalancingu (M2)** — R1: \|dryf\| > próg (domyślnie 5 p.p.) → transakcja do targetu, kwota dzielona proporcjonalnie na tickery; R2: limit obrotu z proporcjonalnym przeskalowaniem; Rmin: minimalna kwota zlecenia; koszt transakcyjny w kwocie netto; deterministycznie, bez furtki (decyzja D3)
- **Protokół decyzji (M3)** — audytowalny markdown: dane wejściowe, pozycje, reguły z ID, transakcje, wyjątki ręczne
- **Metryki F1** — Sharpe/vol/max drawdown portfela vs benchmarki (S&P 500 = główny wg D1, dodatkowe np. Nasdaq-100): z historii biegów (od 3 punktów) oraz rekonstrukcja historyczna przy statycznym składzie
- **Lokalny dashboard** — samowystarczalny HTML (wykres base-100, alokacja, pełne pozycje) — **tylko lokalnie**

## Instalacja

```bash
pip install -r requirements.txt   # Python 3.12
```

## Polecenia

| Polecenie | Co robi |
|---|---|
| `python -m inv_adv.import_ibkr data/portfel_2026.09.01.xlsx` | eksport IBKR → `data/portfolio.csv` |
| `python run.py` | pełny cykl: ceny z Yahoo → M1 → M2 → protokół (+ cache `data/prices/`); bieg ręczny |
| `python run.py --scheduled` | bieg paper tradingu: jeden idempotentny punkt na tydzień ISO |
| `python scripts/weekly_run.py` | cotygodniowy bieg + dashboard + log + opcjonalny alert (Windows/Linux) |
| `python run.py --offline` | j.w. na cache — reprodukowalnie, bez sieci |
| `python -m inv_adv.metrics` | metryki z historii biegów (od 3 punktów) |
| `python -m inv_adv.history_rebuild --period 1y` | historyczne metryki (statyczny skład) → `reports/history_rebuilt.csv` |
| `python -m inv_adv.publish` | lokalny dashboard → `site/index.html` (pełne dane, nie publikować) |
| `python -m inv_adv.execution --ticker SXR8.DE --side BUY --quantity 10 --price 520.5 --fee 2.6` | ręczny zapis faktycznego fill do `reports/executions/` |
| `python scripts/whatif_targets.py` | analiza what-if wariantów targetów D5 (offline, silnik M2) |
| `python -m pytest` | testy jednostkowe (45, offline) |

## Konfiguracja

- **`config.yaml`** — waluta bazowa, **benchmarki** (`benchmarks:` — pierwszy = główny wg D1, kolejne porównawcze, np. Nasdaq-100; `spx_tr` to S&P 500 total return, na razie porównawczy), próg dryfu R1, limit obrotu R2, `transaction_cost_pct`, `min_trade_amount`, opcjonalne `lot_sizes`, `paper_trading_weeks`, `risk_free_annual`, **targety alokacji (decyzja właściciela — suma = 1.0)**
- **`data/ibkr_mapping.yaml`** — `Symbol|Waluta` z IBKR → ticker Yahoo + klasa aktywa
- **`data/portfolio.csv`** — pozycje (lokalne; regenerowane importem; wzór: `data/portfolio.example.csv`)
- **`data/prices_manual.csv`** — ręczne nadpisanie cen (`ticker,price`), np. dla ETF-ów z GPW, gdy Yahoo bywa nieaktualne

## Cykl pracy

1. **Miesięcznie**: nowy eksport IBKR → `python -m inv_adv.import_ibkr <plik>` → `python run.py`
2. **Tygodniowo — automat**: zadanie Harmonogramu Windows `inv-adv-weekly` (sobota 10:00; `scripts/weekly_run.ps1`; StartWhenAvailable — nadrabia po wyłączeniu komputera; log `reports/logs/`): `run.py --scheduled` + dashboard; przy błędzie punkt historii NIE jest dopisywany. Wersja przenośna: `python scripts/weekly_run.py` (Windows/Linux).
3. Decyzje wg protokołu; egzekucja zawsze ręczna (jednomyślna decyzja rady)

## Artefakty

- `reports/decisions/*.md` — protokoły decyzji (audyt)
- `reports/history.csv` — historia biegów (metryki F1, gate G4); kolumna `run_kind` rozdziela `scheduled` / `manual` / `smoke`
- `reports/history_rebuilt.csv` — zrekonstruowana seria (statyczny skład)
- `reports/executions/*.csv` — faktyczne fill-e (ręczny log, audyt wykonania)
- `reports/status.json` — status ostatniego biegu (lokalny, w `.gitignore`)
- `site/index.html` — lokalny dashboard (pełne dane; w `.gitignore`, nie publikować)

## Dokumentacja

- [docs/plan-inv-adv.md](docs/plan-inv-adv.md) — plan przedsięwzięcia + podjęte decyzje D1–D6
- [docs/concept-boardroom.md](docs/concept-boardroom.md) — koncepcja z debaty rady (werdykt PIVOT, ryzyka, gate'e)
- [docs/g1-wynik.md](docs/g1-wynik.md) — wynik gate'a G1 (test komitetu agentów): FAIL, M4 zawieszony, decyzja D6
- [docs/what-if-targets.md](docs/what-if-targets.md) — analiza what-if wariantów targetów (wsparcie decyzji D5)
- [docs/metodologia.md](docs/metodologia.md) — logika i metodologia systemu krok po kroku
- [docs/operacje.md](docs/operacje.md) — cotygodniowy bieg, `run_kind`, status, alerty
- [docs/decyzje.md](docs/decyzje.md) — rejestr decyzji właściciela
- Wyjściowy opis pomysłu: [TODOs.txt](TODOs.txt)

## Prywatność

Repo **musi być prywatne**. Jeśli widzisz je publicznie, to błąd konfiguracji —
natychmiast zmień widoczność i wyczyść historię: `data/portfel_*.xlsx` oraz
`data/portfolio.csv` były commitowane w przeszłości (m.in. `80f68b0`, `d62f309`)
i pozostają w historii nawet po usunięciu z HEAD. Protokoły w `reports/` oraz
log fill-e `reports/executions/` zawierają wartości pozycji — świadomy wybór
(audyt) przy prywatnym repo. Docelowo trzymaj audyt i dane w osobnym prywatnym
repo/zaszyfrowanym wolumenie, a nie w repo kodu.

Dane pozycyjne (`data/portfel_*.xlsx`, `data/portfolio.csv`) i dashboard (`site/`)
są w `.gitignore` — pozostają wyłącznie lokalnie. `reports/status.json` też jest
lokalny. Przy ewentualnym upublicznieniu wymagane czyszczenie historii gita
(plik xlsx występuje w historii).