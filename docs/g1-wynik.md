# G1 — wynik testu komitetu agentów (2026-09-04)

> Test wykonany zgodnie z pomiarem predefiniowanym w [g1-komitet-input.md](g1-komitet-input.md)
> (zdefiniowanym PRZED debatą). Pełne artefakty: `idea-orch\sessions\g1-komitet\`
> (agenda, opinie per agent per runda, syntezy, concept.md, cost_report.md). Koszt sesji: **$0.2107**.

## Wynik formalny: G1 — PORAŻKA

| Kryterium (predefiniowane) | Wymóg | Wynik | Werdykt |
|---|---|---|---|
| Liczbowe rekomendacje targetów | ≥ 2/3 agentów | **0/3** — żaden agent (GLM-5.3, GPT-5.1, GPT-5-mini) nie podał wektora 6 klas | ❌ |
| Rozbieżność parowa L1 wektorów | ≥ 30 p.p. | **n/d** — brak wektorów do porównania | ❌ |

Trzech agentów przez dwie pełne rundy **debátowało metodykę samego gate'a zamiast
rekomendować alokację** — mimo że wejście wprost wymagało „liczb obowiązkowych".
Ryzyko „teatru multi-agentowego", które G1 miał wykryć, materializuje się nawet
głębiej: nie tyle zgodne rekomendacje, co **dyskusja o pomiarze zamiast pomiaru**.

## Co debata jednak ustaliła (wartościowe ustalenia)

1. **Próg 30 p.p. został sfalsyfikowany na materiale samej rady** (visionary podał
   przykładowe pary wektorów do symulacji; sceptic przeliczył):
   - dwa merytorycznie sensowne portfele: `[60,10,10,8,2,10]` vs `[50,15,8,10,2,15]` → **L1 = 24 p.p.** — poniżej progu,
   - para „sensowny + teatralny": `[55,15,10,8,2,10]` vs `[90,0,0,0,0,10]` → **L1 = 70 p.p.**.
   Wniosek: gate w tej formie **nagradza teatralność, a odrzuca zgodność merytoryczną** (Goodhart).
2. **Brak baseline'u niedeterminizmu** — bez zmierzenia, ile L1 generuje sam niedeterminizm
   modelu (kilka uruchomień jednego agenta bez person), każdy próg rozbieżności jest niekalibrowany.
3. **Kontekst wejścia biasuje agentów** — tabela Sharpe z 8-miesięcznego okna w prompcie
   ciągnie rekomendacje w stronę „pościgu za indeksem"; w re-teście zastąpić profilem i horyzontem.
4. **D1 (kryterium właściciela) i G1 (ocena komitetu) to dwa różne pytania** — portfel
   100% aktywów ryzykownych bez obligacji strukturalnie trudno bije Sharpe S&P 500
   w trendującym rynku; wyniku D1 nie wolno odczytywać jako oceny warstwy LLM.

## Werdykt sędziego (concept.md)

**NO-GO dla M4 w obecnej formie** + warunkowy PIVOT — przed ewentualnym re-testem G1
trzeba *wykonać* (nie: zaplanować) 5 kroków zerokosztowych:

1. baseline niedeterminizmu (5–10 uruchomień jednego agenta bez person),
2. symulacja 20 par „sensowne/teatralne" wektory → kalibracja progu,
3. prompty bez tabeli Sharpe (profil/horyzont zamiast wyników okresu),
4. rozdzielenie oceny D1 od oceny komitetu,
5. liczbowy protokół furtki (np. max 1 tilt/kwartał, max 5 p.p. odchylenia).

Jeśli po kalibracji rozbieżność między agentami nadal nie przewyższa szumu
wewnątrz-agenta — M4 zamykamy jako „teatr multi-agentowy", bez dalszych debat.

## Konsekwencja dla planu

- **M4 (komitet agentów) pozostaje zawieszony** — G1 nieprzejściowy w obu wariantach
  (formalny FAIL + sfalsyfikowany próg).
- **Decyzja właściciela D6** ([decyzje.md](decyzje.md)): (a) trwałe zamknięcie M4, czy
  (b) jednorazowa kalibracja zerokosztowa (godziny pracy, ~$0.05) i skalibrowany re-test G1.
- Zastrzeżenie metodologiczne: to pojedyncza sesja i jeden projekt wejścia — kalibracja
  z pkt 1–2 rozstrzygnie, czy wynik jest cechą komitetu, czy artefaktem setupu.
- G2 (sentyment) bez zmian — niewykonane, blokada niezależna od G1. Rdzeń F0/F1 działa.