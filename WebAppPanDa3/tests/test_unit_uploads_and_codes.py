"""Testy jednostkowe: walidacja plików (validate_upload) i kody dostępu (get_valid_access_code)."""
import io

from werkzeug.datastructures import FileStorage

from app.main import validate_upload, get_valid_access_code


def _upload(filename, content):
    return FileStorage(stream=io.BytesIO(content), filename=filename)


def test_validate_upload_accepts_pdf_with_valid_signature():
    assert validate_upload(_upload('wyniki.pdf', b'%PDF-1.4 tresc')) is None


def test_validate_upload_rejects_text_file_disguised_as_pdf():
    error = validate_upload(_upload('wyniki.pdf', b'to jest zwykly tekst'))
    assert error == 'Zawartość pliku nie zgadza się z jego rozszerzeniem.'


def test_get_valid_access_code_returns_active_code(flask_app, make_user, make_pet, make_code):
    pet_id = make_pet(make_user())
    code = make_code(pet_id, hours=24)

    with flask_app.app_context():
        access = get_valid_access_code(code)

    assert access is not None and access.pet_id == pet_id


def test_get_valid_access_code_returns_none_for_expired_code(flask_app, make_user, make_pet, make_code):
    code = make_code(make_pet(make_user()), hours=-1)

    with flask_app.app_context():
        assert get_valid_access_code(code) is None
