# Decyzje właściciela — odpowiedzi na kluczowe pytania

> **Jak używać:** wpisz odpowiedź pod `**Odpowiedź:**` w każdej sekcji i zmień `Status` na `ZAMKNIĘTE`.
> Po zapisaniu poproś Cline: „przenies decyzje do planu i commitnij".
> Kontekst decyzji: werdykt **PIVOT** z debaty rady — [concept-boardroom.md](concept-boardroom.md).

| # | Decyzja | Status | Blokuje |
|---|---|---|---|
| D1 | Próg porażki projektu | ZAMKNIĘTE | kryterium zamknięcia F1 |
| D2 | Portfel i budżet (dane + LLM) | ZAMKNIĘTE | gate G3 (ekonomika) |
| D3 | Obszar dyskrecjonalny | ZAMKNIĘTE | projekt modułu M2 |
| D4 | Źródło danych rynkowych | ZAMKNIĘTE | implementację M1 (F0) |

## D1. Próg porażki projektu

**Pytanie:** jaka metryka / benchmark / okres kończy pracę nad projektem?

**Dlaczego:** debata wskazała ryzyko „projektu bez końca" — bez kryterium zamknięcia
system może trwać w nieskończoność (ryzyko nr 6 w planie).

**Wpływa na:** kryterium zamknięcia fazy F1, ocenę sensu dalszych inwestycji w projekt.

**Status:** ZAMKNIĘTE

**Odpowiedź:**
Zakładam 100% inwestycje w akcje i aktywa ryzykowne (krypto), zatem punktem odniesienia
powinien być szeroki indeks płynnego rynku, np. S&P 500. Jeśli po 12 mies. paper tradingu
Sharpe projektu < Sharpe S&P 500 — projekt zamykam.

## D2. Wielkość portfela i budżet na dane + LLM

**Pytanie:** jaka jest wartość portfela i ile rocznie możesz wydawać na dane i LLM?

**Dlaczego:** gate G3 wymaga rachunku: koszty roczne < 0,3–0,5% wartości portfela
(szacunek rady: dane+LLM 1,5–15 tys. USD/rok — może nie przejść przy mniejszym portfelu).

**Pomocniczo:** zapisz trzy liczby — wartość portfela [PLN/USD], koszt danych rocznie,
koszt LLM rocznie. Próg sensu = 0,3–0,5% wartości portfela (np. portfel 100 tys. PLN
→ budżet ok. 300–500 PLN/rok).

**Status:** ZAMKNIĘTE

**Odpowiedź:**
Portfel: 1 000 000; budżet: dane 1 000/rok, LLM 1 000/rok (łącznie 2 000/rok).

**Wynik gate'a G3:** 2 000 / 1 000 000 = 0,2% < 0,3–0,5% → **PRZEJŚCIE**
(założenie: wszystkie trzy liczby w tej samej walucie). 

## D3. Obszar dyskrecjonalny

**Pytanie:** czy dopuszczasz wyjątki od twardych reguł rebalancingu? Jeśli tak — jak wąsko je definiujesz (kto, kiedy, jaka granica odchylenia)?

**Dlaczego:** rada ostrzegła, że furtki typu „chyba że przekroczone progi ryzyka"
unieważniają rygor systemu (ryzyko nr 3 w planie).

**Wpływa na:** projekt modułu M2 (silnik rebalancingu) — im węższa definicja, tym prostsza logika.

**Status:** ZAMKNIĘTE

**Odpowiedź:**
NIE — system zawsze wykonuje regułę; wyjątek tylko ręcznie, z wpisem w logu.

## D4. Źródło danych rynkowych

**Pytanie:** skąd brać wyceny portfela i kursy benchmarku?

**Opcje:** Stooq (darmowe, dobre dla PL) / yfinance (darmowe, Yahoo Finance) /
własne pliki CSV/Excel / inne (wpisz).

**Wpływa na:** implementację M1 (pierwsza rzecz budowana w F0).

**Status:** ZAMKNIĘTE

**Odpowiedź:**
Benchmarki i dane ze źródeł publicznych (np. Stooq, Yahoo i inne) lub API brokera, np. XTB.