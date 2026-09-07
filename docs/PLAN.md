# Plan

## Goal(s)

1. Pobrać repozytorium https://github.com/rzymek/civil42pwa-public.git, ale **nie pushować** do niego — pracować lokalnie na klonie.
2. Sprawdzić, co to repozytorium robi, **analizując wyłącznie kod** (nie uruchamiać aplikacji).
3. Porównać z pomysłem z burzy mózgów.
4. Podsumować:
   - co jest już zrobione w obecnym kodzie,
   - co trzeba jeszcze zrobić do **PoC**,
   - co trzeba jeszcze zrobić do **MVP**,
   - co trzeba jeszcze zrobić do gotowego produktu w wersji **beta**.

**Natura projektu:** research/analiza. „Implementacja" = dokument Markdown; nie powstaje żaden kod, nie uruchamiamy aplikacji.

## Krytyczne ustalenie wejściowe

Dokument z burzy mózgów **nie jest obecny** w repozytorium roboczym (README to tylko cel; `docs/*` to szablony; docelowe repo nie ma README). Porównanie wykonano z **jawnie oznaczonym modelem roboczym** (sekcja 2 `docs/ANALYSIS.md`). Po dostarczeniu dokumentu z pomysłem należy zaktualizować tabelę porównawczą — to planowana zmiana, nie blokada.

## Deliverable

Główny, samodzielny dokument: **`docs/ANALYSIS.md`** (kompletna analiza). Pliki pomocnicze: `docs/PLAN.md` (ten plik), `docs/ARCHITECTURE.md` (decyzje projektowe).

## Milestones

- [x] M1 — stub: utworzyć `docs/ANALYSIS.md` z kompletną pierwszą wersją (sekcje 1–6: co robi repo, porównanie, co zrobione, PoC/MVP/beta).
- [x] M1 — real: zweryfikować sekcje 1–6 względem plików kodu (commit `429f9bc`) i strony GitHub; doprecyzować w miejscu.
- [x] M2 — stub: dodać sekcje ryzyk technicznych (7) oraz źródeł i otwartych pytań (8–9).
- [x] M2 — real: sprawdzić, że każde ryzyko ma odwołanie do pliku, a źródła są faktycznie użyte.
- [x] M3 — stub: napisać `docs/PLAN.md` i `docs/ARCHITECTURE.md` spójne z celem.
- [x] M3 — real: uzgodnić dokumenty z finalnym `ANALYSIS.md` (brak dryfu).

## Jak zaadresowano uwagi krytyka (blokada)

1. Krytyk słusznie wskazał, że nie powstał żaden deliverable. Naprawiono przez utworzenie `docs/ANALYSIS.md` (kompletny, samodzielny dokument z realną treścią, nie placeholder) oraz `docs/PLAN.md` i `docs/ARCHITECTURE.md`.
2. Krytyk słusznie wskazał, że `ANALYSIS.md` niedoszacowuje błędu zapisu w `persist()`: to nie tylko brak `geo_desc` w DDL, lecz potrójny błąd (5 placeholderów przy 4 bindach + nieużywany `desc`). Naprawiono F2, §4.2, §1.3 i wiersz „Centralny rejestr", tak by opisywały pełny błąd i poprawną minimalną poprawkę do PoC.

Oba punkty są w zakresie celu — przyjęte w całości, nic nie odrzucono (szczegóły w `docs/ARCHITECTURE.md`).

## Zakaz pushowania do repo docelowego

Klon docelowy znajduje się w `civil42pwa-public/`; jego `origin` to https://github.com/rzymek/civil42pwa-public.git. **Nie wykonujemy `git push` w tym katalogu.** Commity wykonujemy wyłącznie w repozytorium roboczym (zewnętrznym), do którego należą pliki `docs/*`.
