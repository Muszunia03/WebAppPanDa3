import os
import secrets
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from flask import Flask, render_template, request, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, login_required,
                         logout_user, current_user)
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
load_dotenv(os.path.join(PROJECT_DIR, '.env'))


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URI') or 'sqlite:///panda3.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = env_bool('SESSION_COOKIE_SECURE', False)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
AVATAR_FOLDER = os.path.join(BASE_DIR, 'static', 'avatars')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['AVATAR_FOLDER'] = AVATAR_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(AVATAR_FOLDER, exist_ok=True)

app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # limit 5 MB
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}
FILE_SIGNATURES = {
    'pdf': (b'%PDF',),
    'png': (b'\x89PNG\r\n\x1a\n',),
    'jpg': (b'\xff\xd8\xff',),
    'jpeg': (b'\xff\xd8\xff',),
}

db = SQLAlchemy(app)
csrf = CSRFProtect(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["1000 per day", "300 per hour"],
    default_limits_exempt_when=lambda: request.endpoint == 'static',
    storage_uri="memory://"
)

login_manager = LoginManager(app)
login_manager.login_view = 'login'


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    pwz_number = db.Column(db.String(50), nullable=True)
    pets = db.relationship('Pet', backref='owner', lazy=True)


class Pet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    species = db.Column(db.String(50), nullable=False)
    image_filename = db.Column(db.String(255), nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    documents = db.relationship('Document', backref='pet', lazy=True, cascade="all, delete-orphan")
    medical_records = db.relationship('MedicalRecord', backref='pet', lazy=True, cascade="all, delete-orphan")
    access_codes = db.relationship('AccessCode', backref='pet', lazy=True, cascade="all, delete-orphan")


class MedicalRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    diagnosis = db.Column(db.Text, nullable=False)
    weight = db.Column(db.Float, nullable=True)
    temperature = db.Column(db.Float, nullable=True)
    date = db.Column(db.DateTime, default=utcnow)
    pet_id = db.Column(db.Integer, db.ForeignKey('pet.id'), nullable=False)
    vet_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    vet = db.relationship('User', backref='authored_records', lazy=True)


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    pet_id = db.Column(db.Integer, db.ForeignKey('pet.id'), nullable=False)


class AccessCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(16), unique=True, nullable=False)
    pet_id = db.Column(db.Integer, db.ForeignKey('pet.id'), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)


with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.before_request
def make_session_permanent():
    if request.endpoint not in ('static', 'health'):
        session.permanent = True


def get_extension(filename):
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''


def allowed_file(filename, allowed=ALLOWED_EXTENSIONS):
    return get_extension(filename) in allowed


def file_signature_ok(file_storage):
    ext = get_extension(file_storage.filename)
    header = file_storage.stream.read(8)
    file_storage.stream.seek(0)
    return any(header.startswith(sig) for sig in FILE_SIGNATURES.get(ext, ()))


def validate_upload(file_storage, allowed=ALLOWED_EXTENSIONS):
    if not allowed_file(file_storage.filename, allowed):
        return 'Niedozwolony format pliku. Dozwolone: ' + ', '.join(sorted(allowed)) + '.'
    if not file_signature_ok(file_storage):
        return 'Zawartość pliku nie zgadza się z jego rozszerzeniem.'
    return None


def remove_file(folder, filename):
    if not filename:
        return
    path = os.path.join(folder, filename)
    if os.path.exists(path):
        os.remove(path)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/health')
@limiter.exempt
def health():
    return jsonify({"status": "ok"}), 200


@app.errorhandler(CSRFError)
def csrf_error(e):
    return "Nieprawidłowy lub brakujący token.", 400


@app.errorhandler(400)
def bad_request(e):
    return "Nieprawidłowe żądanie.", 400


@app.errorhandler(403)
def forbidden(e):
    return "Brak dostępu.", 403


@app.errorhandler(404)
def not_found(e):
    return "Nie znaleziono strony.", 404


@app.errorhandler(413)
def too_large(e):
    return "Plik jest za duży (maksymalnie 5 MB).", 413


@app.errorhandler(429)
def ratelimit_error(e):
    return "Wykryto zbyt wiele prób!", 429


@app.errorhandler(500)
def server_error(e):
    db.session.rollback()
    return "Wewnętrzny błąd serwera.", 500


if __name__ == '__main__':
    app.run(host=os.environ.get('HOST') or '127.0.0.1',
            port=int(os.environ.get('PORT') or 5000),
            debug=env_bool('DEBUG', default=False))