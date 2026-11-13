from app.main import validate_registration


def test_validate_registration_accepts_valid_owner_data():
    error = validate_registration('jan@example.com', 'Panda12345', 'Jan', 'Kowalski', 'owner', '')
    assert error is None


def test_validate_registration_rejects_invalid_email():
    error = validate_registration('jan.kowalski', 'Panda12345', 'Jan', 'Kowalski', 'owner', '')
    assert error == 'Nieprawidłowy format adresu e-mail.'


def test_validate_registration_rejects_password_without_digit():
    error = validate_registration('jan@example.com', 'abcdefgh', 'Jan', 'Kowalski', 'owner', '')
    assert error == 'Hasło musi zawierać co najmniej jedną literę i jedną cyfrę.'


def test_validate_registration_rejects_vet_without_pwz_number():
    error = validate_registration('anna@example.com', 'Weterynarz1', 'Anna', 'Nowak', 'vet', '')
    assert error == 'Weterynarz musi podać poprawny numer PWZ (5-10 cyfr).'
