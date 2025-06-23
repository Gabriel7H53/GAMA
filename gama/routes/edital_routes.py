# gama/routes/edital_routes.py
from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from gama.models.edital import Edital, Cargo, Candidato
from datetime import datetime

edital_bp = Blueprint('edital', __name__, template_folder='../templates')

def check_admin():
    return 'usuario_id' in session and session.get('tipo') == 'administrador'

# ROTA CORRIGIDA
@edital_bp.route('/painel')
def painel(): # NOME DA FUNÇÃO ATUALIZADO
    if not check_admin():
        flash('Acesso negado. Apenas administradores podem gerenciar editais.', 'error')
        return redirect(url_for('auth.login'))

    editais = Edital.get_all()
    candidatos_por_edital = {}
    for edital in editais:
        candidatos_por_edital[edital[0]] = Candidato.get_by_edital(edital[0])

    return render_template(
        'edital.html', 
        nome=session.get('nome'), 
        editais=editais,
        candidatos_por_edital=candidatos_por_edital
    )

# ROTA CORRIGIDA
@edital_bp.route('/adicionar', methods=['POST'])
def adicionar_edital():
    if not check_admin():
        return redirect(url_for('auth.login'))
    
    # ... (código interno da função permanece o mesmo) ...
    numero_edital = request.form['numero_edital']
    data_edital = request.form['data_edital']
    data_publicacao = request.form['data_publicacao']
    vencimento_edital = request.form['vencimento_edital']
    prazo_prorrogacao = request.form.get('prazo_prorrogacao') or 0
    status = request.form['status']
    success, message = Edital.create(numero_edital, data_edital, data_publicacao, vencimento_edital, prazo_prorrogacao, status)

    flash(message, 'success' if success else 'error')
    return redirect(url_for('edital.painel')) # REDIRECIONAMENTO CORRIGIDO

# ROTA CORRIGIDA
@edital_bp.route('/editar/<int:id_edital>', methods=['POST'])
def editar_edital(id_edital):
    if not check_admin():
        return redirect(url_for('auth.login'))
        
    # ... (código interno da função permanece o mesmo) ...
    numero_edital = request.form['numero_edital']
    data_edital = request.form['data_edital']
    data_publicacao = request.form['data_publicacao']
    vencimento_edital = request.form['vencimento_edital']
    prazo_prorrogacao = request.form.get('prazo_prorrogacao') or 0
    status = request.form['status']
    success, message = Edital.update(id_edital, numero_edital, data_edital, data_publicacao, vencimento_edital, prazo_prorrogacao, status)
    
    flash(message, 'success' if success else 'error')
    return redirect(url_for('edital.painel')) # REDIRECIONAMENTO CORRIGIDO

# ROTA CORRIGIDA
@edital_bp.route('/remover/<int:id_edital>', methods=['POST'])
def remover_edital(id_edital):
    if not check_admin():
        return redirect(url_for('auth.login'))
        
    success, message = Edital.delete(id_edital)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('edital.painel')) # REDIRECIONAMENTO CORRIGIDO

# ROTA CORRIGIDA
@edital_bp.route('/<int:id_edital>/candidato/adicionar', methods=['POST'])
def adicionar_candidato(id_edital):
    if not check_admin():
        return redirect(url_for('auth.login'))

    # ... (código interno da função permanece o mesmo) ...
    nome_cargo = request.form['nome_cargo'].strip()
    id_cargo = Cargo.get_or_create(id_edital, nome_cargo)
    nome = request.form['nome']
    inscricao = request.form['numero_inscricao']
    nota = request.form['nota']
    classificacao = request.form['classificacao']
    pcd = 'pcd' in request.form
    cotista = 'cotista' in request.form
    situacao = request.form['situacao']
    data_posse = request.form.get('data_posse')
    success, message = Candidato.create(id_edital, id_cargo, nome, inscricao, nota, classificacao, pcd, cotista, situacao, data_posse)

    flash(message, 'success' if success else 'error')
    return redirect(url_for('edital.painel')) # REDIRECIONAMENTO CORRIGIDO

# Rota OK, apenas o redirecionamento foi corrigido
@edital_bp.route('/candidato/editar/<int:id_candidato>', methods=['POST'])
def editar_candidato(id_candidato):
    if not check_admin():
        return redirect(url_for('auth.login'))
    
    # Lógica para atualizar o cargo
    id_edital = request.form['id_edital']
    nome_cargo = request.form['nome_cargo'].strip()
    id_cargo = Cargo.get_or_create(id_edital, nome_cargo)
    
    # Coleta dos outros dados do formulário
    nome = request.form['nome']
    inscricao = request.form['numero_inscricao']
    nota = request.form['nota']
    classificacao = request.form['classificacao']
    pcd = 'pcd' in request.form
    cotista = 'cotista' in request.form
    situacao = request.form['situacao']
    data_posse = request.form.get('data_posse')

    # Chamada da função de update com o novo id_cargo
    success, message = Candidato.update(id_candidato, id_cargo, nome, inscricao, nota, classificacao, pcd, cotista, situacao, data_posse)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('edital.painel'))


# Rota OK, apenas o redirecionamento foi corrigido
@edital_bp.route('/candidato/remover/<int:id_candidato>', methods=['POST'])
def remover_candidato(id_candidato):
    if not check_admin():
        return redirect(url_for('auth.login'))
        
    success, message = Candidato.delete(id_candidato)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('edital.painel')) # REDIRECIONAMENTO CORRIGIDO