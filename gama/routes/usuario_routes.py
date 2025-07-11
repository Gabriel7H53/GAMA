from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify
from werkzeug.security import generate_password_hash
from gama.models.usuario import Usuario
from gama.models.edital import Edital
from gama.models.agendamento import Agendamento
from gama.models.candidato import Candidato
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

@usuario_bp.route('/agendamentos')
def agendamentos():
    # Proteção: Garante que o usuário esteja logado
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    todos_editais = Edital.get_all()
    agendamentos_por_edital = {}

    for edital in todos_editais:
        id_edital = edital[0]
        agendamentos_por_edital[id_edital] = Agendamento.get_by_edital(id_edital)

    return render_template(
        'agendamentos.html', 
        nome=session.get('nome'), 
        editais=todos_editais,
        agendamentos_por_edital=agendamentos_por_edital
    )


@usuario_bp.route('/agendamento/criar', methods=['POST'])
def criar_agendamento():
    if 'usuario_id' not in session:
        flash('Acesso negado.', 'error')
        return redirect(url_for('auth.login'))

    try:
        id_edital = request.form['id_edital']
        nome_pessoa = request.form['nome_pessoa']
        data = request.form['data_agendamento']
        hora = request.form['hora_agendamento']
        
        # Combina data e hora em um único objeto datetime
        data_hora_agendamento = datetime.strptime(f"{data} {hora}", '%Y-%m-%d %H:%M')

        id_usuario_logado = session['usuario_id']

        success, message = Agendamento.create(id_edital, id_usuario_logado, data_hora_agendamento, nome_pessoa)
        flash(message, 'success' if success else 'error')

    except Exception as e:
        flash(f"Ocorreu um erro ao processar sua solicitação: {e}", "error")

    return redirect(url_for('usuarios.agendamentos'))

@usuario_bp.route('/api/candidatos/search')
def search_candidatos_api():
    if 'usuario_id' not in session:
        return jsonify({"error": "Acesso não autorizado"}), 401

    query = request.args.get('query', '')
    if len(query) < 2:
        return jsonify([])

    nomes = Candidato.search_by_name(query)
    return jsonify(nomes)

@usuario_bp.route('/agendamento/editar/<int:id_agendamento>', methods=['POST'])
def editar_agendamento(id_agendamento):
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    try:
        nome_pessoa = request.form['nome_pessoa']
        data = request.form['data_agendamento']
        hora = request.form['hora_agendamento']
        status = request.form['status_agendamento'] # <-- Pega o novo campo do formulário
        data_hora = datetime.strptime(f"{data} {hora}", '%Y-%m-%d %H:%M')

        # Passa o status para o método de update
        success, message = Agendamento.update(id_agendamento, data_hora, nome_pessoa, status)
        flash(message, 'success' if success else 'error')
    except Exception as e:
        flash(f"Ocorreu um erro ao editar: {e}", "error")
        
    return redirect(url_for('usuarios.agendamentos'))


@usuario_bp.route('/agendamento/remover/<int:id_agendamento>', methods=['POST'])
def remover_agendamento(id_agendamento):
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    success, message = Agendamento.delete(id_agendamento)
    flash(message, 'success' if success else 'error')
    
    return redirect(url_for('usuarios.agendamentos'))