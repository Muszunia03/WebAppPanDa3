import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from flask import (Flask, render_template, request, session, jsonify,
                   redirect, url_for, flash, send_from_directory)
from flask_sqlalchemy import SQLAlchemy
from flask_login import (LoginManager, UserMixin, login_user, login_required,
                         logout_user, current_user)
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

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

app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024
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


def save_upload(file_storage, folder):
    original = secure_filename(file_storage.filename) or 'plik'
    stored = f"{uuid.uuid4()}_{original}"
    file_storage.save(os.path.join(folder, stored))
    return stored, original

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PWZ_RE = re.compile(r"^\d{5,10}$")


def validate_registration(email, password, first_name, last_name, role, pwz_number):
    if role not in ('owner', 'vet'):
        return 'Nieprawidłowa rola.'
    if not first_name or not last_name:
        return 'Imię i nazwisko są wymagane.'
    if len(first_name) > 50 or len(last_name) > 50:
        return 'Imię i nazwisko mogą mieć maksymalnie 50 znaków.'
    if len(email) > 120 or not EMAIL_RE.match(email):
        return 'Nieprawidłowy format adresu e-mail.'
    if len(password) < 8 or len(password) > 128:
        return 'Hasło musi mieć od 8 do 128 znaków.'
    if not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
        return 'Hasło musi zawierać co najmniej jedną literę i jedną cyfrę.'
    if role == 'vet' and not PWZ_RE.match(pwz_number):
        return 'Weterynarz musi podać poprawny numer PWZ (5-10 cyfr).'
    return None


def read_pet_form():
    name = (request.form.get('name') or '').strip()
    species = (request.form.get('species') or '').strip()
    if species == 'Inne':
        species = (request.form.get('species_other') or '').strip()
    if not name or len(name) > 100:
        return None, None, 'Imię zwierzaka jest wymagane (max 100 znaków).'
    if not species or len(species) > 50:
        return None, None, 'Gatunek jest wymagany (max 50 znaków).'
    return name, species, None


def get_valid_access_code(code):
    if not code:
        return None
    access = AccessCode.query.filter_by(code=code).first()
    if not access or access.expires_at < utcnow():
        return None
    return access

def render_dashboard(status=200):
    if current_user.role == 'owner':
        pets = Pet.query.filter_by(owner_id=current_user.id).all()
        return render_template('dashboard.html', pets=pets), status
    return render_template('dashboard.html'), status


def render_pet_page(pet, status=200):
    documents = Document.query.filter_by(pet_id=pet.id).all()
    codes = AccessCode.query.filter_by(pet_id=pet.id).all()
    records = MedicalRecord.query.filter_by(pet_id=pet.id).order_by(MedicalRecord.date.desc()).all()
    return render_template('pet_detail.html', pet=pet, documents=documents,
                           codes=codes, records=records, now=utcnow()), status


def render_vet_pet_page(pet, code, status=200):
    documents = Document.query.filter_by(pet_id=pet.id).all()
    records = MedicalRecord.query.filter_by(pet_id=pet.id).order_by(MedicalRecord.date.desc()).all()
    return render_template('vet_pet_detail.html', pet=pet, documents=documents,
                           records=records, current_code=code), status

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/health')
@limiter.exempt
def health():
    return jsonify({"status": "ok"}), 200

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        role = (request.form.get('role') or '').strip()
        pwz_number = (request.form.get('pwz_number') or '').strip()
        first_name = (request.form.get('first_name') or '').strip()
        last_name = (request.form.get('last_name') or '').strip()

        error = validate_registration(email, password, first_name, last_name, role, pwz_number)
        if error:
            flash(error)
            return render_template('register.html'), 400

        if User.query.filter_by(email=email).first():
            flash('Taki email jest już w bazie.')
            return render_template('register.html'), 409

        new_user = User(
            email=email,
            password_hash=generate_password_hash(password, method='scrypt'),
            role=role,
            pwz_number=pwz_number if role == 'vet' else None,
            first_name=first_name,
            last_name=last_name
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Konto utworzone! Możesz się zalogować.')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute", exempt_when=lambda: request.method == 'GET')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''

        if not email or not password:
            flash('Podaj email i hasło.')
            return render_template('login.html'), 400

        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))

        flash('Błędny email lub hasło.')
        return render_template('login.html'), 401

    return render_template('login.html')


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_dashboard()


@app.route('/add_pet', methods=['POST'])
@login_required
def add_pet():
    if current_user.role != 'owner':
        return "Brak uprawnień", 403

    name, species, error = read_pet_form()
    if error:
        flash(error)
        return render_dashboard(400)

    filename = None
    image_file = request.files.get('pet_image')
    if image_file and image_file.filename != '':
        error = validate_upload(image_file, IMAGE_EXTENSIONS)
        if error:
            flash(error)
            return render_dashboard(400)
        filename, _ = save_upload(image_file, app.config['AVATAR_FOLDER'])

    new_pet = Pet(name=name, species=species, owner_id=current_user.id, image_filename=filename)
    db.session.add(new_pet)
    db.session.commit()

    flash('Zwierzak został dodany!')
    return redirect(url_for('dashboard'))


@app.route('/pet/<int:pet_id>', methods=['GET', 'POST'])
@login_required
def view_pet(pet_id):
    pet = db.session.get(Pet, pet_id)

    if not pet or pet.owner_id != current_user.id:
        return "Brak dostępu! To nie jest twój zwierzak.", 403

    if request.method == 'POST':
        file = request.files.get('document')
        if file is None:
            flash('Brak pliku w formularzu.')
            return render_pet_page(pet, 400)
        if file.filename == '':
            flash('Nie wybrano żadnego pliku.')
            return render_pet_page(pet, 400)

        error = validate_upload(file)
        if error:
            flash(error)
            return render_pet_page(pet, 400)

        stored, original = save_upload(file, app.config['UPLOAD_FOLDER'])
        db.session.add(Document(filename=stored, original_filename=original, pet_id=pet.id))
        db.session.commit()

        flash('Dokument został bezpiecznie wgrany!')
        return redirect(url_for('view_pet', pet_id=pet.id))

    return render_pet_page(pet)


@app.route('/edit_pet/<int:pet_id>', methods=['POST'])
@login_required
def edit_pet(pet_id):
    pet = db.session.get(Pet, pet_id)
    if not pet or pet.owner_id != current_user.id:
        return "Brak dostępu!", 403

    name, species, error = read_pet_form()
    if error:
        flash(error)
        return render_pet_page(pet, 400)

    pet.name = name
    pet.species = species
    db.session.commit()

    flash('Dane pacjenta zostały zaktualizowane.')
    return redirect(url_for('view_pet', pet_id=pet.id))


@app.route('/delete_pet/<int:pet_id>', methods=['POST'])
@login_required
def delete_pet(pet_id):
    pet = db.get_or_404(Pet, pet_id)

    if pet.owner_id != current_user.id:
        return "Brak dostępu! To nie jest twój zwierzak.", 403

    remove_file(app.config['AVATAR_FOLDER'], pet.image_filename)
    for doc in pet.documents:
        remove_file(app.config['UPLOAD_FOLDER'], doc.filename)

    db.session.delete(pet)
    db.session.commit()
    flash('Zwierzak i wszystkie powiązane z nim pliki zostały usunięte!')
    return redirect(url_for('dashboard'))

@app.route('/download/<int:doc_id>')
@login_required
def download_doc(doc_id):
    doc = db.session.get(Document, doc_id)
    if not doc:
        return "Nie znaleziono pliku.", 404

    pet = db.session.get(Pet, doc.pet_id)
    if not pet or pet.owner_id != current_user.id:
        return "Brak autoryzacji do pobrania tego pliku.", 403

    return send_from_directory(app.config['UPLOAD_FOLDER'], doc.filename, as_attachment=True,
                               download_name=doc.original_filename)


@app.route('/delete_document/<int:doc_id>', methods=['POST'])
@login_required
def delete_document(doc_id):
    doc = db.session.get(Document, doc_id)
    if not doc:
        return "Dokument nie istnieje.", 404

    pet = db.session.get(Pet, doc.pet_id)
    if not pet or pet.owner_id != current_user.id:
        return "Brak autoryzacji do usunięcia tego pliku.", 403

    remove_file(app.config['UPLOAD_FOLDER'], doc.filename)
    db.session.delete(doc)
    db.session.commit()
    flash('Dokument medyczny został usunięty.')
    return redirect(url_for('view_pet', pet_id=pet.id))

@app.route('/generate_code/<int:pet_id>', methods=['POST'])
@login_required
def generate_code(pet_id):
    pet = db.session.get(Pet, pet_id)
    if not pet or pet.owner_id != current_user.id:
        return "Brak dostępu!", 403

    try:
        hours = int(request.form.get('expires_in', 24))
        if hours not in (1, 24, 168):
            hours = 24
    except ValueError:
        hours = 24

    random_code = secrets.token_hex(8)
    new_code = AccessCode(code=random_code, pet_id=pet.id,
                          expires_at=utcnow() + timedelta(hours=hours))
    db.session.add(new_code)
    db.session.commit()

    flash(f'Wygenerowano nowy kod ważny przez {hours}h: {random_code}')
    return redirect(url_for('view_pet', pet_id=pet.id))


@app.route('/revoke_code/<int:code_id>', methods=['POST'])
@login_required
def revoke_code(code_id):
    code_obj = db.session.get(AccessCode, code_id)
    if not code_obj:
        return "Kod nie istnieje.", 404

    pet = db.session.get(Pet, code_obj.pet_id)
    if not pet or pet.owner_id != current_user.id:
        return "Brak autoryzacji!", 403

    db.session.delete(code_obj)
    db.session.commit()
    flash('Kod został pomyślnie odwołany.')
    return redirect(url_for('view_pet', pet_id=pet.id))

@app.route('/vet/access', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def vet_access():
    if current_user.role != 'vet':
        return "Brak uprawnień. Tylko weterynarz może używać kodów dostępu.", 403

    code_input = (request.form.get('code') or '').strip()
    if not code_input:
        flash('Podaj kod dostępu.')
        return render_dashboard(400)

    if not get_valid_access_code(code_input):
        flash('Podany kod jest nieprawidłowy lub już wygasł.')
        return render_dashboard(403)

    return redirect(url_for('vet_view_pet', code=code_input))


@app.route('/vet/pet/<code>')
@login_required
def vet_view_pet(code):
    if current_user.role != 'vet':
        return "Brak uprawnień.", 403

    access = get_valid_access_code(code)
    if not access:
        flash('Sesja dostępu wygasła.')
        return render_dashboard(403)

    pet = db.session.get(Pet, access.pet_id)
    return render_vet_pet_page(pet, code)


@app.route('/vet/download/<code>/<int:doc_id>')
@login_required
def vet_download_doc(code, doc_id):
    if current_user.role != 'vet':
        return "Brak uprawnień.", 403

    access = get_valid_access_code(code)
    if not access:
        return "Brak dostępu. Kod wygasł lub jest nieprawidłowy.", 403

    doc = db.session.get(Document, doc_id)
    if not doc or doc.pet_id != access.pet_id:
        return "Nie znaleziono pliku w tej kartotece.", 404

    return send_from_directory(app.config['UPLOAD_FOLDER'], doc.filename, as_attachment=True,
                               download_name=doc.original_filename)


@app.route('/vet/add_record/<code>', methods=['POST'])
@login_required
def vet_add_record(code):
    if current_user.role != 'vet':
        return "Brak uprawnień.", 403

    access = get_valid_access_code(code)
    if not access:
        return "Brak autoryzacji lub kod wygasł.", 403

    pet = db.session.get(Pet, access.pet_id)
    diagnosis = (request.form.get('diagnosis') or '').strip()
    weight_raw = (request.form.get('weight') or '').strip().replace(',', '.')
    temp_raw = (request.form.get('temperature') or '').strip().replace(',', '.')

    if not diagnosis or len(diagnosis) > 5000:
        flash('Diagnoza jest wymagana (max 5000 znaków).')
        return render_vet_pet_page(pet, code, 400)

    try:
        weight = float(weight_raw) if weight_raw else None
        temperature = float(temp_raw) if temp_raw else None
    except ValueError:
        flash('Waga i temperatura muszą być liczbami.')
        return render_vet_pet_page(pet, code, 400)

    if (weight is not None and not 0 < weight < 1000) or \
       (temperature is not None and not 30 <= temperature <= 45):
        flash('Waga lub temperatura poza dopuszczalnym zakresem.')
        return render_vet_pet_page(pet, code, 400)

    db.session.add(MedicalRecord(diagnosis=diagnosis, weight=weight, temperature=temperature,
                                 pet_id=access.pet_id, vet_id=current_user.id))
    db.session.commit()

    flash('Pomyślnie dodano nowy wpis medyczny do kartoteki.')
    return redirect(url_for('vet_view_pet', code=code))

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