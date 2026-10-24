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

## Wymagania środowiskowe
- Python 3.10 lub nowszy
- pip (menedżer pakietów Pythona)
- git (do pobrania repozytorium)

Wszystkie wymagane biblioteki wraz z wersjami znajdują się w pliku `requirements.txt`.

## Instalacja
1. Pobierz repozytorium i wejdź do jego katalogu:
   ```
   git clone <adres-repozytorium>
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
   Aplikacja uruchomi się także bez pliku `.env`. Wtedy używa wartości domyślnych, a klucz sesji jest generowany losowo przy każdym starcie.

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
Baza danych i wszystkie tabele tworzą się automatycznie przy starcie, nie trzeba nic tworzyć ręcznie.

## Adres aplikacji
http://127.0.0.1:5000

## Endpoint
### `GET /health`
Sprawdza, czy aplikacja jest uruchomiona. Endpoint jest dostępny bez logowania.

- **Kod odpowiedzi:** `200 OK`
- **Odpowiedź (JSON):**
  ```json
  {
    "status": "ok"
  }
  ```

## Przykładowe żądania
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

## Struktura projektu
```
app/              kod aplikacji (main.py, templates/, static/)
tests/            testy aplikacji (na tym etapie puste)
.env.example      szablon konfiguracji
.gitignore        pliki wykluczone z repozytorium
requirements.txt  zależności wraz z wersjami
README.md         dokumentacja
```