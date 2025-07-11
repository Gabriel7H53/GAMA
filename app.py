from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from gama.database.database import verificar_login
from werkzeug.security import generate_password_hash
from datetime import timedelta 
from datetime import datetime as dt_parser

# Importando os Blueprints
from gama.routes.auth_routes import auth_bp
from gama.routes.admin_routes import admin_bp
from gama.routes.usuario_routes import usuario_bp
from gama.routes.edital_routes import edital_bp

app = Flask(__name__, static_folder='gama/static', template_folder='gama/templates')
app.secret_key = 'chave_secreta_super_segura'

def format_date_br(value):
    if isinstance(value, str):
        try:
            date_obj = dt_parser.strptime(value.split('.')[0], '%Y-%m-%d %H:%M:%S')
            return date_obj.strftime('%d/%m/%Y')
        except ValueError:
            return value.split(' ')[0] # Em caso de erro, mostra a data original
    return value

def format_time(value):
    if isinstance(value, str):
        try:
            date_obj = dt_parser.strptime(value.split('.')[0], '%Y-%m-%d %H:%M:%S')
            return date_obj.strftime('%H:%M')
        except ValueError:
            return value.split(' ')[1] # Em caso de erro, mostra a hora original
    return value

app.jinja_env.filters['dateformat_br'] = format_date_br
app.jinja_env.filters['timeformat'] = format_time
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.jinja_env.auto_reload = True

@app.before_request
def make_session_permanent():
    session.permanent = True

# Definindo rota principal
@app.route('/')
def home():
    return redirect(url_for('auth.login'))

# Registrando os blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(usuario_bp, url_prefix='/usuario')
app.register_blueprint(edital_bp, url_prefix='/edital')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')