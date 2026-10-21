from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-super-secret-panda-key')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///panda3.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'owner' lub 'vet'
    pwz_number = db.Column(db.String(50), nullable=True)
    pets = db.relationship('Pet', backref='owner', lazy=True)


class Pet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    species = db.Column(db.String(50), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)


with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- ROUTING (ENDPOINTY) ---
@app.route('/')
def index():
    return 'Witaj w PanDa3! <a href="/register">Zarejestruj się</a> lub <a href="/login">Zaloguj</a>.'


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        pwz_number = request.form.get('pwz_number')

        if User.query.filter_by(email=email).first():
            flash('Taki email jest już w bazie.')
            return redirect(url_for('register'))

        if role == 'vet' and not pwz_number:
            flash('Weterynarz musi podać numer PWZ!')
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password, method='scrypt')

        new_user = User(email=email, password_hash=hashed_pw, role=role, pwz_number=pwz_number)
        db.session.add(new_user)
        db.session.commit()

        flash('Konto utworzone! Możesz się zalogować.')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Błędny email lub hasło.')

    return render_template('login.html')


@app.route('/dashboard')
@login_required
def dashboard():
    if current_user.role == 'owner':
        user_pets = Pet.query.filter_by(owner_id=current_user.id).all()
        return render_template('dashboard.html', pets=user_pets)
    else:
        return render_template('dashboard.html')


@app.route('/add_pet', methods=['POST'])
@login_required
def add_pet():
    if current_user.role != 'owner':
        return "Brak uprawnień", 403

    name = request.form.get('name')
    species = request.form.get('species')

    new_pet = Pet(name=name, species=species, owner_id=current_user.id)
    db.session.add(new_pet)
    db.session.commit()

    flash('Zwierzak został dodany!')
    return redirect(url_for('dashboard'))


@app.route('/delete_pet/<int:pet_id>', methods=['POST'])
@login_required
def delete_pet(pet_id):
    pet = Pet.query.get_or_404(pet_id)

    if pet.owner_id != current_user.id:
        return "Brak dostępu! To nie jest twój zwierzak.", 403

    db.session.delete(pet)
    db.session.commit()
    flash('Zwierzak został usunięty!')
    return redirect(url_for('dashboard'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)