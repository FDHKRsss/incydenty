# Architecture — projekt „incydenty" (analiza `civil42pwa-public`)

To jest projekt **research/analiza**. „Architektura" opisuje tutaj decyzje dotyczące sposobu wykonania analizy i struktury deliverable'ów, a nie architekturę budowanego oprogramowania.

## Cel w jednym zdaniu

Dostarczyć samodzielny dokument Markdown, który na podstawie statycznej analizy kodu odpowiada: co robi repo, jak ma się do pomysłu z burzy mózgów, co jest zrobione oraz co brakuje do PoC / MVP / beta — **bez uruchamiania aplikacji i bez pushowania do repo docelowego**.

## Decyzje projektowe

1. **Tylko analiza statyczna.** Nie uruchamiamy `vite`, funkcji Firebase ani Snowflake. Wszystkie wnioski pochodzą z lektury plików; tam, gdzie wnioskujemy o zachowaniu runtime, jest to oznaczone jako obserwacja z kodu.
2. **Główny deliverable = `docs/ANALYSIS.md`.** Jeden, kompletny, samodzielny plik z sekcjami 1–9 (co robi repo → porównanie → co zrobione → PoC → MVP → beta → ryzyka → źródła → otwarte pytania). Plik jest pisany w całości od razu (crash-safe), a potem udoskonalany w miejscu.
3. **Brak dokumentu z burzy mózgów traktujemy jawnie.** Nie fabrykujemy treści pomysłu. Porównanie opiera się na oznaczonym modelu roboczym, a w sekcji 2.1/9 udokumentowano, że po dostarczeniu dokumentu należy zaktualizować porównanie. To decyzja o uczciwości badawczej, a nie przeoczenie.
4. **PoC/MVP/beta zdefiniowane jako pionowe plastry.** PoC = minimalna ścieżka „przechwycenie → wysyłka → zapis" dla jednego testera; MVP = użyteczne dla małej grupy (odczyt, auth, offline, RODO); beta = stabilna i skalowalna wersja produkcyjna (role, cykl życia, bezpieczeństwo, niezawodność). Wszystkie progi opisane w dokumencie analizy.
5. **Nie piszemy kodu.** Gapsy opisujemy prozą/punktami z odwołaniami do plików; nie generujemy patchy ani implementacji.
6. **Weryfikacja jest zautomatyzowana i groundingująca.** `tests/test_analysis.py` (uruchamiany przez `python -m unittest tests.test_analysis`) nie testuje działania aplikacji, lecz sprawdza, że każde istotne twierdzenie analizy o kodzie jest zgodne z faktyczną zawartością klonu (`civil42pwa-public/`): stan gita (commit `429f9bc`, czysty klon, brak README), potrójny bug `persist()`, zachowania endpointu `/report`, helpery, frontend i konfiguracja. 32 testy, wszystkie zielone. To „testy zielone" w rozumieniu tego projektu research/analiza.

## Dyspozycja uwag krytyka

1. **„Nie powstał żaden deliverable"** — sensowna i w pełni w zakresie celu; **przyjęto w całości** (utworzono `docs/ANALYSIS.md`, `docs/PLAN.md`, `docs/ARCHITECTURE.md`).
2. **„`ANALYSIS.md` niedoszacowuje błędu zapisu w `persist()`"** — sensowna i w zakresie celu (to poprawność analizy i poprawna lista prac do PoC). **Przyjęto w całości**: F2, §4.2, §1.3 i wiersz „Centralny rejestr" poprawione, by opisywały potrójny błąd (brak `geo_desc` w DDL + 5 placeholderów przy 4 bindach + nieużywany `desc`). **Nic nie odrzucono** — brak punktów poza zakresem.

## Granice zakresu (czego celowo NIE robimy)

- Nie uruchamiamy aplikacji ani nie instalujemy jej zależności (cel tego zabrania).
- Nie modyfikujemy kodu w `civil42pwa-public/` (analiza, nie rozwój) i **nie pushujemy** do `origin` tego repo.
- Nie piszemy README (własność celu i nadzorcy).
- Nie rozszerzamy analizy o implementację — jedynie o plany prac do PoC/MVP/beta.

## Struktura plików

- `docs/ANALYSIS.md` — główny deliverable (wyniki analizy).
- `docs/PLAN.md` — cel, milestones (stub/real), adnotacje o uwagach krytyka.
- `docs/ARCHITECTURE.md` — ten plik (decyzje i dyspozycje).
- `docs/CONTEXT.md` — trwałe, nieprzekraczalne dyrektywy (esencja, bez powtórzenia całego celu).
- `docs/lessons/known-issues.md` — wnioski z pułapek (m.in. pełna ścieżka `INSERT`: placeholder vs bindy vs użyte pola).
- `tests/test_analysis.py` — zautomatyzowany test groundingujący (32 testy).
- `civil42pwa-public/` — klon analizowanego repo (tylko do odczytu).
