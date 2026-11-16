"""Scenariusze bezpieczeństwa."""
import io
import os

from app.main import db, Pet, Document, AccessCode


def test_user_cannot_access_or_modify_pet_of_another_owner(flask_app, login_as, make_pet):
    owner = login_as('jan@example.com')
    attacker = login_as('ewa@example.com', first_name='Ewa', last_name='Zielinska')
    pet_id = make_pet(owner.user_id, name='Burek')
    with flask_app.app_context():
        doc = Document(filename='abc_plik.pdf', original_filename='plik.pdf', pet_id=pet_id)
        db.session.add(doc)
        db.session.commit()
        doc_id = doc.id

    responses = {
        'podgląd zwierzaka': attacker.get(f'/pet/{pet_id}'),
        'edycja zwierzaka': attacker.post(f'/edit_pet/{pet_id}', data={'name': 'HACK', 'species': 'Pies'}),
        'usunięcie zwierzaka': attacker.post(f'/delete_pet/{pet_id}'),
        'pobranie dokumentu': attacker.get(f'/download/{doc_id}'),
        'usunięcie dokumentu': attacker.post(f'/delete_document/{doc_id}'),
        'generowanie kodu': attacker.post(f'/generate_code/{pet_id}', data={'expires_in': '24'}),
    }

    for action, response in responses.items():
        assert response.status_code == 403, f'{action} powinno zwrócić 403'
    with flask_app.app_context():
        assert db.session.get(Pet, pet_id).name == 'Burek'       # dane bez zmian
        assert db.session.get(Document, doc_id) is not None       # dokument nadal istnieje
        assert AccessCode.query.count() == 0                      # nie powstał żaden kod


def test_malicious_uploads_are_rejected_and_not_saved(flask_app, login_as, make_pet):
    client = login_as('jan@example.com')
    pet_id = make_pet(client.user_id)
    upload_dir = flask_app.config['UPLOAD_FOLDER']

    def send(filename, content):
        return client.post(f'/pet/{pet_id}', data={'document': (io.BytesIO(content), filename)},
                           content_type='multipart/form-data')

    assert send('wirus.exe', b'MZ\x90\x00').status_code == 400                  # zabronione rozszerzenie
    assert send('skrypt.php', b'<?php echo 1; ?>').status_code == 400           # zabronione rozszerzenie
    assert send('falsz.pdf', b'<?php system($_GET["c"]); ?>').status_code == 400  # zła sygnatura
    assert send('duzy.pdf', b'%PDF' + b'a' * (6 * 1024 * 1024)).status_code == 413  # ponad 5 MB
    assert os.listdir(upload_dir) == []                                         # nic nie zapisano

    traversal = send('../../poza_folderem.pdf', b'%PDF-1.4 ok')                 # ucieczka ścieżką w nazwie
    saved = os.listdir(upload_dir)
    assert traversal.status_code == 302
    assert len(saved) == 1 and '..' not in saved[0] and '/' not in saved[0]
    assert not os.path.exists(os.path.join(upload_dir, '..', 'poza_folderem.pdf'))


def test_post_without_csrf_token_is_rejected(flask_app, login_as):
    client = login_as('jan@example.com')
    flask_app.config['WTF_CSRF_ENABLED'] = True   # w pozostałych testach CSRF jest wyłączony

    response = client.post('/add_pet', data={'name': 'Burek', 'species': 'Pies'})

    assert response.status_code == 400
    with flask_app.app_context():
        assert Pet.query.count() == 0
