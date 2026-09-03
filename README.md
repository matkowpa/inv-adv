# inv-adv

System wspierania decyzji inwestycyjnych oparty o wieloagentowy komitet inwestycyjny.

## Cel

Zarządzanie własnym kapitałem zainwestowanym w płynne aktywa finansowe (akcje, obligacje, ETF-y) — pomnażanie majątku przy jednoczesnym ograniczaniu ryzyka.

## Zakres

1. **Przegląd portfela** — bieżący podgląd i ocena istniejącego portfela.
2. **Rebalancing** — decyzje rebalancingowe podejmowane na podstawie ścisłych kryteriów.
3. **Sentyment rynkowy** — inwestycje w aktywa zgodnie z wyłapywanym sentymentem rynkowym.

## Komitet inwestycyjny

Decyzje podejmuje komitet złożony z agentów, m.in.: dyrektora inwestycyjnego, szefa ryzyka i analityków. Komitet deliberuje w kilku rundach dyskusji, a jego głównym celem jest zaproponowanie i realizacja przyjętej strategii inwestycyjnej.

## Status

Faza planowania — wyjściowy opis pomysłu: [TODOs.txt](TODOs.txt).

## Uruchomienie (F0 — MVP rdzenia)

1. `pip install -r requirements.txt`
2. Uzupełnij `data/portfolio.csv` (wzór: [data/portfolio.example.csv](data/portfolio.example.csv)) i targety w `config.yaml` (decyzja D1).
3. `python run.py` — pobiera ceny z Yahoo (akcje/ETF/krypto + FX), generuje protokół decyzji i dopisuje wiersz do historii.
   `python run.py --offline` — używa cache z `data/prices/` (bez sieci, reprodukowalnie).

Wyniki: `reports/decisions/*.md` (audyt) i `reports/history.csv` (buduje serię pod metryki w F1).
Metryki F1 (Sharpe/drawdown/vol vs S&P 500) w protokole od 3 punktów historii; podgląd: `python -m inv_adv.metrics`.

## Import portfela z IBKR

1. Eksport pozycji z IBKR (.xlsx) zapisz w `data/` (kolumny: Currency, Symbol, Description, Quantity, ...).
2. Mapowanie pozycji: `data/ibkr_mapping.yaml` (klucz `Symbol|Waluta` → ticker Yahoo + klasa aktywa).
3. `python -m inv_adv.import_ibkr data/portfel_2026.09.01.xlsx` — pisze `data/portfolio.csv`.
4. `python run.py` — protokół na realnych danych.

Pozycje ze słabymi danymi Yahoo (np. ETF-y z GPW): ręczna cena w `data/prices_manual.csv`
(kolumny `ticker,price`) — nadpisuje Yahoo również w trybie offline (odnotowane w protokole).
Plan przedsięwzięcia: [docs/plan-inv-adv.md](docs/plan-inv-adv.md).