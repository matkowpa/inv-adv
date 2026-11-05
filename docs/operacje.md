# Operacje — cotygodniowy bieg i paper trading

> Stan: 2026-11-05. Dokument opisuje warstwę operacyjną, nie strategię.
> Strategia i decyzje: [plan-inv-adv.md](plan-inv-adv.md), [decyzje.md](decyzje.md).

## 1. Zasada: jeden punkt na tydzień

Historia (`reports/history.csv`) ma kolumnę `run_kind`:

| `run_kind` | Kiedy | Wpływ na metryki |
|---|---|---|
| `scheduled` | automatyczny bieg tygodniowy | **tylko ta seria** wchodzi do metryk D1 |
| `manual` | ręczne uruchomienie `python run.py` | nie wchodzi do metryk D1 |
| `smoke` | test/uruchomienie kontrolne | nie wchodzi do metryk D1 |

Bieg `scheduled` jest **idempotentny w obrębie tygodnia ISO**: ponowne
uruchomienie w tym samym tygodniu aktualizuje istniejący wiersz, nie dopisuje
duplikatu. Dzięki temu jeden tydzień = jeden punkt, nawet jeśli automat
uruchomi się dwa razy.

Metryki (`compute_metrics`) domyślnie liczą całą historię. W `run.py` są
filtrowane do `run_kind="scheduled"` i mają próg `paper_trading_weeks`
(domyślnie 12) — dopiero po tylu tygodniach pojawia się Sharpe w protokole.
Stare wiersze bez `run_kind` są traktowane jako `legacy` i nie wchodzą do
paper tradingu.

## 2. Uruchomienie

Ręcznie (bez wpływu na paper trading):

```bash
python run.py
```

Paper trading (jeden punkt na tydzień):

```bash
python run.py --scheduled
```

Pełny bieg operacyjny z logiem i dashboardem:

```bash
python scripts/weekly_run.py
```

`scripts/weekly_run.py` robi `run.py --scheduled` → `inv_adv.publish`, pisze
log do `reports/logs/run-YYYY-MM-DD.log` i — jeśli ustawisz
`INV_ADV_ALERT_WEBHOOK` — wysyła JSON POST przy błędzie. Nie wymaga
PowerShella; działa na Windows i Linux.

Po ręcznym wykonaniu zlecenia zapisz fill:

```bash
python -m inv_adv.execution --ticker SXR8.DE --side BUY \
  --quantity 10 --price 520.5 --fee 2.6 --note "IBKR fill"
```

Log trafia do `reports/executions/YYYY-MM.csv`. To audyt faktu, nie automatyczne
rozliczenie propozycji M2 — przy większej liczbie zleceń warto dodać
reconciliation (propozycja ↔ fill).

Na Windows nadal działa `scripts/weekly_run.ps1` (zaktualizowany o
`--scheduled`). Harmonogram: sobota 10:00, „StartWhenAvailable”.

## 3. Status i monitoring

Po każdym biegu `run.py` zapisuje `reports/status.json` (lokalny,
w `.gitignore`) z polami:

- `status`: `ok` / `error`,
- `run_kind`,
- `history_action`: `created` / `appended` / `updated`,
- `history_rows`, `scheduled_weeks`, `paper_trading_weeks`,
- `metrics_ready`,
- `protocol` (ścieżka),
- `error` (tylko przy błędzie).

To lekki manifest dla monitoringu — **bez wartości portfela i pozycji**.
Jeśli status nie zmienił się od ponad 8 dni, automat prawdopodobnie nie
działa.

## 4. Co zrobić, gdy bieg padnie

1. Sprawdź `reports/status.json` — pole `error` i `step`.
2. Sprawdź log `reports/logs/run-YYYY-MM-DD.log`.
3. Nie dopisuj punktu ręcznie „na siłę”. Po naprawie uruchom
   `python run.py --scheduled` w tym samym tygodniu — nadpisze punkt, jeśli
   zdążył powstać, albo doda go, jeśli nie.
4. Jeśli tydzień został pominięty, zostaw lukę. Metryki liczą rzeczywiste
   odstępy czasu; sztuczne wyrównywanie serii zafałszuje wynik.

## 5. Paper trading — zegar D1

`paper_trading_weeks` w `config.yaml` (domyślnie 12) to próg, po którym
pojawiają się metryki w protokole. **Nie** jest to jeszcze 12 miesięcy D1.
Kryterium D1 nadal wymaga 12 miesięcy paper tradingu; datę startu ustaw na
pierwszy czysty punkt `scheduled`, a nie na stare punkty `legacy`/`manual`.

Obecne 7 punktów z 4–10.09.2026 to prehistoria — 5 z nich powstało jednego
dnia. Nie traktuj ich jako tygodni paper tradingu.

## 6. Higiena danych

- `data/portfolio.csv`, `data/portfel_*.xlsx`, `site/` i `reports/status.json`
  są lokalne (`.gitignore`).
- `reports/history.csv` i `reports/decisions/` zawierają wartości — trzymaj
  repo prywatne; docelowo przenieś audyt do osobnego prywatnego repo.
- Logi (`reports/logs/`) są operacyjne; nie są audytem.
