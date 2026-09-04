# inv-adv

System wspierania decyzji inwestycyjnych: **twardy rdzeń rebalancingu** (reguły, audyt, brak dyskrecji) + docelowo warstwa eksperymentalna LLM (komitet agentów, sentyment) — uruchamiana dopiero po przejściu gate'ów walidacyjnych.

## Status projektu

| Faza | Zakres | Status |
|---|---|---|
| **F0 — rdzeń MVP** | przegląd portfela (M1), silnik rebalancingu (M2), protokół decyzji (M3) | ✅ ukończona — działa na realnym portfelu z IBKR |
| **F1 — metryki i paper trading** | Sharpe/vol/drawdown vs benchmarki (S&P 500, Nasdaq-100), historia biegów (→ G4) | 🔄 metryki gotowe; historia się buduje |
| **F2 — eksperymenty LLM** | M4 komitet agentów (gate G1), M5 sentyment (gate G2) | ⬜ za gate'ami walidacyjnymi |
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
- **Silnik rebalancingu (M2)** — R1: \|dryf\| > próg (domyślnie 5 p.p.) → transakcja do targetu, kwota dzielona proporcjonalnie na tickery; R2: limit obrotu z proporcjonalnym przeskalowaniem; deterministycznie, bez furtki (decyzja D3)
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
| `python run.py` | pełny cykl: ceny z Yahoo → M1 → M2 → protokół (+ cache `data/prices/`) |
| `python run.py --offline` | j.w. na cache — reprodukowalnie, bez sieci |
| `python -m inv_adv.metrics` | metryki z historii biegów (od 3 punktów) |
| `python -m inv_adv.history_rebuild --period 1y` | historyczne metryki (statyczny skład) → `reports/history_rebuilt.csv` |
| `python -m inv_adv.publish` | lokalny dashboard → `site/index.html` (pełne dane, nie publikować) |
| `python -m pytest` | testy jednostkowe (34, offline) |

## Konfiguracja

- **`config.yaml`** — waluta bazowa, **benchmarki** (`benchmarks:` — pierwszy = główny wg D1, kolejne porównawcze, np. Nasdaq-100), próg dryfu R1, limit obrotu R2, `risk_free_annual`, **targety alokacji (decyzja właściciela — suma = 1.0)**
- **`data/ibkr_mapping.yaml`** — `Symbol|Waluta` z IBKR → ticker Yahoo + klasa aktywa
- **`data/portfolio.csv`** — pozycje (lokalne; regenerowane importem; wzór: `data/portfolio.example.csv`)
- **`data/prices_manual.csv`** — ręczne nadpisanie cen (`ticker,price`), np. dla ETF-ów z GPW, gdy Yahoo bywa nieaktualne

## Cykl pracy

1. **Miesięcznie**: nowy eksport IBKR → `python -m inv_adv.import_ibkr <plik>` → `python run.py`
2. **Tygodniowo** (docelowo automat): `python run.py` — buduje historię pod metryki i gate G4
3. Decyzje wg protokołu; egzekucja zawsze ręczna (jednomyślna decyzja rady)

## Artefakty

- `reports/decisions/*.md` — protokoły decyzji (audyt)
- `reports/history.csv` — historia biegów (metryki F1, gate G4)
- `reports/history_rebuilt.csv` — zrekonstruowana seria (statyczny skład)
- `site/index.html` — lokalny dashboard (pełne dane; w `.gitignore`, nie publikować)

## Dokumentacja

- [docs/plan-inv-adv.md](docs/plan-inv-adv.md) — plan przedsięwzięcia + podjęte decyzje D1–D4
- [docs/concept-boardroom.md](docs/concept-boardroom.md) — koncepcja z debaty rady (werdykt PIVOT, ryzyka, gate'e)
- [docs/decyzje.md](docs/decyzje.md) — rejestr decyzji właściciela
- Wyjściowy opis pomysłu: [TODOs.txt](TODOs.txt)

## Prywatność

Repo **prywatne**. Dane pozycyjne (`data/portfel_*.xlsx`, `data/portfolio.csv`) i dashboard (`site/`) są w `.gitignore` — pozostają wyłącznie lokalnie. Protokoły w `reports/` zawierają wartości pozycji — świadomy wybór (audyt) przy prywatnym repo; przy ewentualnym upublicznieniu wymagane czyszczenie historii gita (plik xlsx występuje w historii).