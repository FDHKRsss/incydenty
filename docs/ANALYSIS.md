# Analiza repozytorium `civil42pwa-public` (projekt „incydenty")

**Data analizy:** 2026-09-07
**Źródło:** https://github.com/rzymek/civil42pwa-public.git — klon lokalny w katalogu `civil42pwa-public/`, commit `429f9bc` („initial commit")
**Metoda:** analiza statyczna kodu — przeczytano wszystkie pliki źródłowe i konfiguracyjne repozytorium; aplikacji **nie uruchamiano** (zgodnie z poleceniem).
**Status:** wersja kompletna (draft + weryfikacja względem źródeł zakończona).

---

## TL;DR

`civil42pwa-public` to wczesna, instalowalna aplikacja PWA (React + Vite + TypeScript) służąca do **zgłaszania zdarzeń/incydentów w terenie**. Urządzenie nagrywa dźwięk, użytkownik dotknięciem ekranu robi zdjęcie, a aplikacja wysyła do backendu **zdjęcie + klip audio + współrzędne GPS**. Backend (Firebase Cloud Functions) parsuje żądanie, dopisuje adres przez reverse geocoding (Nominatim/OpenStreetMap) i zapisuje dane do **Snowflake**.

Stan jest bardzo wczesny: frontend realizuje „szkielet" ścieżki przechwycenia i wysyłki, a backend ma krytyczne braki produkcyjne (twardo zakodowane poświadczenia Snowflake, brak walidacji wejścia, niespójny schemat bazy, niejednoznaczna ścieżka wdrożenia). Porównanie z pomysłem z burzy mózgów jest **ograniczone brakiem dokumentu z pomysłem** — poniżej przyjęto jawnie oznaczony model roboczy.

---

## 1. Co robi repozytorium (analiza kodu)

### 1.1. Frontend — aplikacja PWA

Technologia: **React 18 + TypeScript + Vite**, PWA przez `vite-plugin-pwa` (manifest, automatyczna aktualizacja service workera), testy przez Vitest.

- `index.html` — tytuł aplikacji: **Civil42**; ładuje `src/main.tsx`.
- `vite.config.ts` — konfiguracja PWA: nazwa/skrót „Civil42", kolor motywu `#FFFFE0`, ikony generowane z `public/icon.png` (krok `build:icons` z `pwa-assets-generator`). Manifest deklaruje ikony `pwa-64x64.png`, `pwa-192x192.png`, `pwa-512x512.png`, `maskable-icon-512x512.png`.
- `src/main.tsx` — start aplikacji z `ErrorBoundary` (łapanie błędów renderowania + przycisk „Reload"); rejestruje przerysowanie w globalnym `update`.
- `src/app.tsx` — główna orkiestracja:
  - przy starcie (`useEffect`) uruchamia nagrywanie audio (`audio.start()`);
  - pobiera geolokalizację przez `use-geo-location` i wyświetla status w nakładce tekstowej (np. `[Nagrywam] Nacinij, aby wysłać zdjęcie z audio i pozycją [<wersja>]`);
  - funkcja `submit(photo, voice)` konwertuje zdjęcie (`HTMLCanvasElement`) na PNG (`Blob`) i wysyła wraz z dźwiękiem oraz `gps.latitude`/`gps.longitude` do `/report`.
- `src/Camera.tsx` — podgląd z tylnej kamery (`facingMode: "environment"`), rysowanie klatki na `<canvas>`; kliknięcie w obraz zatrzymuje kamerę, zapisuje klatkę i po 1 s wznawia podgląd.
- `src/useRecordAudio.tsx` — nagrywanie mikrofonu przez `MediaRecorder`, wynik jako `audio/webm` (`Blob`).
- `src/send.tsx` — `POST` multipart/form-data na względny adres `/report` z polami `voice` (plik `voice.webm`), `image` (plik `image.png`), `lat`, `lon`.
- `src/state/state.tsx` + `src/state/update.ts` — szkielet stanu globalnego z zapisem do `localStorage`; w praktyce `state` jest **pusty** (`initialState = {}`) i nieużywany przez `App`.
- `src/app.spec.tsx` — test jednostkowy, który w rzeczywistości nic nie testuje: `expect(true).toBe(true)`.

**Obserwacja:** aplikacja jest interfejsem „złap i wyślij": nagrywanie audio działa w tle, a jedno dotknięcie ekranu robi zdjęcie i wysyła kompletny raport. Nie ma ekranu podglądu/potwierdzenia zdjęcia ani listy zgłoszeń.

### 1.2. Backend — Firebase Cloud Functions

Technologia: **Firebase Cloud Functions v2** (`firebase-functions`), Node.js 22, TypeScript, ESM.

- `functions/src/index.ts` — eksportuje funkcje `report` i `querySnowflake`; `querySnowflake` wykonuje `SELECT CURRENT_VERSION()` jako test połączenia ze Snowflake (deklaruje `secrets: []`).
- `functions/src/report.ts` — endpoint `/report` (HTTP, tylko `POST`):
  - parsuje multipart/form-data biblioteką **busboy**;
  - odczytuje pola `lat`, `lon` oraz pliki `voice` i `image`;
  - wywołuje `whatIsAtLocation({lat, lon})` (reverse geocoding), jeżeli `lat` i `lon` są prawdziwe;
  - zapisuje dane przez `persist(...)` do Snowflake;
  - odpowiada `200` / `500` / `400`.
- `functions/src/persist.ts` — zapis raportu do Snowflake:
  - zapisuje bufory audio i obrazu do plików tymczasowych w `/tmp`;
  - wgrywa pliki do stage'y Snowflake (`@uploads_audio`, `@uploads`) komendą `PUT`;
  - wstawia wiersz do tabeli `reports` (kolumny `lat`, `lon`, `audio_path`, `image_path`, `geo_desc`);
  - sprząta pliki tymczasowe w `finally`.
- `functions/src/snowflake.ts` — helper połączenia z Snowflake (`snowflake-sdk`); baza `CIVIL42`, schemat `public`, warehouse `civil42wh`.
- `functions/src/whatIsAtLocation.ts` — reverse geocoding przez publiczne API `nominatim.openstreetmap.org/reverse` (User-Agent `Civil42PWA/1.0`), zwraca `display_name`.

### 1.3. Przechowywanie danych

Docelowy magazyn to **Snowflake**:

- baza danych `CIVIL42`, schemat `public`, warehouse `civil42wh`;
- stage'e plików `@uploads` (obrazy) i `@uploads_audio` (nagrania);
- tabela `reports` (zgodnie z komentarzem DDL w `persist.ts`): `id` (UUID), `created_at`, `lat`, `lon`, `audio_path`, `image_path`.

**Uwaga:** DDL z komentarza **nie zawiera** kolumny `geo_desc`, a instrukcja `INSERT` w tym samym pliku **jej używa** — i dodatkowo ma 5 placeholderów przy tylko 4 bindach, a `desc` nie jest w ogóle użyty (pełny opis w sekcji 7, F2).

### 1.4. Wdrożenie / hosting

- `firebase.json` — hosting statyczny z `dist`; przepisania:
  - `/report` → funkcja `report`,
  - `/snow` → funkcja `querySnowflake`;
  - funkcje z `functions`, `predeploy`: `pnpm --prefix "$RESOURCE_DIR" run build`.
- `.firebaserc` — projekt Firebase **`civil42poc`**.
- `.github/workflows/deploy.yml` — po pushu na `master`: instaluje pnpm, buduje i wdraża frontend na **Surge** (`Civil42.surge.sh`, skrypt `deploy` w `package.json`).
- `.github/workflows/firebase-hosting-pull-request.yml` — na PR buduje i publikuje **podgląd na Firebase Hosting** (project `civil42poc`).
- `.nvmrc` — Node `v24` (przy funkcjach wymagających Node 22 — potencjalna niespójność wersji, patrz sekcja 7).

### 1.5. Przepływ użytkownika end-to-end (tak, jak to wynika z kodu)

1. Użytkownik otwiera PWA i udziela zgód na kamerę, mikrofon i lokalizację.
2. Nagrywanie audio startuje od razu (ciągłe).
3. Dotknięcie podglądu kamery → klatka zapisana do `<canvas>`, kamera i mikrofon zatrzymane.
4. `App.submit` buduje multipart (zdjęcie PNG + audio webm + `lat`/`lon`) i wysyła na `/report`.
5. Funkcja `report` parsuje dane, dopisuje opis lokalizacji (Nominatim) i zapisuje do Snowflake.
6. Frontend wyświetla odpowiedź tekstową serwera w nakładce.

### 1.6. Inwentarz plików (skrót)

| Obszar | Pliki | Rola |
|---|---|---|
| Frontend | `index.html`, `src/main.tsx`, `src/app.tsx`, `src/Camera.tsx`, `src/useRecordAudio.tsx`, `src/send.tsx` | UI, kamera, mikrofon, wysyłka |
| Stan (martwy) | `src/state/state.tsx`, `src/state/update.ts` | pusty szkielet stanu globalnego |
| Testy | `src/app.spec.tsx` | test pozorny |
| Backend | `functions/src/index.ts`, `report.ts`, `persist.ts`, `snowflake.ts`, `whatIsAtLocation.ts` | endpointy, zapis, geokodowanie |
| Konfiguracja | `firebase.json`, `.firebaserc`, `package.json`, `functions/package.json`, `vite.config.ts`, `tsconfig*.json` | hosting, PWA, build |
| CI/CD | `.github/workflows/deploy.yml`, `firebase-hosting-pull-request.yml` | wdrożenia |

---

## 2. Porównanie z pomysłem z burzy mózgów

### 2.1. Ważne zastrzeżenie (brak dokumentu z pomysłem)

W repozytorium roboczym **nie ma dokumentu opisującego pomysł z burzy mózgów**. Sprawdzono:

- `README.md` (repo robocze) — zawiera wyłącznie cel zadania, bez treści pomysłu;
- `docs/` — `CHECKUP.md`, `CONTEXT.md`, `DIRECTIVE.md`, `docs/lessons/*.md` to puste/techniczne szablony;
- docelowe repo `civil42pwa-public` — nie zawiera `README.md` ani żadnego opisu pomysłu (na GitHubie strona repozytorium ma „No description, website, or topics provided").

Dlatego **uczciwe porównanie 1:1 nie jest możliwe bez tego dokumentu**. Aby mimo to odpowiedzieć na polecenie, poniżej przyjmuję **model roboczy pomysłu**, wywnioskowany wyłącznie z: nazwy projektu (**Civil42**), tytułu zadania (**„incydenty"**) oraz tego, co kod już próbuje realizować. Każdy element tego modelu jest **założeniem do potwierdzenia** — nie należy go traktować jako faktycznej treści burzy mózgów.

### 2.2. Przyjęty model roboczy pomysłu (założenia)

Przyjmuję, że pomysł dotyczy **mobilnego systemu zgłaszania incydentów / zdarzeń w terenie** dla organizacji obywatelskiej, służb lub wolontariuszy, z naciskiem na:

- szybkie zgłoszenie „jednym dotknięciem" (zdjęcie + notatka głosowa + lokalizacja);
- automatyczne dopełnienie lokalizacji (adres) na podstawie GPS;
- centralny rejestr zgłoszeń z możliwością przeglądania i obsługi (statusy, mapa);
- działanie w terenie, w tym **offline** (słaby/brak zasięgu);
- prywatność i zgodność (RODO) dla lokalizacji i nagrań;
- identyfikację zgłaszającego / uprawnienia;
- docelowo powiadomienia i koordynację reakcji.

_Powyższe jest rekonstrukcją, a nie cytatem pomysłu — do potwierdzenia, gdy dokument z burzy mózgów zostanie dostarczony._

### 2.3. Tabela porównawcza (model roboczy vs stan kodu)

| Obszar pomysłu (założenie) | Stan w obecnym kodzie | Luka |
|---|---|---|
| Zgłoszenie jednym dotknięciem (zdjęcie) | ✅ Zaimplementowane (`Camera.tsx`, tap → klatka) | Brak podglądu/potwierdzenia przed wysłaniem |
| Notatka głosowa | ✅ Zaimplementowane (`useRecordAudio.tsx`) | Brak kontroli nad długością / ponownym nagraniem; cicha awaria mikrofonu |
| Lokalizacja GPS | ✅ Zaimplementowane (`use-geo-location`, `lat`/`lon`) | Brak obsługi braku zgody/GPS; możliwe wysłanie `undefined` |
| Automatyczny adres (reverse geocoding) | ✅ Zaimplementowane (`whatIsAtLocation.ts`, Nominatim) | Blokuje zapis przy awarii; prywatność i limity API nieobsłużone |
| Wysyłka do backendu | ✅ Zaimplementowane (`send.tsx`, `report.ts`) | Brak walidacji, limitów, auth; brak kolejki offline |
| Centralny rejestr (zapis) | ⚠️ Częściowo (`persist.ts` → Snowflake) | Poświadczenia to placeholdery; zapis niespójny (DDL vs INSERT vs bindy, gubiony `desc`) |
| Przeglądanie zgłoszeń / mapa / statusy | ❌ Brak | Brak jakiegokolwiek UI odczytu |
| Praca offline | ❌ Brak | Zgłoszenie ginie przy braku sieci |
| Uwierzytelnianie / role | ❌ Brak | Endpoint publiczny, anonimowe raporty |
| Prywatność / RODO | ❌ Brak | Brak zgód, notatek, retencji; GPS do podmiotu trzeciego |
| Powiadomienia / koordynacja | ❌ Brak | Brak |
| Jakość / testy / CI | ⚠️ Minimalnie | Test pozorny; niespójna ścieżka wdrożenia |

---

## 3. Co jest już zrobione w obecnym kodzie

**Frontend (PWA):**

- [x] Szkielet PWA z manifestem i generowaniem ikon (`vite.config.ts`, `public/icon.png`).
- [x] Podgląd tylnej kamery i przechwytywanie klatki do `<canvas>` (`Camera.tsx`).
- [x] Nagrywanie dźwięku do `audio/webm` (`useRecordAudio.tsx`).
- [x] Pobieranie geolokalizacji (`use-geo-location` w `app.tsx`).
- [x] Wysyłka multipart (zdjęcie + audio + GPS) na `/report` (`send.tsx`).
- [x] `ErrorBoundary` i podstawowy stan etykiety statusu (`main.tsx`, `app.tsx`).

**Backend (Firebase Cloud Functions):**

- [x] Endpoint `/report` przyjmujący multipart/form-data i parsujący go (busboy) — `report.ts`.
- [x] Reverse geocoding przez Nominatim/OSM — `whatIsAtLocation.ts`.
- [x] Struktura zapisu do Snowflake: pliki tymczasowe → `PUT` do stage'y → `INSERT` do `reports` — `persist.ts`.
- [x] Helper połączenia z Snowflake (`snowflake-sdk`) — `snowflake.ts`.
- [x] Endpoint testowy `/snow` (`SELECT CURRENT_VERSION()`) — `index.ts`.

**Konfiguracja / wdrożenie:**

- [x] Firebase Hosting + rewrites `/report` i `/snow` — `firebase.json`.
- [x] Dwa workflow CI (deploy na Surge; podgląd Firebase na PR).

**Co jest tylko „szkicem" mimo że istnieje plik:** poświadczenia Snowflake to literały-placeholdery, `state.tsx`/`update.ts` to martwy kod, test jest pozorny, a komentarz `TODO: Implement storage/database logic` w `report.ts` jest nieaktualny (bo `persist()` już jest wywoływane).

---

## 4. Co trzeba jeszcze zrobić, aby powstał PoC

**Definicja PoC (przyjęta):** minimalny, działający pion weryfikujący ścieżkę „przechwycenie → wysyłka → zapis" dla jednego testera, bez wymagań produkcyjnych.

1. **Podłączyć prawdziwe poświadczenia Snowflake** (przez Secret Manager / zmienne środowiskowe) zamiast literałów `'[SNOWFLAKE-ACCOUNT]'`, `'[SNOWFLAKE-USERNAME]'`, `'[SNOWFLAKE-TOKEN]'` w `snowflake.ts` — inaczej zapis nie zadziała. Alternatywnie (na czas PoC) tymczasowo podmienić magazyn na coś prostszego (np. Firebase Storage + Firestore), pozostawiając moduł `persist` jako punkt wymiany.
2. **Naprawić zapis w `persist()` — to bug potrójny, nie tylko różnica w DDL.** (a) DDL (komentarz) nie zawiera kolumny `geo_desc`; (b) `INSERT` ma **5** placeholderów (`lat, lon, audio_path, image_path, geo_desc`), a `executeQuery` dostaje tylko **4** bindy `[lat, lon, audio_path, image_path]`; (c) `loc.desc` (adres z reverse geocodingu, przekazywany z `report.ts` jako `{lat, lon, desc}`) nie jest w ogóle użyty w `persist()`. Minimalna poprawka PoC: dodać `geo_desc` do DDL **i** przekazać `loc.desc` jako piąty bind — np. `[loc.lat, loc.lon, @uploads_audio/…, @uploads/…, loc.desc]` (albo konsekwentnie usunąć `geo_desc` z `INSERT`; ale wtedy tracimy adres, który jest istotny dla produktu).
3. **Dodać minimalną walidację wejścia** w `report.ts`: wymagać obecności plików `voice` i `image`, walidować `lat`/`lon` jako liczby, a przy braku któregoś pola zwracać czytelny błąd 400 zamiast wyjątku 500.
4. **Uczynić geokodowanie nieblokującym**: awaria/limit Nominatim nie może powodować utraty raportu — zapisuj raport także wtedy, gdy opis adresu się nie uda (adres jako wartość opcjonalna).
5. **Domknąć ścieżkę wdrożenia**, żeby względne `POST /report` trafiało do funkcji: hostować frontend i funkcje razem (Firebase Hosting z rewrites) albo wysyłać na jawny URL funkcji. Obecny deploy produkcyjny na Surge nie obsługuje przepisania `/report`.
6. **Naprawić krawędź GPS na froncie**: nie wysyłać zgłoszenia, zanim lokalizacja nie będzie gotowa (albo jawnie wysłać brak lokalizacji), oraz pokazać użytkownikowi błąd dostępu do mikrofonu/kamery (teraz mikrofon psuje się cicho w `console.error`).
7. **Wykonać ręczny test end-to-end**: zdjęcie + audio + GPS → wiersz w Snowflake, i potwierdzić, że raport jest kompletny.
8. **Usunąć mylące pozostałości**: nieaktualny komentarz `TODO` w `report.ts` i pozorny test w `app.spec.tsx` (albo zastąpić go minimalnym testem rzeczywistej logiki).

**Efekt PoC:** jedna osoba może na żywo zrobić zdjęcie, nagrać notatkę i zobaczyć zapisany raport w Snowflake — bez wymagań produkcyjnych.

---

## 5. Co trzeba jeszcze zrobić, aby powstał MVP

**Definicja MVP (przyjęta):** wersja nadająca się do używania przez małą, realną grupę użytkowników w terenie.

1. **Wszystko z PoC** (sekcja 4) — jako warunek wstępny.
2. **Podgląd i potwierdzenie przed wysłaniem**: zamiast automatycznej wysyłki po dotknięciu, pokazać przechwycone zdjęcie i przyciski „wyślij"/„powtórz", aby uniknąć przypadkowych zgłoszeń.
3. **Uwierzytelnianie i podstawowa autoryzacja**: anonimowe lub konta użytkowników (Firebase Auth), a endpoint `/report` chroniony, by zgłaszać mogli tylko zamierzeni użytkownicy (a nie dowolny bot).
4. **Limity i zabezpieczenia endpointu**: limit rozmiaru plików (busboy ma domyślnie nieograniczony rozmiar), limit częstotliwości (rate limiting), sanityzacja wejścia.
5. **Przeglądanie zgłoszeń (odczyt)**: minimalny widok listy + mapy dla zgłaszającego/operatora — bez niego produkt jest „tylko do zapisu" i nieużywalny w praktyce.
6. **Obsługa offline (minimum)**: kolejka zgłoszeń w IndexedDB i wysyłka po powrocie sieci; przynajmniej nie tracić danych przy błędzie sieci (obecnie `send` zwraca „HTTP error" i raport przepada).
7. **Prywatność i zgody (RODO)**: ekran zgody na nagrywanie i lokalizację, informacja o tym, że dokładne współrzędne trafiają do geokodera zewnętrznego; podstawowa polityka retencji.
8. **Geokodowanie z cache i fallbackiem**: lokalny cache adresów, przestrzeganie limitu Nominatim (1 żądanie/s), a w razie niedostępności — zapis bez adresu (nie blokować zgłoszenia).
9. **Spójny język UX**: polskie komunikaty także po stronie serwera (obecnie „Report received successfully"), poprawa literówki „Nacinij" → „Naciśnij".
10. **Komunikaty błędów dla użytkownika**: spójne toasty/etykiety zamiast surowego `HTTP error! status: ...` i cichego błędu mikrofonu.
11. **Finalny model danych**: tabela `reports` z kolumnami zgodnymi z kodem (`geo_desc`, `status`, `created_at`, identyfikator urządzenia/zgłaszającego) i spójnym schematem.
12. **Realne testy** (jednostkowe i jeden test E2E ścieżki wysyłki) zamiast `expect(true).toBe(true)`.
13. **Jedna spójna ścieżka CI/CD**: frontend + funkcje na jednym hoście (Firebase Hosting), usunięcie niejednoznaczności Surge/Firebase.

**Efekt MVP:** mała grupa może zgłaszać incydenty z telefonu i je przeglądać; zgłoszenia nie giną offline; dostęp jest chroniony; podstawowe wymogi prywatności są spełnione.

---

## 6. Co trzeba jeszcze zrobić, aby powstał gotowy produkt w wersji beta

**Definicja beta (przyjęta):** wersja przygotowana do szerszych testów produkcyjnych — stabilna, bezpieczna, skalowalna i zgodna.

1. **Wszystko z MVP** (sekcja 5) — jako warunek wstępny.
2. **Role i uprawnienia**: zgłaszający / dyspozytor / administrator, zarządzanie użytkownikami, kontrola dostępu do raportów.
3. **Cykl życia zgłoszenia**: statusy (nowe → w toku → zamknięte), komentarze, historia zmian (audit log), przypisywanie zgłoszeń.
4. **Skalowalna architektura przechowywania**: pliki w obiektowym storage (Firebase/Cloud Storage) z metadanymi w Snowflake/Firestore, URL-e sygnowane, CDN; obecne wgrywanie plików do stage'y Snowflake nie jest typowym rozwiązaniem produkcyjnym dla mediów.
5. **Geokodowanie produkcyjne**: własna instancja geokodera (np. Photon/Nominatim) lub płatny geokoder z SLA, cache, bez wycieku dokładnych współrzędnych do stron trzecich.
6. **Bezpieczeństwo**: poświadczenia wyłącznie w Secret Manager (usunąć literały), walidacja i limity wejścia, skanowanie przesłanych plików, podpisywane uploady, WAF/ochrona przed nadużyciami.
7. **Niezawodność**: retry z idempotencją, kolejka dead-letter, monitorowanie i alerty, logowanie strukturalne, śledzenie błędów.
8. **Offline-first + synchronizacja**: w pełni działający service worker, kolejka z synchronizacją w tle, odporność na restart aplikacji.
9. **Powiadomienia**: push o zmianie statusu/przypisaniu zgłoszenia.
10. **Zgodność i prywatność (RODO)**: prawo dostępu/usunięcia, eksport danych, polityka retencji, anonimizacja, audyt zgód.
11. **Wydajność**: kompresja/przeskalowanie zdjęć przed wysyłką, rozsądny bitrate audio, leniwe ładowanie, obsługa dużych wolumenów zgłoszeń.
12. **Jakość i obserwowalność**: telemetria (z poszanowaniem prywatności), raportowanie crashy, testy E2E, środowisko staging, testy obciążeniowe.
13. **UX i dostępność**: mobilny, dostępny (WCAG) interfejs, onboarding, obsługa błędów uprawnień, spójny język.
14. **Dokumentacja operatora**: jak wdrażać, konfigurować, monitorować i obsługiwać system.

**Efekt beta:** stabilny, bezpieczny i skalowalny system gotowy do testów produkcyjnych na szerszej grupie, z pełnym cyklem życia zgłoszenia i zgodnością regulacyjną.

---

## 7. Zidentyfikowane problemy i ryzyka techniczne w obecnym kodzie

Poniższe ustalenia wynikają wyłącznie z lektury plików (nie uruchamiano aplikacji).

| # | Problem | Miejsce | Skutek |
|---|---|---|---|
| F1 | Poświadczenia Snowflake to literały-placeholdery (`'[SNOWFLAKE-ACCOUNT]'`, `'[SNOWFLAKE-USERNAME]'`, `'[SNOWFLAKE-TOKEN]'`), a `querySnowflake` deklaruje `secrets: []` | `functions/src/snowflake.ts`, `functions/src/index.ts` | Backend nie połączy się z realną bazą; komentarz o Secret Managerze nie jest zrealizowany |
| F2 | `persist()` ma **trzy** niespójności zapisu: (1) DDL (komentarz) nie zawiera kolumny `geo_desc`; (2) `INSERT` ma **5** placeholderów (`lat, lon, audio_path, image_path, geo_desc`), ale `executeQuery` dostaje tylko **4** bindy; (3) przekazany `desc` (adres z reverse geocodingu, `{lat, lon, desc}` w `report.ts`) nigdy nie jest użyty w `persist()` | `functions/src/persist.ts`, `functions/src/report.ts` | `INSERT` nie wykona się (mismatch liczby bindów) nawet po dodaniu `geo_desc` do DDL; adres z geokodowania jest po cichu gubiony — ścieżka zapisu nie zadziała |
| F3 | Brak walidacji wejścia: dostęp do `voice.buffer`/`image.buffer` bez sprawdzenia obecności; `Number(fields.lat)` może dać `NaN` | `functions/src/report.ts` | Błędne/malformowane żądanie → wyjątek 500; `NaN` może trafić do bazy |
| F4 | Reverse geocoding jest `await`-owane **przed** zapisem; wysyła dokładne współrzędne do Nominatim/OSM; brak cache i limitu 1 rq/s | `functions/src/report.ts`, `whatIsAtLocation.ts` | Awaria/limit geokodera = utrata raportu; ryzyko prywatności |
| F5 | Brak limitu rozmiaru plików (busboy z domyślnymi limitami) i brak autoryzacji/rate limitingu | `functions/src/report.ts` | Nadużycia, koszty, DoS |
| F6 | Cichy błąd mikrofonu (`console.error`); możliwość wysłania `gps.latitude`/`longitude` jako `undefined` przed gotowością lokalizacji | `useRecordAudio.tsx`, `app.tsx` | Użytkownik nie wie o problemie; serwer dostaje `"undefined"` |
| F7 | Ciągłe nagrywanie od startu strony, bez gestu użytkownika | `app.tsx` | Prywatność/bateria/RODO; możliwe blokady autoodtwarzania |
| F8 | Test pozorny `expect(true).toBe(true)` | `app.spec.tsx` | Brak realnej ochrony przed regresjami |
| F9 | Martwy/nieużywany kod (`state.tsx` pusty, `update.ts`, `resetState`), nieaktualny komentarz `TODO: Implement storage/database logic` | `src/state/*`, `functions/src/report.ts` | Dezorientacja, niezgodność z dyrektywą jakości |
| F10 | Niespójna ścieżka wdrożenia: produkcja na Surge (statyczne), ale funkcje i rewrites w Firebase Hosting | `package.json`, `deploy.yml`, `firebase.json` | Względne `POST /report` nie zadziała na Surge |
| F11 | Literówka „Nacinij" i angielska odpowiedź serwera w polskiej aplikacji | `app.tsx`, `report.ts` | Jakość UX/spójność języka |
| F12 | `.nvmrc` = `v24` vs funkcje wymagające Node 22 | `.nvmrc`, `functions/package.json` | Potencjalne różnice runtime/CI |

---

## 8. Źródła

**Kod (klon lokalny, commit `429f9bc`):**

- `civil42pwa-public/index.html`, `src/main.tsx`, `src/app.tsx`, `src/Camera.tsx`, `src/useRecordAudio.tsx`, `src/send.tsx`, `src/state/state.tsx`, `src/state/update.ts`, `src/app.spec.tsx`
- `civil42pwa-public/functions/src/index.ts`, `functions/src/report.ts`, `functions/src/persist.ts`, `functions/src/snowflake.ts`, `functions/src/whatIsAtLocation.ts`
- `civil42pwa-public/firebase.json`, `.firebaserc`, `package.json`, `functions/package.json`, `vite.config.ts`, `.nvmrc`, `.github/workflows/deploy.yml`, `.github/workflows/firebase-hosting-pull-request.yml`

**Strona repozytorium (dostęp: 2026-09-07):**

- https://github.com/rzymek/civil42pwa-public — repozytorium publiczne; brak opisu, README i tematów („No description, website, or topics provided").

**Uwaga o źródłach zewnętrznych:** analiza opiera się na kodzie i konfiguracji w repozytorium. Nie wykorzystano dokumentu z burzy mózgów, ponieważ nie został on dostarczony (patrz sekcja 2.1).

---

## 9. Otwarte pytania / założenia

1. **Brak dokumentu z burzy mózgów** — to najważniejsza luka wejściowa. Sekcja 2 opiera się na modelu roboczym oznaczonym jako założenie; po dostarczeniu dokumentu należy zaktualizować tabelę porównawczą 1:1.
2. **Docelowy magazyn danych** — kod wskazuje Snowflake, ale nie wiadomo, czy to świadomy wybór docelowy, czy tymczasowy. Wpływa to na zakres MVP/beta (sekcja 6, pkt 4).
3. **Docelowa grupa użytkowników i role** — nieznana; przyjęto ogólny model „zgłaszający / dyspozytor / administrator".
4. **Czy nagrywanie ma być ciągłe, czy na żądanie** — kod nagrywa ciągle; to decyzja produktowa i prywatnościowa do potwierdzenia.
5. **Wymagania regulacyjne (RODO)** — przyjęto, że będą obowiązywać, bo zbierane są lokalizacja i nagrania; konkretny zakres (podmiot, retencja) do potwierdzenia.
