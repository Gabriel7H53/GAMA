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
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    todos_editais = Edital.get_all()
    dados_pagina = {}

    for edital in todos_editais:
        id_edital = edital[0]
        dados_pagina[id_edital] = {
            'candidatos': [],
            'agend_docs': [],
            'agend_pericias': []
        }

        # 1. Buscar todos os agendamentos do edital
        agendamentos_edital = Agendamento.get_by_edital(id_edital)

        # 2. Criar listas e lookups de agendamentos
        docs_agendados = {}
        docs_entregues = {}
        pericia_agendada = {}
        pericia_concluida = {}

        for ag in agendamentos_edital:
            # Índices: [2]=nome, [5]=status, [6]=tipo
            nome_candidato = ag[2]
            if ag[6] == 'documento':
                if ag[5] == 'concluido':
                    docs_entregues[nome_candidato] = 'entregue'
                elif ag[5] == 'agendado':
                    docs_agendados[nome_candidato] = 'agendado'
                # Adiciona à lista de exibição (seção 2)
                dados_pagina[id_edital]['agend_docs'].append(ag)
            
            elif ag[6] == 'pericia':
                if ag[5] == 'concluido':
                    pericia_concluida[nome_candidato] = 'concluida'
                elif ag[5] == 'agendado':
                    pericia_agendada[nome_candidato] = 'agendado'
                # Adiciona à lista de exibição (seção 2)
                dados_pagina[id_edital]['agend_pericias'].append(ag)

        # 3. Buscar candidatos e processar status
        todos_candidatos_do_edital = Candidato.get_by_edital(id_edital)
        
        # Filtra apenas nomeados (índice 8 = situacao)
        candidatos_nomeados = [c for c in todos_candidatos_do_edital if c[8] == 'nomeado']
        
        lista_candidatos_final = []
        for c in candidatos_nomeados:
            # Índices: [0]=id, [1]=nome, [15]=contatado
            id_candidato = c[0]
            nome_candidato = c[1]
            contatado = c[15] 

            # Define o status do documento
            status_doc = docs_entregues.get(nome_candidato, docs_agendados.get(nome_candidato, 'agendar'))
            
            # Define o status da perícia
            status_pericia = pericia_concluida.get(nome_candidato, pericia_agendada.get(nome_candidato, 'agendar'))

            lista_candidatos_final.append({
                'id': id_candidato,
                'nome': nome_candidato,
                'contatado': contatado,
                'status_doc': status_doc,
                'status_pericia': status_pericia
            })
        
        dados_pagina[id_edital]['candidatos'] = lista_candidatos_final
        
        # 4. Ordenar listas de agendamento (concluídos por último)
        dados_pagina[id_edital]['agend_docs'].sort(key=lambda x: x[5] == 'concluido')
        dados_pagina[id_edital]['agend_pericias'].sort(key=lambda x: x[5] == 'concluido')


    return render_template(
        'agendamentos.html', 
        nome=session.get('nome'), 
        editais=todos_editais,
        dados_pagina=dados_pagina # Passa a nova estrutura de dados
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
        tipo_agendamento = request.form.get('tipo_agendamento', 'documento')
        
        id_documento_a_concluir = request.form.get('id_documento_a_concluir')

        data_hora_agendamento = datetime.strptime(f"{data} {hora}", '%Y-%m-%d %H:%M')
        id_usuario_logado = session['usuario_id']

        if tipo_agendamento == 'pericia' and id_documento_a_concluir:
            Agendamento.update_status(id_documento_a_concluir, 'concluido')

        success, message = Agendamento.create(
            id_edital, id_usuario_logado, data_hora_agendamento, nome_pessoa, tipo_agendamento
        )
        
        if tipo_agendamento == 'pericia' and success:
             flash("Perícia agendada e entrega de documento concluída com sucesso.", 'success')
        else:
            flash(message, 'success' if success else 'error')

    except Exception as e:
        flash(f"Ocorreu um erro ao processar sua solicitação: {e}", "error")

    return redirect(url_for('usuarios.agendamentos', open=id_edital))

@usuario_bp.route('/agendamento/concluir_pericia/<int:id_agendamento>', methods=['POST'])
def concluir_pericia(id_agendamento):
    if 'usuario_id' not in session:
        flash('Acesso negado.', 'error')
        return redirect(url_for('auth.login'))

    # ALTERAÇÃO: Busca o agendamento para saber o ID do Edital
    agendamento = Agendamento.get_by_id(id_agendamento)
    id_edital = agendamento['id_edital'] if agendamento else None

    try:
        success, message = Agendamento.update_status(id_agendamento, 'concluido')
        
        if success:
            flash("Perícia marcada como realizada com sucesso.", 'success')
        else:
            flash(message, 'error')
            
    except Exception as e:
        flash(f"Ocorreu um erro ao atualizar o status: {e}", "error")
    
    # Redireciona com open=...
    return redirect(url_for('usuarios.agendamentos', open=id_edital))


@usuario_bp.route('/agendamento/editar/<int:id_agendamento>', methods=['POST'])
def editar_agendamento(id_agendamento):
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    # ALTERAÇÃO: Busca o agendamento antes de editar
    agendamento = Agendamento.get_by_id(id_agendamento)
    id_edital = agendamento['id_edital'] if agendamento else None

    try:
        nome_pessoa = request.form['nome_pessoa']
        data = request.form['data_agendamento']
        hora = request.form['hora_agendamento']
        status = request.form['status_agendamento'] 
        data_hora = datetime.strptime(f"{data} {hora}", '%Y-%m-%d %H:%M')

        success, message = Agendamento.update(id_agendamento, data_hora, nome_pessoa, status)
        flash(message, 'success' if success else 'error')
    except Exception as e:
        flash(f"Ocorreu um erro ao editar: {e}", "error")
        
    return redirect(url_for('usuarios.agendamentos', open=id_edital))


@usuario_bp.route('/agendamento/remover/<int:id_agendamento>', methods=['POST'])
def remover_agendamento(id_agendamento):
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    # ALTERAÇÃO: Busca o agendamento ANTES de deletar
    agendamento = Agendamento.get_by_id(id_agendamento)
    id_edital = agendamento['id_edital'] if agendamento else None

    success, message = Agendamento.delete(id_agendamento)
    flash(message, 'success' if success else 'error')
    
    return redirect(url_for('usuarios.agendamentos', open=id_edital))

@usuario_bp.route('/candidato/toggle_contatado', methods=['POST'])
def toggle_contatado():
    if 'usuario_id' not in session:
        return jsonify({"success": False, "message": "Acesso negado."}), 401
    
    try:
        data = request.get_json()
        id_candidato = data.get('id_candidato')
        novo_status = data.get('status')

        if id_candidato is None:
            return jsonify({"success": False, "message": "ID do candidato não fornecido."}), 400

        success = Candidato.set_contatado(id_candidato, novo_status)
        
        if success:
            return jsonify({"success": True, "novo_status": novo_status})
        else:
            return jsonify({"success": False, "message": "Erro ao atualizar o banco de dados."}), 500

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500