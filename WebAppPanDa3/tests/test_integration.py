import io
import os

from app.main import db, User, Pet, Document, AccessCode

PDF = b'%PDF-1.4 testowy dokument'


def _first_id(app, model, **filters):
    with app.app_context():
        return model.query.filter_by(**filters).first().id


def test_register_login_and_open_dashboard(flask_app):
    client = flask_app.test_client()

    registered = client.post('/register', data={
        'first_name': 'Jan', 'last_name': 'Kowalski', 'email': 'jan@example.com',
        'password': 'Panda12345', 'role': 'owner'})
    logged_in = client.post('/login', data={'email': 'jan@example.com', 'password': 'Panda12345'})
    dashboard = client.get('/dashboard')

    assert registered.status_code == 302 and '/login' in registered.headers['Location']
    assert logged_in.status_code == 302 and '/dashboard' in logged_in.headers['Location']
    assert dashboard.status_code == 200 and 'jan@example.com' in dashboard.get_data(as_text=True)
    with flask_app.app_context():
        stored = User.query.filter_by(email='jan@example.com').one()
        assert stored.password_hash.startswith('scrypt:') and 'Panda12345' not in stored.password_hash


def test_owner_adds_edits_and_deletes_pet(flask_app, login_as):
    client = login_as('jan@example.com')

    client.post('/add_pet', data={'name': 'Burek', 'species': 'Pies'})
    assert 'Burek' in client.get('/dashboard').get_data(as_text=True)

    pet_id = _first_id(flask_app, Pet, name='Burek')
    client.post(f'/edit_pet/{pet_id}', data={'name': 'Burek II', 'species': 'Kot'})
    details = client.get(f'/pet/{pet_id}').get_data(as_text=True)
    assert 'Burek II' in details and 'Kot' in details

    client.post(f'/delete_pet/{pet_id}')
    assert 'Burek' not in client.get('/dashboard').get_data(as_text=True)
    with flask_app.app_context():
        assert Pet.query.count() == 0


def test_owner_uploads_downloads_and_deletes_document(flask_app, login_as, make_pet):
    client = login_as('jan@example.com')
    pet_id = make_pet(client.user_id)
    upload_dir = flask_app.config['UPLOAD_FOLDER']

    client.post(f'/pet/{pet_id}', data={'document': (io.BytesIO(PDF), 'wyniki.pdf')},
                content_type='multipart/form-data')
    saved = os.listdir(upload_dir)
    assert len(saved) == 1 and saved[0].endswith('_wyniki.pdf') and saved[0] != 'wyniki.pdf'

    doc_id = _first_id(flask_app, Document, pet_id=pet_id)
    # `with` zamyka odpowiedź i zwalnia uchwyt do pliku (na Windows inaczej os.remove daje WinError 32)
    with client.get(f'/download/{doc_id}') as downloaded:
        assert downloaded.status_code == 200 and downloaded.data == PDF

    client.post(f'/delete_document/{doc_id}')
    assert os.listdir(upload_dir) == []
    with flask_app.app_context():
        assert Document.query.count() == 0


def test_vet_reads_pet_with_access_code_and_adds_medical_record(flask_app, login_as, make_pet):
    owner = login_as('jan@example.com')
    vet = login_as('anna@example.com', role='vet', first_name='Anna', last_name='Nowak')
    pet_id = make_pet(owner.user_id, name='Burek')

    owner.post(f'/generate_code/{pet_id}', data={'expires_in': '24'})
    with flask_app.app_context():
        code = AccessCode.query.filter_by(pet_id=pet_id).one().code

    accessed = vet.post('/vet/access', data={'code': code})
    card = vet.get(f'/vet/pet/{code}')
    added = vet.post(f'/vet/add_record/{code}', data={
        'diagnosis': 'Kontrola ogólna', 'weight': '12,5', 'temperature': '38.5'})
    owner_view = owner.get(f'/pet/{pet_id}').get_data(as_text=True)

    assert accessed.status_code == 302 and code in accessed.headers['Location']
    assert card.status_code == 200 and 'Burek' in card.get_data(as_text=True)
    assert added.status_code == 302
    assert 'Kontrola ogólna' in owner_view and '12.5' in owner_view and 'Anna Nowak' in owner_view


def test_revoking_access_code_blocks_vet(flask_app, login_as, make_pet):
    owner = login_as('jan@example.com')
    vet = login_as('anna@example.com', role='vet')
    pet_id = make_pet(owner.user_id)
    owner.post(f'/generate_code/{pet_id}', data={'expires_in': '1'})
    with flask_app.app_context():
        access = AccessCode.query.filter_by(pet_id=pet_id).one()
        code, code_id = access.code, access.id
    assert vet.get(f'/vet/pet/{code}').status_code == 200

    owner.post(f'/revoke_code/{code_id}')

    assert vet.get(f'/vet/pet/{code}').status_code == 403
    with flask_app.app_context():
        assert AccessCode.query.count() == 0