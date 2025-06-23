from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from werkzeug.security import generate_password_hash
from gama.models.usuario import Usuario
from datetime import datetime

usuario_bp = Blueprint('usuarios', __name__, template_folder='../templates')

@usuario_bp.route('/painel_usuario')
def painel_usuario():
    return render_template('painel_usuario.html', nome=session.get('nome'))

@usuario_bp.route('/config_usuarios', methods=['GET', 'POST'])
def config_usuarios():
    if 'usuario_id' not in session or session.get('tipo') != 'administrador':
        flash('Acesso negado.', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        id_usuario = request.form['id_usuario']
        cpf_usuario = request.form['cpf_usuario']
        nome = request.form['nome']
        email = request.form['email']
        senha = request.form['senha']
        confirmar_senha = request.form.get('confirmar_senha', '')

        if senha != confirmar_senha:
            flash('Senhas não coincidem.', 'error')
            return redirect(url_for('usuarios.config_usuarios'))

        hashed_password = generate_password_hash(senha)
        success, message = Usuario.create(id_usuario, cpf_usuario, nome, email, hashed_password)
        flash(message, 'success' if success else 'error')

        return redirect(url_for('usuarios.config_usuarios'))
    
    usuarios_originais = Usuario.get_all()

    usuarios_processados = []

    for usuario_tupla in usuarios_originais:
        usuario_lista = list(usuario_tupla)  

        data_ingresso = usuario_lista[6]

        if isinstance(data_ingresso, str):
            try:
                usuario_lista[6] = datetime.strptime(data_ingresso.split('.')[0], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                print(f"AVISO: Não foi possível converter a data '{data_ingresso}' para o usuario {usuario_lista[0]}.")
                usuario_lista[6] = data_ingresso 
        
        usuarios_processados.append(tuple(usuario_lista))

    return render_template('config_usuarios.html', usuarios=usuarios_processados, nome=session.get('nome'))


@usuario_bp.route('/remover_usuario/<id_usuario>', methods=['POST'])
def remover_usuario(id_usuario):
    if 'usuario_id' not in session or session.get('tipo') != 'administrador':
        flash('Acesso negado.', 'error')
        return redirect(url_for('auth.login'))

    success, message = Usuario.delete(id_usuario)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('usuarios.config_usuarios'))


@usuario_bp.route('/editar_usuario', methods=['POST'])
def editar_usuario():
    if 'usuario_id' not in session or session.get('tipo') != 'administrador':
        flash('Acesso negado.', 'error')
        return redirect(url_for('auth.login'))

    id_usuario = request.form['id_usuario']
    nome = request.form['nome']
    email = request.form['email']
    cpf_usuario = request.form['cpf_usuario']
    senha = request.form.get('senha', '')

    if senha:
        hashed_password = generate_password_hash(senha)
        success, message = Usuario.update(id_usuario, nome, email, cpf_usuario, hashed_password)
    else:
        success, message = Usuario.update(id_usuario, nome, email, cpf_usuario)

    flash(message, 'success' if success else 'error')
    return redirect(url_for('usuarios.config_usuarios'))