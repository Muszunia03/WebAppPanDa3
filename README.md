# PanDa3

## Członkowie zespołu
- Dawid Widawski
- Mikołaj Mach

## Wybrany język
Python (framework Flask, baza danych SQLite)

## Krótki opis
- **Jaki problem rozwiązuje aplikacja?** Rozwiązuje problem rozproszonej, łatwej do zgubienia papierowej dokumentacji medycznej zwierząt domowych (książeczki, wyniki badań) oraz braku bezpiecznego, w pełni kontrolowanego sposobu jej udostępniania lekarzom weterynarii.
- **Kto będzie z niej korzystał?** Właściciele zwierząt domowych oraz lekarze weterynarii.
- **Dlaczego aplikacja jest potrzebna?** Pozwala zgromadzić całą historię zdrowotną zwierzęcia w jednym, centralnym miejscu. Zapewnia właścicielowi wyłączną decyzyjność w kwestii tego, który lekarz i przez jaki czas ma wgląd w dane jego pupila.
- **Jaką podstawową czynność umożliwia?** Umożliwia dodanie profilu zwierzęcia, bezpieczne wgranie dokumentacji medycznej i wygenerowanie kodu dostępu, który pozwala wybranemu weterynarzowi na odczyt teczki oraz dodanie nowego wpisu z diagnozą.

## Funkcje aplikacji
**Konto**
- Rejestracja i logowanie z wyborem roli: właściciel lub weterynarz (weterynarz podaje numer PWZ).
- Wylogowanie.

**Właściciel zwierzęcia**
- Dodawanie zwierząt (imię, gatunek, opcjonalne zdjęcie), edycja danych i usuwanie wraz z powiązanymi plikami.
- Wgrywanie dokumentów medycznych (PDF, JPG, PNG, do 5 MB), pobieranie i usuwanie.
- Generowanie kodów dostępu dla weterynarza (ważność 1 godzina, 24 godziny lub 7 dni) oraz ich ręczne odwoływanie.
- Podgląd historii medycznej zwierzęcia.

**Weterynarz**
- Wpisanie kodu otrzymanego od właściciela i wgląd w kartotekę zwierzęcia.
- Pobieranie dokumentów zwierzęcia.
- Dodawanie wpisów medycznych (diagnoza, waga, temperatura).

## Zabezpieczenia
- Hasła są przechowywane wyłącznie jako hash (scrypt), nigdy jawnym tekstem.
- Wymagania hasła: 8-128 znaków, co najmniej jedna litera i jedna cyfra.
- Kontrola dostępu: użytkownik widzi i modyfikuje tylko swoje zasoby, a weterynarz ma dostęp wyłącznie do zwierzęcia, dla którego ma ważny kod.
- Ochrona CSRF we wszystkich formularzach, wylogowanie tylko metodą POST.
- Limit prób: 5 logowań na minutę, 10 użyć kodu dostępu na minutę.
- Walidacja danych po stronie serwera (puste pola, długości, format e-mail i numeru PWZ, zakresy wagi i temperatury).
- Walidacja plików: dozwolone rozszerzenia, zgodność zawartości z rozszerzeniem (sygnatura), limit 5 MB, losowe nazwy plików na dysku.
- Ciasteczka sesji z flagami HttpOnly i SameSite, sesja wygasa po 30 minutach.
- Dane poufne w pliku `.env`, nie w kodzie.

## Wymagania środowiskowe
- Python 3.10 lub nowszy
- pip (menedżer pakietów Pythona)
- git (do pobrania repozytorium)

Wszystkie wymagane biblioteki wraz z wersjami znajdują się w pliku `requirements.txt`.

## Instalacja
1. Pobierz repozytorium i wejdź do jego katalogu:
   ```
   git clone https://github.com/Muszunia03/WebAppPanDa3.git
   cd WebAppPanDa3
   ```
2. Utwórz i aktywuj wirtualne środowisko:
   ```
   python -m venv .venv

   # Windows (PowerShell)
   .venv\Scripts\Activate.ps1

   # Linux / macOS
   source .venv/bin/activate
   ```
3. Zainstaluj zależności:
   ```
   pip install -r requirements.txt
   ```
4. (Opcjonalnie) Skopiuj plik z przykładową konfiguracją i ustaw własne wartości:
   ```
   # Windows (PowerShell)
   copy .env.example .env

   # Linux / macOS
   cp .env.example .env
   ```
   Aplikacja uruchomi się także bez pliku `.env`. Wtedy używa wartości domyślnych, a klucz sesji jest generowany losowo przy każdym starcie (po restarcie trzeba zalogować się ponownie).

## Konfiguracja (plik `.env`)
Plik `.env` nie jest przechowywany w repozytorium. Szablon znajduje się w `.env.example`.

| Zmienna | Opis | Domyślnie |
|---|---|---|
| `SECRET_KEY` | klucz do podpisywania sesji | losowy przy starcie |
| `DATABASE_URI` | adres bazy danych | `sqlite:///panda3.db` |
| `SESSION_COOKIE_SECURE` | `True` przy działaniu przez HTTPS | `False` |
| `HOST` | adres, na którym działa serwer | `127.0.0.1` |
| `PORT` | port serwera | `5000` |
| `DEBUG` | tryb debugowania (nie włączać na produkcji) | `False` |

## Uruchomienie
Aplikację uruchamia jedno polecenie (z katalogu głównego projektu):
```
python app/main.py
```
Baza danych i wszystkie tabele tworzą się automatycznie przy starcie, nie trzeba nic tworzyć ręcznie. Plik bazy powstaje w katalogu `instance/`.

## Adres aplikacji
http://127.0.0.1:5000

## Baza danych
Baza SQLite, tabele powiązane relacją po identyfikatorze użytkownika:

| Tabela | Opis | Relacje |
|---|---|---|
| `user` | konta (imię, nazwisko, e-mail, hash hasła, rola, numer PWZ) | |
| `pet` | zwierzęta | `owner_id` → `user.id` |
| `document` | wgrane dokumenty | `pet_id` → `pet.id` |
| `medical_record` | wpisy medyczne | `pet_id` → `pet.id`, `vet_id` → `user.id` |
| `access_code` | kody dostępu z datą wygaśnięcia | `pet_id` → `pet.id` |

## Endpointy
### `GET /health`
Sprawdza, czy aplikacja jest uruchomiona. Endpoint jest dostępny bez logowania.

- **Kod odpowiedzi:** `200 OK`
- **Odpowiedź (JSON):**
  ```json
  {
    "status": "ok"
  }
  ```

### Pozostałe trasy
| Metoda | Adres | Dostęp |
|---|---|---|
| GET | `/` | publiczny |
| GET, POST | `/register`, `/login` | publiczny |
| POST | `/logout` | zalogowany |
| GET | `/dashboard` | zalogowany |
| POST | `/add_pet`, `/edit_pet/<id>`, `/delete_pet/<id>` | właściciel zwierzęcia |
| GET, POST | `/pet/<id>` (podgląd, wgranie dokumentu) | właściciel zwierzęcia |
| GET | `/download/<id>` | właściciel dokumentu |
| POST | `/delete_document/<id>` | właściciel dokumentu |
| POST | `/generate_code/<id>`, `/revoke_code/<id>` | właściciel zwierzęcia |
| POST | `/vet/access` | weterynarz |
| GET | `/vet/pet/<kod>`, `/vet/download/<kod>/<id>` | weterynarz z ważnym kodem |
| POST | `/vet/add_record/<kod>` | weterynarz z ważnym kodem |

Formularze (POST) wymagają tokenu CSRF, więc najwygodniej korzystać z aplikacji w przeglądarce.

## Kody odpowiedzi
| Kod | Znaczenie |
|---|---|
| 200 | sukces |
| 302 | przekierowanie (np. po zapisie formularza, niezalogowany użytkownik trafia na `/login`) |
| 400 | błędne dane (walidacja, brak tokenu CSRF) |
| 401 | błędny e-mail lub hasło |
| 403 | brak uprawnień (cudzy zasób, zła rola, nieważny kod) |
| 404 | nie znaleziono zasobu |
| 409 | e-mail jest już zarejestrowany |
| 413 | plik większy niż 5 MB |
| 429 | zbyt wiele prób |
| 500 | błąd serwera |

## Przykładowe żądania
Sprawdzenie statusu aplikacji.

Linux / macOS:
```
curl -i http://127.0.0.1:5000/health
```

Windows (PowerShell), w którym `curl` jest aliasem innego polecenia, więc trzeba użyć `curl.exe`:
```
curl.exe -i http://127.0.0.1:5000/health
```

Przykładowa odpowiedź:
```
HTTP/1.1 200 OK
Content-Type: application/json

{"status":"ok"}
```

Dostęp do panelu bez logowania (przekierowanie na stronę logowania):
```
curl -i http://127.0.0.1:5000/dashboard
```
```
HTTP/1.1 302 FOUND
Location: /login?next=%2Fdashboard
```

Nieistniejąca strona:
```
curl -i http://127.0.0.1:5000/nie-ma-takiej-strony
```
```
HTTP/1.1 404 NOT FOUND

Nie znaleziono strony.
```

## Szybki test ręczny w przeglądarce
1. Otwórz http://127.0.0.1:5000/register i załóż dwa konta: właściciela (np. `jan.kowalski@example.com`, hasło `Panda12345`) oraz weterynarza (np. `anna.nowak@example.com`, hasło `Weterynarz123`, numer PWZ `1234567`).
2. Zaloguj się jako właściciel, dodaj zwierzę, wgraj dokument PDF i wygeneruj kod dostępu.
3. Wyloguj się, zaloguj jako weterynarz, wpisz kod, pobierz dokument i dodaj wpis medyczny.
4. Zaloguj się ponownie jako właściciel i sprawdź, że wpis jest widoczny w historii.

## Struktura projektu
```
app/              kod aplikacji (main.py, templates/, static/)
tests/            testy aplikacji (na tym etapie puste)
.env.example      szablon konfiguracji
.gitignore        pliki wykluczone z repozytorium
requirements.txt  zależności wraz z wersjami
README.md         dokumentacja
```