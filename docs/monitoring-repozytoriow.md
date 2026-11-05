# Monitoring repozytoriów i jobów — schemat działania

> Stan na **2026-11-05**. Dokument opisuje działający system dashboardu
> „Joby i projekty”, nie projekt `models-monitoring` (ten monitoruje modele
> ClinePass i ma osobny mechanizm publikacji).
>
> **Wersja publiczna.** Z oryginału usunięto wewnętrzny adres Tailscale
> i identyfikator czatu Telegram. Pełna wersja pozostaje w prywatnym repo
> z analizami (folder `infrastruktura/`).

## 1. Co ten system monitoruje

Dashboard zbiera w jednym miejscu:

- **joby Hermesa** — harmonogram, ostatni run, historię 30 dni, błędy,
  czas wykonania, dostarczenie, koszt modeli;
- **repozytoria GitHub** — CI, PR-y, issues, branche, Pages, ostatni commit,
  wiek ostatniego pushu;
- **alerty** — wyliczane z powyższych danych, z oceną 0–10 i poziomem
  ważności;
- **koszty modeli** — szacowane z logu API, z podziałem na joby i rozmowy
  poza cronem.

To **nie jest** monitoring jakości kodu ani bezpieczeństwa zależności.
Sprawdza stan operacyjny repozytoriów i jobów.

## 2. Skrót — dwa joby i jeden serwer

| Element | Wartość |
|---|---|
| Job dashboardu | `Dashboard: joby + repozytoria (odświeżanie)` |
| ID | `407a626270f2` |
| Harmonogram | `*/30 * * * *` — co 30 minut |
| Typ | `no_agent: true` — czysty skrypt, bez modelu |
| Skrypt | `/opt/data/scripts/dashboard-build.sh` |
| Wynik | `index.html`, `data.json`, `data/repo_history.json` |
| Job alertów | `Dashboard: alerty na Telegram (tylko zmiany)` |
| ID | `556c1b28e92e` |
| Harmonogram | `5,35 * * * *` — co 30 minut, o :05 i :35 |
| Typ | `no_agent: true` — czysty skrypt, bez modelu |
| Skrypt | `/opt/data/scripts/alert-push.sh` |
| Wynik | Telegram tylko przy nowych/ustąpionych alertach |
| Serwer | `serve.py` na `0.0.0.0:8765` |
| Adres w tailnecie | `https://<tailnet-host>/monitor/` |

Oba joby są wpisane w `cron/jobs.json` i uruchamiane przez scheduler Hermesa
w kontenerze. **Nie są to GitHub Actions** i nie wymagają publicznego repo.

## 3. Przepływ danych

```
cron/jobs.json ─────────────┐
cron/executions.db ─────────┤
logs/agent.log ─────────────┤
                             ▼
                    monitoring/build.py
                    ├─ sources.py       (cron, log, GitHub API)
                    ├─ build_alerts()   (reguły i scoring)
                    └─ render.py        (jeden statyczny HTML)
                             │
              ┌──────────────┼──────────────────┐
              ▼              ▼                  ▼
        index.html       data.json      data/repo_history.json
              │
              ▼
        serve.py :8765 ──► tailscale serve /monitor/
              │
              ▼
        alertpush.py ──► Telegram (tylko zmiany)
```

`build.py` jest deterministyczny: nie wywołuje modelu, nie streszcza i nie
interpretuje danych. Wszystkie liczby pochodzą z API/logów albo są jawnie
oznaczone jako szacunek.

## 4. Jak system jest odpalany

### 4.1. Automatycznie

Scheduler Hermesa budzi job `407a626270f2` co 30 minut. Job ma
`no_agent: true`, więc uruchamia `dashboard-build.sh` jako proces, bez
tworzenia sesji agenta i bez wywołania LLM.

`dashboard-build.sh`:

1. wchodzi do `/opt/data/monitoring`;
2. uruchamia `python3 build.py`;
3. sprawdza, czy `http://127.0.0.1:8765/index.html` odpowiada;
4. jeśli serwer nie działa, startuje `nohup python3 serve.py >> http.log 2>&1 &`
   i ponownie sprawdza zdrowie strony;
5. przy błędzie builda lub martwym serwerze kończy się kodem ≠ 0.

Job `556c1b28e92e` uruchamia `alert-push.sh` o :05 i :35. Skrypt wchodzi do
`/opt/data/monitoring` i uruchamia `python3 alertpush.py`. Ten czyta
`data.json` oraz `data/alert_state.json` i wypisuje wyłącznie zmiany. Puste
wyjście oznacza brak wiadomości — cron nie wysyła wtedy nic.

### 4.2. Ręcznie

```bash
# pełne odświeżenie + pilnowanie serwera
/opt/data/scripts/dashboard-build.sh

# samo wygenerowanie plików
cd /opt/data/monitoring && python3 build.py

# wysłanie różnic alertów (bez zmian = brak wiadomości)
/opt/data/scripts/alert-push.sh

# sam serwer (zwykle nie trzeba — dashboard-build.sh go pilnuje)
cd /opt/data/monitoring && python3 serve.py
```

### 4.3. Czas

- Wyrażenia cron są minutowe (`*/30`, `5,35`), więc zmiana czasu letniego/
  zimowego nie zmienia odstępów.
- `generated_at` w `data.json` i daty na stronie są w **Europe/Warsaw**.
- Scheduler przechowuje `next_run_at` w UTC; to normalne, że w `jobs.json`
  widać UTC, a strona pokazuje czas lokalny.

## 5. Źródła danych — dokładnie

### 5.1. Joby

| Plik | Co jest czytane |
|---|---|
| `/opt/data/cron/jobs.json` | definicje jobów: nazwa, harmonogram, `no_agent`, `deliver`, stan, ostatni błąd |
| `/opt/data/cron/executions.db` | historia wykonań: `job_id`, `status`, `started_at`, `finished_at`, `error`, `delivery_outcome` |

Okno: **30 dni** (`WINDOW_DAYS = 30`). Dla każdego joba liczone są m.in.:
liczba runów, sukcesy, błędy, mediana czasu, seria porażek, opóźnienie
(`overdue`), błąd dostarczenia. Job uznaje się za opóźniony, gdy jego
`next_run_at` minął ponad **90 minut** temu (`grace_minutes=90`).

### 5.2. Log modeli

`/opt/data/logs/agent.log` jest parsowany regexem po liniach:

```
API call #N: model=... provider=... in=... out=... total=... latency=...s
```

Z sesji `cron_<job_id>_<timestamp>` dashboard przypisuje wywołanie do joba.
Dla każdego joba i dla rozmów poza cronem liczy: liczbę wywołań, tokeny
wejścia/wyjścia, cache, medianę latencji i **szacowany** koszt.

Stawki są w `monitoring/rates.json` — to referencyjne stawki ClinePass
(`retrieved_at: 2026-10-02`). Koszt jest **szacunkiem**, nie fakturą:
subskrypcja ClinePass rozlicza się ryczałtem. Modele bez stawki trafiają do
`unpriced_models`, a ich koszt nie jest zgadywany.

### 5.3. GitHub

Token jest brany z `GITHUB_TOKEN` (env) albo z `/opt/data/.env`. Dashboard
wywołuje REST API:

1. `GET /user/repos?per_page=100&sort=pushed&affiliation=owner,collaborator`
   — **lista jest dynamiczna**, nie ma ręcznej listy repozytoriów. Nowe repo
   pojawia się w dashboardzie po następnym przebiegu.
2. Dla każdego repo:
   - `GET /repos/{full}/actions/runs?per_page=10` — najnowszy run CI i mediana
     czasów udanych runów;
   - `GET /repos/{full}/pulls?state=open&per_page=20` — do 5 PR-ów na stronie,
     plus review każego z tych 5;
   - `GET /repos/{full}/issues?state=open&per_page=50` — issues (bez PR-ów);
   - `GET /repos/{full}/commits?per_page=1&sha={default}` — ostatni commit;
   - `GET /repos/{full}/branches?per_page=100` — liczba branchy i najstarszy
     z pierwszych trzech sprawdzanych;
   - `GET /repos/{full}/pages/builds/latest` i
     `GET /repos/{full}/deployments?environment=github-pages` — stan Pages.
3. Wynik jest zapisywany w `data.json`, a dzienny skrót w
   `data/repo_history.json` (jeden wpis na dzień, maks. **120 dni**).

Ograniczenia: API zwraca maks. pierwsze 100 repozytoriów; prywatne repo bez
uprawnień tokena pokazuje `brak dostępu` / `ci_available: false`, a nie
zmyślone dane.

### 5.4. Historia

`data/repo_history.json` przechowuje dzienne snapshoty: CI, mediana CI,
liczba PR-ów, issues, branchy i gwiazdek. Służą one do wykrywania spowolnienia
CI (porównanie z snapshotem sprzed tygodnia) bez dodatkowych wywołań API.
Ten sam dzień jest nadpisywany, nie duplikowany.

## 6. Jakie modele są używane

**Dashboard i alerty nie używają żadnego modelu.** Oba joby mają
`no_agent: true`; `build.py`, `render.py`, `alertpush.py` i `serve.py` to
czysty Python (standard library). Pole `model` w `jobs.json` nadal zawiera
domyślny model schedulera (`cline-pass/deepseek-v4.1-flash-1017`), ale przy
`no_agent: true` nie jest on wywoływany — nie powstaje sesja agenta ani
koszt tokenów.

Model pojawia się w dashboardzie tylko jako **temat pomiaru**: log API innych
jobów jest parsowany, a ich koszt szacowany. W snapshocie z 2026-11-05
wszystkie zarejestrowane wywołania miały model
`cline-pass/deepseek-v4.1-flash-1017`; to nie znaczy, że dashboard go używa.

Osobny projekt `models-monitoring` monitoruje **modele ClinePass** (catalog,
Artificial Analysis, stawki) i publikuje na GitHub Pages. To inny system —
nie jest częścią dashboardu „Joby i projekty”.

## 7. Alerty — reguły

Okno alertów: **30 dni**. Próg „stare repo”: **14 dni** bez pushu. Próg
„stary PR”: **7 dni**. PR bez review: **2 dni**. Stary branch: **30 dni**.
Spowolnienie CI: mediana co najmniej **1,5×** wyższa niż tydzień temu.
Pages bez przebudowy mimo pushy: **7 dni**.

| Alert | Warunek | Bazowy score |
|---|---|---:|
| `job-failed-*` | nieudany run w oknie | 2–9, zależnie od stanu joba |
| `job-streak-*` | seria porażek | 10 |
| `job-overdue-*` | `next_run_at` minął > 90 min | 8 |
| `job-delivery-*` | run OK, dostarczenie nieudane | 6 |
| `ci-*` | CI `failure`, `timed_out` lub `cancelled` | 8 |
| `ci-slowed-*` | CI zielone, mediana ≥ 1,5× tydzień temu | 4 |
| `pages-*` | Pages `errored` / `building` / inny zły stan | 5 |
| `pages-stale-*` | Pages nie przebudowane > 7 dni mimo pushy | 2 |
| `pr-stale-*` | PR otwarty > 7 dni | 3 |
| `pr-noreview-*` | PR bez review ≥ 2 dni | 4 |
| `branch-*` | najstarszy branch bez ruchu > 30 dni | 2 |
| `push-*` | brak pushu > 14 dni | 1 |

Po naliczeniu score alert dostaje flagę:

- **🔴 czerwony** — score ≥ 7 (poziom `err`);
- **🟡 żółty** — score 4–6 (poziom `warn`);
- **⚪ biały** — score 0–3 (poziom `info`).

Alerty są sortowane po score malejąco. `alertpush.py` wysyła **tylko nowe**
alerty i **tylko te, które ustały**. Pierwszy run po skasowaniu
`data/alert_state.json` tylko zapisuje stan (seed) i nic nie wysyła — dzięki
temu świeża instalacja nie zasypuje Telegrama starymi alertami.

## 8. Gdzie są publikowane wyniki

| Wynik | Miejsce | Przeznaczenie |
|---|---|---|
| Dashboard HTML | `/opt/data/monitoring/index.html` | samowystarczalna strona, zero CDN/JS |
| Dane maszynowe | `/opt/data/monitoring/data.json` | źródło dla alertów i dalszych integracji |
| Historia repo | `/opt/data/monitoring/data/repo_history.json` | trendy CI/PR/branchy, 120 dni |
| Stan alertów | `/opt/data/monitoring/data/alert_state.json` | otwarte alerty i znaczniki czasu |
| Log serwera | `/opt/data/monitoring/http.log` | start/restart serwera |
| Strona w sieci | `https://<tailnet-host>/monitor/` | tylko tailnet, bez publicznego dostępu |
| Alerty | Telegram — skonfigurowany czat źródłowy | krótkie powiadomienia o zmianach |

**Nie ma publikacji na GitHub Pages** dla tego dashboardu. `index.html` i
`data.json` zawierają metadane prywatnych repozytoriów, więc nie wolno ich
commitować do publicznego repo ani wystawiać portu 8765 poza Tailscale.

`serve.py` obsługuje zarówno `/`, jak i `/monitor/` — Tailscale montuje
backend pod prefiksem i strona działa niezależnie od tego, czy proxy obcina
prefiks.

## 9. Bezpieczeństwo i ograniczenia

- `GITHUB_TOKEN` jest czytany z env lub `/opt/data/.env`; **nie może** trafić
  do repo, `index.html` ani `data.json`.
- Dashboard pokazuje nazwy prywatnych repozytoriów i metadane PR/issues.
  Dostęp jest tylko przez Tailscale; `serve.py` nie ma własnej autoryzacji.
- API GitHub ma limity; dashboard odświeża się co 30 minut i nie paginuje
  ponad pierwsze 100 repozytoriów.
- Koszt modeli to szacunek według stawek referencyjnych, nie faktura.
- Brak danych jest pokazywany jako `-` / `brak dostępu`, nie jako zero.
- Historia repo zaczyna się od pierwszego uruchomienia `repo_history.json`;
  wcześniejsze trendy nie istnieją.
- Alert „brak pushu” jest informacyjny — nie oznacza, że repo jest zepsute.

## 10. Runbook — szybka diagnostyka

1. **Czy dane są świeże?**

   ```bash
   python3 -c 'import json; d=json.load(open("/opt/data/monitoring/data.json")); print(d["generated_at"], len(d["repos"]), len(d["alerts"]))'
   ```

2. **Czy strona odpowiada lokalnie?**

   ```bash
   curl -sf http://127.0.0.1:8765/index.html >/dev/null && echo OK
   ```

3. **Wymuś przebudowę:**

   ```bash
   /opt/data/scripts/dashboard-build.sh
   ```

4. **Sprawdź, czy alerty nie są zablokowane:** `data/alert_state.json`
   powinien istnieć i mieć sekcję `open`. Jeśli go usuniesz, następny run
   tylko zaseeduje stan — nie wyśle alertów.

5. **Sprawdź logi:** `/opt/data/monitoring/http.log` oraz wynik
   `dashboard-build.sh` (`jobs=... repos=... alerts=... api_calls=...`).

## 11. Pliki i odpowiedzialności

| Plik | Rola |
|---|---|
| `monitoring/sources.py` | pobieranie cron/DB/logów/GitHub API, historia repo |
| `monitoring/build.py` | orkiestracja, reguły alertów, scoring, zapis wyników |
| `monitoring/render.py` | render jednego statycznego HTML |
| `monitoring/alertpush.py` | różnice alertów i tekst na Telegram |
| `monitoring/serve.py` | serwer HTTP na 8765, obsługa `/monitor/` |
| `scripts/dashboard-build.sh` | job `407a626270f2`: build + health-check serwera |
| `scripts/alert-push.sh` | job `556c1b28e92e`: push alertów |
| `cron/jobs.json` | definicje jobów i harmonogramy |
| `cron/executions.db` | historia wykonań |
| `logs/agent.log` | wywołania API, modele, tokeny, latencja |
| `monitoring/rates.json` | referencyjne stawki do szacunku kosztów |

## 12. Weryfikacja działania

Po przebudowie `build.py` wypisuje:

```
jobs=<liczba> repos=<liczba> alerts=<liczba> api_calls=<liczba> koszt=$<kwota>
```

Poprawny stan z 2026-11-05 17:31 Europe/Warsaw:

- 10 jobów,
- 17 repozytoriów,
- 6 alertów,
- 505 wywołań API w oknie 30 dni,
- szacowany koszt $2.01.

Wartości zmieniają się przy każdym przebiegu; powyższe są punktem odniesienia,
nie oczekiwanym wynikiem testu.
