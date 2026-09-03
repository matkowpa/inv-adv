# Koncepcja biznesowa: Osobisty Komitet Inwestycyjny (AI Portfolio Committee)

## 1. Koncepcja
System wspierania decyzji inwestycyjnych dla własnego portfela płynnych aktywów (akcje, obligacje, ETF-y), oparty na twardych regułach rebalancingu i limitach ryzyka, uzupełniony o symulowany multi-agentowy "komitet inwestycyjny" (CIO, Risk Officer, analitycy) generujący uzasadnienia i rekomendacje. Sentyment rynkowy służy wyłącznie jako filtr modyfikujący tempo działań, nie jako sygnał decyzyjny.

## 2. Problem i grupa docelowa
- **Problem**: brak dyscypliny i systematyczności w rebalancingu prywatnego portfela, decyzje emocjonalne, brak audytowalnej dokumentacji procesu.
- **Grupa docelowa**: w fazie 1 — właściciel projektu (self-use). W ewentualnej fazie 2 — zaawansowani inwestorzy indywidualni/HNWI, docelowo family office (niszowy rynek, rząd dziesiątek-setek tysięcy osób w regionie EU/PL — bez zweryfikowanego rozmiaru).

## 3. Model monetyzacji
- Faza 1: brak monetyzacji — wartość = efektywność kapitału własnego (Sharpe, drawdown vs benchmark).
- Faza 2+ (warunkowa): SaaS/subskrypcja dla advanced retail lub white-label dla small family office. **Nierozstrzygnięte i blokujące**: brak analizy regulacyjnej (KNF/MiFID) — rekomendacje inwestycyjne dla osób trzecich mogą wymagać licencji.

## 4. Konkurencja i przewaga
- **Konkurenci**: arkusze/Python (Zipline, QuantRocket), robo-advisors (Wealthfront, Betterment), narzędzia portfolio-tracking (Portfolio Performance, Sharesight, Addepar).
- **Przewaga deklarowana**: audytowalny "protokół komitetu" z uzasadnieniami decyzji, transparentność vs "czarna skrzynka" robo-advisorów.
- **Zastrzeżenie sędziego**: przewaga ta jest niepotwierdzona — jeśli test rozbieżności agentów wykaże >80-90% zgodności rekomendacji, USP redukuje się do ozdobnej narracji nad zwykłym silnikiem reguł, który konkurenci już mają.

## 5. Główne ryzyka (z atrybucją)
1. **"Teatr multi-agentowy"** — agenci LLM tej samej rodziny mogą dawać iluzję deliberacji przy wysokiej korelacji błędów (sceptic). Niezweryfikowane w żadnej z dwóch rund.
2. **Brak dowodu mocy predykcyjnej sentymentu** — ryzyko wzmacniania szumu rynkowego (sceptic, potwierdzone częściowo przez analyst i visionary jako wymóg backtestu przed wdrożeniem).
3. **Sprzeczność reguł twardych vs dyskrecji agentów** — furtki typu "chyba że przekroczone progi ryzyka" unieważniają rygor systemu (sceptic); visionary próbował rozwiązać dwuwarstwowym modelem (reguły twarde/obszar dyskrecjonalny), ale operacyjny podział pozostaje niedopracowany.
4. **Nieudowodniona ekonomika projektu** — koszty danych/LLM (szacunek analyst: 1,500–15,000 USD/rok) mogą przewyższać próg 0,3–0,5% wartości portfela rocznie, poniżej którego projekt self-use nie ma sensu (sceptic, analyst).
5. **Ryzyko regulacyjne skalowania** — plany B2C/white-label bez analizy prawnej (MiFID/KNF) mogą być nierealizowalne (sceptic).
6. **Ryzyko automatyzacji egzekucji** — jednogłośnie odrzucone na starcie przez wszystkich agentów; halucynacja LLM przy auto-tradingu = ryzyko katastroficzne.
7. **Brak zdefiniowanego progu porażki** — projekt może trwać bez końca bez jasnego kryterium zamknięcia (sceptic).

## 6. Nierozstrzygnięte kwestie
- Wynik testu rozbieżności rekomendacji agentów (niewykonany w żadnej rundzie — kluczowy test falsyfikujący całe USP).
- Backtest sygnału sentymentowego (niewykonany).
- Rzeczywisty koszt danych/LLM vs deklarowana wielkość portfela (brak liczb wejściowych od właściciela projektu).
- Status regulacyjny dla fazy skalowania.
- Konkretny próg porażki (metryka/benchmark/okres).
- Precyzyjny podział "progi twarde" vs "obszar dyskrecjonalny" — brak operacyjnej specyfikacji.

## 7. Werdykt: **PIVOT**

**Uzasadnienie:**
Pomysł ma solidny rdzeń biznesowy (rules-based rebalancing + backtesty + benchmark), ale warstwa "multi-agentowego komitetu LLM" i "sentymentu rynkowego" nie ma w tej chwili żadnego dowodu wartości — obie kwestie zostały podniesione w rundzie 1 i powtórzone nierozwiązane w rundzie 2. Rada nie osiągnęła konsensusu w kluczowych sporach po dwóch rundach, co samo jest sygnałem, że projekt w obecnej, "pełnej" formie (komitet + sentyment + wizja skalowania) jest przedwczesny.

Rekomendowany pivot: **zredukować projekt do wersji minimalnej — rules-based portfolio manager z prostym logowaniem decyzji i benchmarkiem 60/40**, odsuwając multi-agentowy komitet LLM i sentyment do statusu "eksperyment do walidacji", a nie "rdzeń MVP". Warunki wejścia komponentów LLM:
- test rozbieżności rekomendacji agentów (≥30% różnicy rekomendacji na identycznych danych) — jeśli nieudany, komitet zostaje skasowany na zawsze;
- backtest sentymentu z wykazaną mocą predykcyjną — bez tego zero linii kodu do tego modułu;
- pisemny rachunek kosztów vs wielkość portfela, wykonany PRZED jakimkolwiek dalszym developmentem.

Automatyzacja egzekucji: wykluczona do potwierdzenia wyników w 6-12-miesięcznym paper-tradingu — to jedyny punkt w pełnym konsensusie wszystkich trzech agentów w obu rundach.

Skalowanie do B2C/white-label: zamrożone do wyjaśnienia statusu regulacyjnego — nie inwestować w "modułowość pod skalę" przed tą analizą.

To nie jest NO-GO, bo jądro koncepcji (dyscyplina rebalancingu + audytowalność) ma realną wartość nawet bez AI. Nie jest to też czyste GO, bo flagowa innowacja projektu (komitet AI) jest niezweryfikowanym założeniem, które może się okazać kosztowną fasadą.

---

# Raport kosztów sesji

_2026-09-03 21:26 UTC_

| Model | Wywołania | Tokeny in | Tokeny out | Koszt (USD) |
|---|---|---|---|---|
| `openrouter/anthropic/claude-sonnet-5` | 4 | 33,044 | 7,034 | $0.1364 |
| `openrouter/openai/gpt-5-mini` | 2 | 6,276 | 3,009 | $0.0076 |
| `openrouter/openai/gpt-5.1` | 2 | 6,238 | 3,873 | $0.0465 |
| `openrouter/z-ai/glm-5.3` | 2 | 6,390 | 2,460 | $0.0175 |

**RAZEM: $0.2081**
