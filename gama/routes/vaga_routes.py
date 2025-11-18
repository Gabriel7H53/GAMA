# gama/routes/vaga_routes.py
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify
from gama.models.vaga import CargoGestao, Vaga
from gama.models.candidato import Candidato # Para buscar candidatos do sistema
from gama.models.vaga import CargoGestao, Vaga, HistoricoVaga # Adicione HistoricoVaga
from gama.database.database import conectar
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
    
    # Captura o ID do novo cargo retornado pelo create
    novo_id = CargoGestao.create(cod_cargo, nome_cargo, situacao, nivel)
    
    if novo_id:
        flash('Cargo criado com sucesso!', 'success')
        # Abre o novo cargo criado
        return redirect(url_for('vaga.painel_vagas', open=novo_id))
    else:
        flash('Erro ao criar cargo. O Código do Cargo já pode existir.', 'error')
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
        
    # Reabre o cargo editado
    return redirect(url_for('vaga.painel_vagas', open=id_cargo))

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
    
    # Captura o ID do cargo para reabrir o painel
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
        # Sincronização (Vaga -> Candidato)
        if candidato_id:
            Candidato.vincular_vaga(candidato_id, cod_vaga)
            
        flash('Vaga criada com sucesso!', 'success')
    else:
        flash('Erro ao criar vaga. O Código da Vaga já pode existir.', 'error')

    # Reabre o cargo onde a vaga foi adicionada
    return redirect(url_for('vaga.painel_vagas', open=cargo_id))

@vaga_bp.route('/vaga/editar/<int:id_vaga>', methods=['POST'])
def editar_vaga(id_vaga):
    if not check_admin(): return redirect(url_for('auth.login'))
    
    # Captura o ID do cargo para reabrir o painel (vem do hidden input no form)
    cargo_id = request.form.get('cargo_gestao_id')

    # 1. Buscar dados ANTIGOS para comparação
    conn_temp = conectar() 
    cursor_temp = conn_temp.cursor()
    cursor_temp.execute("SELECT * FROM Vaga WHERE id = ?", (id_vaga,))
    row_antiga = cursor_temp.fetchone()
    conn_temp.close()
    
    cod_vaga_antigo = row_antiga[1] if row_antiga else "N/A"
    situacao_antiga = row_antiga[2] if row_antiga else "N/A"
    ocupante_antigo = row_antiga[3] if row_antiga else "N/A"
    area_antiga = row_antiga[4] if row_antiga else ""

    # 2. Coleta dados
    cod_vaga_novo = request.form['cod_vaga']
    area_nova = request.form.get('area')
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

    # 3. Atualiza
    if Vaga.update(id_vaga, cod_vaga_novo, situacao_vaga, ocupante_final, area_nova, observacoes):
        
        # Histórico
        usuario_logado = session.get('nome', 'Usuário')
        
        ocupante_antigo_safe = ocupante_antigo if ocupante_antigo else "Vago"
        ocupante_novo_safe = ocupante_final if ocupante_final else "Vago"
        if ocupante_antigo_safe != ocupante_novo_safe:
            msg = f"Alterou ocupante: '{ocupante_antigo_safe}' ➝ '{ocupante_novo_safe}'"
            HistoricoVaga.create(id_vaga, usuario_logado, msg)
        elif situacao_antiga != situacao_vaga:
            msg = f"Alterou status: '{situacao_antiga}' ➝ '{situacao_vaga}'"
            HistoricoVaga.create(id_vaga, usuario_logado, msg)

        if str(cod_vaga_antigo) != str(cod_vaga_novo):
            msg = f"Alterou código: '{cod_vaga_antigo}' ➝ '{cod_vaga_novo}'"
            HistoricoVaga.create(id_vaga, usuario_logado, msg)

        val_area_antiga = str(area_antiga).strip() if area_antiga else ""
        val_area_nova = str(area_nova).strip() if area_nova else ""
        if val_area_antiga != val_area_nova:
            display_antiga = val_area_antiga if val_area_antiga else "N/A"
            display_nova = val_area_nova if val_area_nova else "N/A"
            msg = f"Alterou área: '{display_antiga}' ➝ '{display_nova}'"
            HistoricoVaga.create(id_vaga, usuario_logado, msg)
            
        # Sincronização (Vaga -> Candidato)
        if candidato_id:
            Candidato.vincular_vaga(candidato_id, cod_vaga_novo)
        else:
            Candidato.desvincular_vaga(cod_vaga_novo)

        flash('Vaga atualizada com sucesso!', 'success')
    else:
        flash('Erro ao atualizar vaga.', 'error')

    # Reabre o cargo
    return redirect(url_for('vaga.painel_vagas', open=cargo_id))

@vaga_bp.route('/vaga/remover/<int:id_vaga>', methods=['POST'])
def remover_vaga(id_vaga):
    if not check_admin(): return redirect(url_for('auth.login'))
    
    conn = conectar()
    cursor = conn.cursor()
    # Precisamos pegar o cargo_gestao_id TAMBÉM para saber onde voltar
    cursor.execute("SELECT cod_vaga, cargo_gestao_id FROM Vaga WHERE id = ?", (id_vaga,))
    row = cursor.fetchone()
    cod_vaga_para_remover = row[0] if row else None
    id_cargo_pai = row[1] if row else None
    conn.close()

    if Vaga.delete(id_vaga):
        if cod_vaga_para_remover:
            Candidato.desvincular_vaga(cod_vaga_para_remover)
            
        flash('Vaga removida com sucesso.', 'success')
    else:
        flash('Erro ao remover vaga.', 'error')
        
    # Reabre o cargo pai se ele existir
    if id_cargo_pai:
        return redirect(url_for('vaga.painel_vagas', open=id_cargo_pai))
    else:
        return redirect(url_for('vaga.painel_vagas'))

@vaga_bp.route('/api/historico/<int:id_vaga>')
def get_historico_vaga(id_vaga):
    if 'usuario_id' not in session:
        return jsonify([]), 401
    
    historico = HistoricoVaga.get_by_vaga(id_vaga)
    return jsonify(historico)