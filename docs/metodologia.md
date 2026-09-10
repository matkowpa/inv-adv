# Metodologia inv-adv — logika systemu krok po kroku

> Dokument syntezuje metodologię projektu (stan: 2026-09-10, po D5 i kalibracji G1).
> Szczegóły operacyjne: [plan-inv-adv.md](plan-inv-adv.md), decyzje: [decyzje.md](decyzje.md).

## 0. Problem, który rozwiązujemy

Portfel ~1,4 mln PLN złożony z płynnych aktywów (ETF-y akcyjne, krypto, pojedyncza akcja).
Trudności, które mają wszyscy inwestorzy indywidualni:

- **dyscyplina** — emocje (FOMO, panika) prowadzą do kupowania wysoko i sprzedawania nisko;
- **brak audytowalności** — decyzje „z głowy" nie mają uzasadnienia, którego można się
  potem przyjrzeć;
- **brak kryterium sukcesu/porażki** — projekt inwestycyjny może trwać w nieskończoność,
  nie odpowiadając na pytanie „czy to w ogóle działa?".

Metoda wybrana w pierwszej debacie (Boardroom, werdykt **PIVOT**,
[concept-boardroom.md](concept-boardroom.md)): **nie budować „AI komitetu" od razu —
najpierw nudny, deterministyczny rdzeń reguł, a warstwa LLM jako eksperyment, który musi
przejść testy falsyfikacyjne, żeby w ogóle powstał.** Fundamentalna zasada systemu:
*nic nie wchodzi do portfela bez dowodu wartości*.

## 1. Cel główny

**Pomnażanie kapitału przy ograniczonym ryzyku — mierzalne i falsyfikowalne.**

Nie „pobijemy rynek zawsze", tylko: portfel w 12 miesiącach paper-tradingu musi mieć
**Sharpe ≥ Sharpe S&P 500** (decyzja D1). Jeśli nie — projekt zamykamy. To najważniejsza
decyzja metodyczna: definiuje kryterium końca i chroni przed „projektem bez końca".

## 2. Architektura: dwie warstwy rozdzielone gate'ami

```
[ Dane: IBKR (pozycje) + Yahoo (ceny/FX) ]
        ↓
[ RDZEŃ — twardy, deterministyczny, bez LLM ]
        ↓
[ GATE'E G1–G4 — testy falsyfikacyjne ]
        ↓
[ WARSTWA LLM — tylko jeśli gate przejścia ]
```

Kluczowa idea: **rdzeń działa w 100% niezależnie od AI**. AI jest opcjonalnym dodatkiem,
nie fundamentem — to odróżnia system od „robo-advisorów z LLM", gdzie model jest czarną
skrzynką, na której wszystko wisi.

## 3. Rdzeń: trzy moduły i cykl (F0 — zbudowany)

### M1 — Przegląd portfela („gdzie jestem?")

- Import pozycji z IBKR (xlsx → CSV), mapowanie tickerów na klasy aktywów
  (`data/ibkr_mapping.yaml`).
- Wycena w PLN: cena (Yahoo) × ilość × kurs FX.
- **Alokacja** = suma wartości w klasie ÷ wartość portfela (np. `equity_us 57,2%`).
- **Dryf** = (alokacja − target) × 100, w p.p. (np. krypto: (4,7% − 10%) = −5,3 p.p.).

### M2 — Silnik rebalancingu („co robić?") — tu jest cała „inteligencja"

Dwie reguły, zero dyskrecji (decyzja D3: system ZAWSZE wykonuje regułę; wyjątek tylko
ręcznie, z wpisem w logu):

- **R1 (dryf):** jeśli |dryf klasy| > **5 p.p.** → transakcja przywracająca klasę
  **dokładnie do targetu**; kwota dzielona proporcjonalnie między tickery klasy.
  Nie ma „sprzedaj trochę", nie ma „wydaje mi się" — jest tylko progi i wzór.
- **R2 (limit obrotu):** jeśli suma transakcji > **20%** wartości portfela → proporcjonalne
  przeskalowanie do 20%. Chroni przed jednym ogromnym rebalancingiem.

**Dlaczego to działa:** próg 5 p.p. daje ostrzeżenie i czas zanim klasa spadnie z 10% do
~5% alokacji (realne ryzyko). Po przekroczeniu progu odmowa działania też jest decyzją —
ale świadomą, zapisaną. Rebalancing jest **kontrariański w skutkach**: system automatycznie
sprzedaje to, co urosło, i kupuje to, co staniało — to zarządzanie ryzykiem, nie spekulacja.

**Czego NIE robi:** nie „optymalizuje" niczego, nie przewiduje cen, nie kupuje „bo rośnie".
Kupuje wyłącznie dlatego, że klasa jest za lekko ważona względem obiecanej struktury.

### M3 — Protokół i historia („dlaczego to zrobiłem?")

Każdy cykl generuje protokół markdown z pełnym łańcuchem: dane wejściowe → ceny → pozycje
→ dryf → reguła z ID → kwoty → wyjątki. Do tego punkt historii (`reports/history.csv`)
z wyceną i alokacją. Eliminuje to samoodwoływanie się do „tamtego dnia to wyglądało
inaczej": zawsze jest dokładne dane i dokładna reguła, którą wykonano — lub świadomie
nie wykonano (wyjątek ręczny D3, z wpisem).

## 4. Metryki (F1) — jak oceniamy, czy to działa

Z historii punktów, zawsze **portfel vs benchmark**:

| Miara | Co mierzy | Rola |
|---|---|---|
| wynik okresu | total return od pierwszego do ostatniego punktu | surowy wynik |
| zmienność roczna | odchylenie std. stóp zwrotu × √(365/dni) | „nerwowość" portfela |
| **Sharpe** | (roczna stopa zwrotu − stopa wolna) / zmienność | **jedyna miara łącząca wynik i ryzyko; kryterium D1** |
| max drawdown | największe obsunięcie od szczytu | ból: ile stracisz w najgorszym momencie |

Sharpe jest kluczowe, bo „zarobiłem 20% przy 80% zmienności" jest **gorsze** niż „15%
przy 10% zmienności". Benchmarki: S&P 500 (główny, D1), Nasdaq-100, WIG20, mWIG40TR
(proxy ETF) — porównawcze. Metryki z historii biegów (od 3 punktów) oraz rekonstrukcji
historycznej przy statycznym składzie (`history_rebuild`).

**Zastrzeżenie:** przy małym n (dni/tygodnie) metryki są ozdobne — znaczenie mają
po miesiącach. Protokół oznacza to „dane orientacyjne".

## 5. Decyzja D5 (krypto = aktualna alokacja) — jak działa i dlaczego

**Kontekst:** target krypto był 10%; właściciel zlikwidował ETH ręcznie, zostało 4,7%
w BITC. R1 zobaczył dryf −5,3 p.p. i zgodnie ze swoimi regułami co tydzień proponował
kupno ~75 tys. PLN BITC — **reguła działała poprawnie, ale target był wyznaczony przez
portfel sprzed likwidacji ETH, nie przez świadomą decyzję**. To pułapka: system słucha
twardej reguły, a „miękkie" założenie w configu jest nieaktualne.

**Krok po kroku:**
1. Co się stanie przy każdym wariancie (W0–W3) — policzone silnikiem M2 offline PRZED
   zmianą cokolwiek (`scripts/whatif_targets.py`, [what-if-targets.md](what-if-targets.md)).
2. Właściciel zdecydował: krypto = poziom obecny (4,7%) — świadome zredukowanie celu (D5).
3. Target krypto = alokacja → **dryf krypto = 0** → R1 milknie. Suma targetów musi
   wynosić 1.0, więc 5,3 p.p. nadwyżki przypisano do `equity_us` → 60,3%.
4. Zmiana **deklaratywna** (config), nie kodowa — silnik nie zna nowej „inteligencji",
   tylko nowe liczby. Zmiana strategii = zmiana danych, nie programu.

**Efekt:** protokoły pokazują „0 transakcji" — system pilnuje, zamiast wywoływać
wrażenie ciągłego kupowania. Uwaga operacyjna: `equity_us` ma teraz dryf −3,1 p.p.,
1,9 p.p. od progu R1 — kolejny słabszy miesiąc US odpali automatyczne dokupienie do 60,3%
(odsysanie nadwyżki z krypto, zgodnie z D5).

## 6. Warstwa LLM (M4) — dlaczego zawieszona i jak wygląda re-test

Pomysł: CIO + szef ryzyka + analityk (agenci LLM) debatują w rundach i rekomendują
alokację. **Gate G1** (falsyfikacyjny): jeśli agenci różnią się rekomendacjami ≥30 p.p.
na tych samych danych, komitet wnosi wartość; jeśli zgodność ~100% — to tylko „teatr"
(wysoka korelacja błędów: modele trenowane na tych samych tekstach).

**Wynik G1: FAIL** — 0/3 agentów podało liczby; agenci debatowali metodologię testu
zamiast rekomendować alokację. Przy okazji sfalsyfikowano sam próg 30 p.p. (Goodhart):
dwa rozsądne portfele różnią się typowo ~46 p.p., więc niski próg nagradzał teatralne,
skrajne wektory.

**Decyzja D6(b): kalibracja przed re-testem** ([g1-retest.md](g1-retest.md)):
1. Symulacja 20 par (seed=42, offline): sens-sens 25–82 p.p. vs sens-teatr 174–198 p.p.
   → przedziały nie przecinają się → **skalibrowany próg 128 p.p.**
   (`scripts/g1_calibration.py`).
2. Prompt v2: bez tabeli Sharpe (ciągnęła agentów do pościgu za wynikiem) — tylko profil
   inwestora + horyzont.
3. Odpowiedź re-testu liczbowa: L1 między wektorami agentów musi przewyższać szum
   wewnątrz samego modelu (baseline niedeterminizmu — krok do wykonania przed re-testem).
4. Jeśli re-test padnie: M4 zamykany **na zawsze**, bez dalszych debat.

**Metodologiczne sedno:** naprawiamy pomiar, nie wynik. Nie obniżamy progu, żeby komitet
„przeszedł" — kalibrujemy go na materiale (baseline + symulacja), żeby test mówił coś
realnego.

## 7. Plan działania — jedna pętla

1. **Twardy rdzeń działa** — rebalancing wg reguł, zero dyskrecji, pełny audyt (F0).
2. **Cotygodniowy automat** (`inv-adv-weekly`, sob. 10:00) zbiera punkty historii bez
   ingerencji (F1).
3. **G4: 6–12 mies. paper tradingu** — system proponuje, właściciel ręcznie egzekwuje
   (lub świadomie nie — z wpisem w logu); zbiera się seria metryk.
4. **D1: po 12 miesiącach** — Sharpe portfela vs Sharpe S&P 500. Wyżej → kontynuacja
   (potem ew. automatyzacja egzekucji). Niżej → **projekt zamykany** — co jest sukcesem
   metodycznym (uniknięta dalsza strata czasu/kapitału).
5. **G2 (sentyment) i re-test G1** — warunkowe; wchodzą tylko, jeśli dowiodą wartości
   liczbowo.
6. **Skalowanie (B2C/white-label)** — zamrożone do analizy regulacyjnej (KNF/MiFID).

## 8. Sedno metodologii — trzy zasady

1. **Determinizm ponad dyskrecję** — ta sama reguła na tych samych danych zawsze daje
   tę samą odpowiedź (`run.py --offline` = reprodukowalność).
2. **Falsyfikowalność ponad wizję** — każdy element (komitet, sentyment, cały projekt)
   ma z góry zapisany test, który może go zabić, i zapisany próg porażki.
3. **Człowiek składa zlecenia, system je proponuje** — nigdy automatycznej egzekucji,
   dopóki 6–12 miesięcy historii nie pokaże, że system nie robi błędów.

**W skrócie:** nie budujemy „AI, które inwestuje". Budujemy **regulowany, audytowalny
proces inwestycyjny**, w którym AI — jeśli w ogóle — może wejść tylko jako element
zmieniający tempo/tilt, i tylko po udowodnieniu, że wnosi coś ponad losowe szumienie.

