from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from gama.database.database import verificar_login  # Certifique-se de que está no caminho correto.

auth_bp = Blueprint('auth', __name__, template_folder='../templates')

@auth_bp.route('/')
def index():
   return redirect(url_for('auth.login'))


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        remember = True if request.form.get('remember') else False
        print(f"\n--- DEBUG: Checkbox 'Lembrar de mim' foi marcado? {remember} ---")

        usuario = verificar_login(email, senha)

        if usuario:
            if remember:
                session.permanent = True
                print("--- DEBUG: A sessão foi definida como PERMANENTE. ---\n")
            else:
                session.permanent = False
                print("--- DEBUG: A sessão foi definida como PADRÃO (NÃO permanente). ---\n")

            session['usuario_id'] = usuario[0]
            session['nome'] = usuario[2]
            session['tipo'] = usuario[5]

            if usuario[5] == 'administrador':
                return redirect(url_for('admin.painel_admin'))
            else:
                return redirect(url_for('usuarios.painel_usuario'))
        else:
            flash('Email ou senha inválidos!', 'error')

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
   session.clear()
   return redirect(url_for('auth.login'))