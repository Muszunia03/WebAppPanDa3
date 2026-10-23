## Cel aplikacji, na co pozwala
PanDa3 to aplikacja webowa służąca jako cyfrowa teczka zdrowia zwierzęcia. Pozwala właścicielowi na centralne przechowywanie dokumentacji medycznej (szczepienia, badania) i jej kontrolowane udostępnianie specjalistom. Aplikacja posiada system rejestracji i logowania, przechowuje dane w relacyjnej bazie danych, a wszystkie funkcje zarządzania wpisami medycznymi oraz profilami zwierząt są chronione i dostępne wyłącznie dla uwierzytelnionych użytkowników.

## Rodzaj użytkownika/użytkowników, jakie ma możliwości
*   Właściciel: Posiada konto systemowe uzyskane poprzez rejestrację. Może dodawać, edytować i usuwać profile swoich zwierząt oraz wgrywać lub usuwać ich dokumentację medyczną. Generuje i odwołuje unikalne kody dostępu dla weterynarzy. Widzi wpisy medyczne wprowadzone przez lekarza, ale nie może ich modyfikować ani usuwać. Nie ma dostępu do profili innych właścicieli.
*   Weterynarz: Posiada konto systemowe uzyskane poprzez rejestrację. Używając kodu autoryzacyjnego otrzymanego od właściciela, zyskuje dostęp (wyłącznie do odczytu) do dokumentacji wskazanego pacjenta. Posiada uprawnienia do dodawania oficjalnych, niezmiennych dla właściciela wpisów medycznych. Nie ma uprawnień do usuwania profili zwierząt ani plików wgranych przez właścicieli.

## Wymagania funkcjonalne
1.  Aplikacja udostępnia formularze rejestracji i logowania, wymagając przypisania do konta jednej z ról docelowych (Właściciel lub Weterynarz).
2.  Interfejs użytkownika i trasy w aplikacji są odpowiednio izolowane – specyficzne narzędzia i widoki są dostępne dopiero po poprawnym rozpoczęciu sesji.
3.  Uwierzytelniony Właściciel posiada moduł do kompleksowego zarządzania (CRUD) podstawowymi danymi swoich zwierząt.
4.  System pozwala Właścicielowi na wygenerowanie czasowego kodu autoryzacyjnego z możliwością zdefiniowania czasu wygasania i opcją ręcznego odwołania w dowolnym momencie.
5.  Zalogowany Weterynarz uzyskuje dostęp do przeglądania profili i pobierania plików medycznych dopiero po poprawnej weryfikacji dostarczonego kodu pacjenta.
6.  Weterynarz posiadający aktualny dostęp do profilu zwierzęcia może utworzyć i zapisać nowy wpis medyczny powiązany z daną wizytą.

## Wymagania bezpieczeństwa
1. Bezpieczne przechowywanie haseł: Hasła są zapisywane w bazie w postaci bezpiecznych skrótów z solą (np. przez Werkzeug), nigdy jako zwykły tekst.
2. Zabezpieczenie sesji: Sesje użytkowników opierają się na ciasteczkach chronionych specjalnymi flagami (HttpOnly, Secure, SameSite) i wygasają po ustalonym czasie.
3. Ścisły podział ról: Każda funkcja w aplikacji weryfikuje uprawnienia – system upewnia się, że właściciel lub weterynarz ma prawo wykonać daną akcję.
4. Ochrona przed dostępem do cudzych danych (IDOR): Przy każdej próbie odczytu lub edycji, aplikacja weryfikuje w bazie, czy dane zwierzę faktycznie należy do żądającego użytkownika.
5. Ochrona przed SQL Injection: Do komunikacji z bazą danych wykorzystywany jest system ORM (Flask-SQLAlchemy), który automatycznie zabezpiecza wszystkie zapytania wejściowe.
6. Bezpieczny upload dokumentów: System sprawdza rzeczywisty typ wgrywanych plików, nadaje im bezpieczne nazwy i pozwala na ich pobranie wyłącznie uprawnionym osobom.
7. Ochrona przed odgadywaniem haseł (Brute-Force): Nałożono limit błędnych prób logowania oraz wpisywania kodów dostępu, aby zablokować ataki siłowe.

## Model zagrożeń

1. Dostęp do cudzych danych

Czego dotyczy: Profile zwierząt, dokumenty i wpisy.
Możliwe konsekwencje: Ktoś podgląda lub edytuje dane cudzego pacjenta (np. po prostu zmieniając numer ID w linku).
Planowana kontrola/działanie: System przy każdej akcji sprawdza w bazie, czy zalogowana osoba jest faktycznym właścicielem tych danych.

2. Wgranie złośliwego pliku

Czego dotyczy: Upload skanów i badań.
Możliwe konsekwencje: Zawirusowanie serwera, sprzętu weterynarza lub zablokowanie działania aplikacji (brak miejsca na dysku).
Planowana kontrola/działanie: Aplikacja sprawdza prawdziwą zawartość pliku (nie tylko samo rozszerzenie), ogranicza jego wagę i zmienia nazwę na bezpieczną.

3. Przejęcie sesji

Czego dotyczy: Sesje logowania i ciasteczka.
Możliwe konsekwencje: Haker wykorzystuje zalogowaną ofiarę, zmuszając jej przeglądarkę do niechcianej akcji (np. usunięcia badań).
Planowana kontrola/działanie: Zabezpieczenie ciasteczek przed kradzieżą oraz dodanie unikalnych, ukrytych tokenów sprawdzających do każdego formularza.