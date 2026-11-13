"""Wspólna konfiguracja testów.

Testy działają na bazie SQLite w pamięci i na tymczasowych folderach na pliki,
więc nie dotykają prawdziwej bazy ani katalogów aplikacji. Każdy test dostaje
czystą bazę i sam tworzy wszystkie potrzebne dane.
"""
import os
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

# Ustawienia muszą być gotowe PRZED zaimportowaniem aplikacji (baza tworzy się przy imporcie).
os.environ['DATABASE_URI'] = 'sqlite:///:memory:'
os.environ['SECRET_KEY'] = 'klucz-tylko-do-testow'

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import main  # noqa: E402


@pytest.fixture()
def flask_app(tmp_path):
    """Aplikacja z czystą bazą w pamięci i tymczasowymi folderami na pliki."""
    uploads = tmp_path / 'uploads'
    avatars = tmp_path / 'avatars'
    uploads.mkdir()
    avatars.mkdir()

    main.app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        UPLOAD_FOLDER=str(uploads),
        AVATAR_FOLDER=str(avatars),
    )
    main.limiter.enabled = False  # limity logowania nie mogą psuć testów

    with main.app.app_context():
        main.db.drop_all()
        main.db.create_all()

    yield main.app

    with main.app.app_context():
        main.db.session.remove()
        main.db.drop_all()
    main.limiter.enabled = True
    main.app.config['WTF_CSRF_ENABLED'] = False


@pytest.fixture()
def make_user(flask_app):
    """Tworzy użytkownika bezpośrednio w bazie i zwraca jego id."""
    def _make(email='jan@example.com', role='owner', password='Panda12345',
              first_name='Jan', last_name='Kowalski', pwz=None):
        with flask_app.app_context():
            user = main.User(
                email=email,
                # szybki hash, żeby testy były szybkie (logowanie działa z każdym hashem Werkzeug)
                password_hash=generate_password_hash(password, method='pbkdf2:sha256:1000'),
                role=role,
                first_name=first_name,
                last_name=last_name,
                pwz_number=pwz,
            )
            main.db.session.add(user)
            main.db.session.commit()
            return user.id
    return _make


@pytest.fixture()
def login_as(flask_app, make_user):
    """Tworzy użytkownika, loguje go i zwraca klienta (z atrybutem user_id)."""
    def _login_as(email, role='owner', password='Panda12345', **kwargs):
        pwz = '1234567' if role == 'vet' else None
        user_id = make_user(email=email, role=role, password=password, pwz=pwz, **kwargs)
        client = flask_app.test_client()
        response = client.post('/login', data={'email': email, 'password': password})
        assert response.status_code == 302, 'logowanie testowego użytkownika nie powiodło się'
        client.user_id = user_id
        return client
    return _login_as


@pytest.fixture()
def make_pet(flask_app):
    """Tworzy zwierzaka dla wskazanego właściciela i zwraca jego id."""
    def _make(owner_id, name='Burek', species='Pies'):
        with flask_app.app_context():
            pet = main.Pet(name=name, species=species, owner_id=owner_id)
            main.db.session.add(pet)
            main.db.session.commit()
            return pet.id
    return _make


@pytest.fixture()
def make_code(flask_app):
    """Tworzy kod dostępu (domyślnie ważny 24 h; ujemna liczba godzin = wygasły)."""
    def _make(pet_id, hours=24, code='abcdef0123456789'):
        with flask_app.app_context():
            access = main.AccessCode(
                code=code, pet_id=pet_id,
                expires_at=main.utcnow() + timedelta(hours=hours))
            main.db.session.add(access)
            main.db.session.commit()
            return access.code
    return _make
