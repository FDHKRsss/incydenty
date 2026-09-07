# Known issues

_Recurring walls/gotchas and how to get past them. One bullet each._

- Weryfikując ścieżkę zapisu w kodzie (np. SQL `INSERT`), sprawdź cały łańcuch: liczbę placeholderów vs liczbę bindów oraz czy każdy przekazany pola jest faktycznie użyty. Lokalna poprawka (np. dodanie kolumny do DDL) nie domyka ścieżki, gdy wciąż jest mismatch bindów albo pole jest po cichu gubione (przykład: `functions/src/persist.ts` w `civil42pwa-public`).
