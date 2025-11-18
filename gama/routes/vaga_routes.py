# gama/routes/vaga_routes.py
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify
from gama.models.vaga import CargoGestao, Vaga
from gama.models.candidato import Candidato # Para buscar candidatos do sistema
import os
import tempfile

vaga_bp = Blueprint('vaga', __name__, template_folder='../templates')

def check_admin():
    return 'usuario_id' in session and session.get('tipo') == 'administrador' or "usuario"

@vaga_bp.route('/painel') # Removido o '_vagas' para ser o painel principal
def painel_vagas():
    if not check_admin():
        flash('Acesso negado.', 'error')
        return redirect(url_for('auth.login'))

    try:
        cargos = CargoGestao.get_all_with_counts()
        vagas_por_cargo = {}
        for cargo in cargos:
            vagas = Vaga.get_by_cargo_id(cargo['id'])
            vagas_por_cargo[cargo['id']] = vagas
        
        candidatos_sistema = Candidato.get_all_with_details()

        return render_template(
            'vagas.html', 
            nome=session.get('nome'),
            cargos=cargos,
            vagas_por_cargo=vagas_por_cargo,
            candidatos_sistema=candidatos_sistema
        )
    except Exception as e:
        flash(f'Erro ao carregar o painel de vagas: {e}', 'error')
        return render_template(
            'vagas.html', 
            nome=session.get('nome'),
            cargos=[],
            vagas_por_cargo={},
            candidatos_sistema=[]
        )
    
@vaga_bp.route('/upload_lote', methods=['POST'])
def upload_lote_vagas():
    if not check_admin():
        return redirect(url_for('auth.login'))
    
    if 'planilha' not in request.files:
        flash('Nenhum arquivo enviado.', 'error')
        return redirect(url_for('vaga.painel_vagas'))

    arquivo = request.files['planilha']

    if arquivo.filename == '':
        flash('Nenhum arquivo selecionado.', 'error')
        return redirect(url_for('vaga.painel_vagas'))

    if not arquivo.filename.lower().endswith('.xlsx'):
        flash('Formato de arquivo inválido. Por favor, envie um arquivo .xlsx', 'error')
        return redirect(url_for('vaga.painel_vagas'))

    fd, temp_path = tempfile.mkstemp(suffix='.xlsx')
    try:
        arquivo.save(temp_path)
        
        cargos_criados, vagas_processadas, erros = Vaga.processar_lote(temp_path)
        
        if cargos_criados > 0 or vagas_processadas > 0:
            flash(f'Importação concluída! {cargos_criados} novos cargos criados. {vagas_processadas} vagas criadas/atualizadas.', 'success')
        
        if erros:
            flash(f"Erros durante a importação: {'; '.join(erros[:5])}", 'error')
        
    except Exception as e:
        flash(f'Ocorreu um erro fatal ao processar o arquivo: {e}', 'error')
    finally:
        os.close(fd)
        os.remove(temp_path)

    return redirect(url_for('vaga.painel_vagas'))

@vaga_bp.route('/cargo/adicionar', methods=['POST'])
def adicionar_cargo():
    if not check_admin(): return redirect(url_for('auth.login'))
    
    cod_cargo = request.form['cod_cargo']
    nome_cargo = request.form['nome_cargo']
    situacao = request.form['situacao']
    nivel = request.form['nivel']
    
    if not CargoGestao.create(cod_cargo, nome_cargo, situacao, nivel):
        flash('Erro ao criar cargo. O Código do Cargo já pode existir.', 'error')
    else:
        flash('Cargo criado com sucesso!', 'success')
    
    return redirect(url_for('vaga.painel_vagas'))

@vaga_bp.route('/cargo/editar/<int:id_cargo>', methods=['POST'])
def editar_cargo(id_cargo):
    if not check_admin(): return redirect(url_for('auth.login'))

    cod_cargo = request.form['cod_cargo']
    nome_cargo = request.form['nome_cargo']
    situacao = request.form['situacao']
    nivel = request.form['nivel']
    
    if not CargoGestao.update(id_cargo, cod_cargo, nome_cargo, situacao, nivel):
        flash('Erro ao atualizar cargo. O Código do Cargo já pode existir.', 'error')
    else:
        flash('Cargo atualizado com sucesso!', 'success')
        
    return redirect(url_for('vaga.painel_vagas'))

@vaga_bp.route('/cargo/remover/<int:id_cargo>', methods=['POST'])
def remover_cargo(id_cargo):
    if not check_admin(): return redirect(url_for('auth.login'))
    
    if CargoGestao.delete(id_cargo):
        flash('Cargo e todas as suas vagas removidos com sucesso.', 'success')
    else:
        flash('Erro ao remover cargo.', 'error')
        
    return redirect(url_for('vaga.painel_vagas'))

@vaga_bp.route('/vaga/adicionar', methods=['POST'])
def adicionar_vaga():
    if not check_admin(): return redirect(url_for('auth.login'))
    
    cargo_id = request.form['cargo_gestao_id']
    cod_vaga = request.form['cod_vaga']
    area = request.form.get('area')
    observacoes = request.form.get('observacoes')
    
    candidato_id = request.form.get('ocupante_candidato_id')
    ocupante_manual = request.form.get('ocupante_manual')
    
    ocupante_final = None
    situacao_vaga = 'Livre'
    
    if candidato_id: 
        candidato = Candidato.get_by_id(candidato_id)
        if candidato:
            ocupante_final = candidato['nome']
            situacao_vaga = 'Ocupada'
    elif ocupante_manual: 
        ocupante_final = ocupante_manual
        situacao_vaga = 'Ocupada'

    if Vaga.create(cargo_id, cod_vaga, situacao_vaga, ocupante_final, area, observacoes):
        flash('Vaga criada com sucesso!', 'success')
    else:
        flash('Erro ao criar vaga. O Código da Vaga já pode existir.', 'error')

    return redirect(url_for('vaga.painel_vagas'))

@vaga_bp.route('/vaga/editar/<int:id_vaga>', methods=['POST'])
def editar_vaga(id_vaga):
    if not check_admin(): return redirect(url_for('auth.login'))
    
    cod_vaga = request.form['cod_vaga']
    area = request.form.get('area')
    observacoes = request.form.get('observacoes')
    
    candidato_id = request.form.get('ocupante_candidato_id')
    ocupante_manual = request.form.get('ocupante_manual')
    
    ocupante_final = None
    situacao_vaga = 'Livre'
    
    if candidato_id: 
        candidato = Candidato.get_by_id(candidato_id)
        if candidato:
            ocupante_final = candidato['nome']
            situacao_vaga = 'Ocupada'
    elif ocupante_manual: 
        ocupante_final = ocupante_manual
        situacao_vaga = 'Ocupada'

    if Vaga.update(id_vaga, cod_vaga, situacao_vaga, ocupante_final, area, observacoes):
        flash('Vaga atualizada com sucesso!', 'success')
    else:
        flash('Erro ao atualizar vaga. O Código da Vaga já pode existir.', 'error')

    return redirect(url_for('vaga.painel_vagas'))

@vaga_bp.route('/vaga/remover/<int:id_vaga>', methods=['POST'])
def remover_vaga(id_vaga):
    if not check_admin(): return redirect(url_for('auth.login'))
    
    if Vaga.delete(id_vaga):
        flash('Vaga removida com sucesso.', 'success')
    else:
        flash('Erro ao remover vaga.', 'error')
        
    return redirect(url_for('vaga.painel_vagas'))