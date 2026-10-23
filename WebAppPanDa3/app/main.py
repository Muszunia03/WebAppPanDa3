import os
import secrets

from dotenv import load_dotenv
from flask import Flask, render_template

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
load_dotenv(os.path.join(PROJECT_DIR, '.env'))


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ('1', 'true', 'yes', 'on')


app = Flask(__name__)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    app.run(host=os.environ.get('HOST') or '127.0.0.1',
            port=int(os.environ.get('PORT') or 5000),
            debug=False)