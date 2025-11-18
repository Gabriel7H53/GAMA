# gama/routes/edital_routes.py
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify
from gama.models.edital import Edital, Cargo
from gama.models.candidato import Candidato
from gama.models.configuracao import Opcao 
from gama.models.vaga import Vaga
from datetime import datetime, timedelta, date
from collections import defaultdict
import csv
import io

edital_bp = Blueprint('edital', __name__, template_folder='../templates')

def check_admin():
    return 'usuario_id' in session and session.get('tipo') == 'administrador' or 'usuario'

@edital_bp.route('/painel')
def painel():
    if not check_admin():
        flash('Acesso negado. Apenas administradores podem gerenciar editais.', 'error')
        return redirect(url_for('auth.login'))

    editais_raw = Edital.get_all()
    
    editais_com_status_vencimento = []
    hoje = date.today()
    tres_meses_frente = hoje + timedelta(days=90)

    for edital_tuple in editais_raw:
        edital_lista = list(edital_tuple)
        status_vencimento = 'ok'
        try:
            data_vencimento = datetime.strptime(edital_lista[4], '%Y-%m-%d').date()
            if data_vencimento < hoje:
                status_vencimento = 'vencido'
            elif hoje <= data_vencimento <= tres_meses_frente:
                status_vencimento = 'proximo'
        except (ValueError, TypeError):
            pass
        edital_lista.append(status_vencimento)
        editais_com_status_vencimento.append(edital_lista)

    candidatos_agrupados = {}
    candidatos_simples = {}

    for edital in editais_com_status_vencimento:
        todos_candidatos_do_edital = Candidato.get_by_edital(edital[0])
        candidatos_simples[edital[0]] = todos_candidatos_do_edital
        candidatos_agrupados_por_cargo = defaultdict(list)
        for candidato in todos_candidatos_do_edital:
            nome_cargo = candidato[11] 
            candidatos_agrupados_por_cargo[nome_cargo].append(candidato)
        candidatos_agrupados[edital[0]] = dict(sorted(candidatos_agrupados_por_cargo.items()))

    opcoes_unidade = Opcao.get_por_tipo('unidade')
    vagas_livres = Vaga.get_all_vagas_livres()

    return render_template(
        'edital.html', 
        nome=session.get('nome'), 
        editais=editais_com_status_vencimento,
        candidatos_por_edital_agrupado=candidatos_agrupados,
        candidatos_por_edital_simples=candidatos_simples,
        opcoes_unidade=opcoes_unidade,
        vagas_livres=vagas_livres 
    )

@edital_bp.route('/adicionar', methods=['POST'])
def adicionar_edital():
    if not check_admin():
        return redirect(url_for('auth.login'))
    
    numero_edital = request.form['numero_edital']
    data_edital = request.form['data_edital']
    data_publicacao = request.form['data_publicacao']
    vencimento_edital = request.form['vencimento_edital']
    prazo_prorrogacao = request.form.get('prazo_prorrogacao') or 0
    status = request.form['status']

    success, message = Edital.create(numero_edital, data_edital, data_publicacao, vencimento_edital, prazo_prorrogacao, status)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('edital.painel'))

@edital_bp.route('/editar/<int:id_edital>', methods=['POST'])
def editar_edital(id_edital):
    if not check_admin():
        return redirect(url_for('auth.login'))
        
    numero_edital = request.form['numero_edital']
    data_edital = request.form['data_edital']
    data_publicacao = request.form['data_publicacao']
    vencimento_edital_str = request.form['vencimento_edital']
    status_do_formulario = request.form['status']

    try:
        prazo_prorrogacao = int(request.form.get('prazo_prorrogacao') or 0)
    except (ValueError, TypeError):
        prazo_prorrogacao = 0

    status_final = status_do_formulario
    vencimento_final_str = vencimento_edital_str

    if prazo_prorrogacao > 0:
        status_final = 'prorrogado'
        
        try:
            data_base_vencimento = datetime.strptime(vencimento_edital_str, '%Y-%m-%d')
            data_vencimento_nova = data_base_vencimento + timedelta(days=prazo_prorrogacao)
            vencimento_final_str = data_vencimento_nova.strftime('%Y-%m-%d')
            flash(f'Edital prorrogado! Novo vencimento: {vencimento_final_str}.', 'info')
        except ValueError:
            flash('Formato de data de vencimento inválido. A prorrogação não pôde ser calculada.', 'error')
            return redirect(url_for('edital.painel'))

    success, message = Edital.update(
        id_edital, 
        numero_edital, 
        data_edital, 
        data_publicacao, 
        vencimento_final_str, 
        prazo_prorrogacao, 
        status_final
    )
    
    flash(message, 'success' if success else 'error')
    return redirect(url_for('edital.painel'))


@edital_bp.route('/remover/<int:id_edital>', methods=['POST'])
def remover_edital(id_edital):
    if not check_admin():
        return redirect(url_for('auth.login'))
        
    success, message = Edital.delete(id_edital)
    flash(message, 'success' if success else 'error')
    return redirect(url_for('edital.painel'))


@edital_bp.route('/<int:id_edital>/candidato/adicionar', methods=['POST'])
def adicionar_candidato(id_edital):
    if not check_admin():
        return redirect(url_for('auth.login'))

    nome_cargo = request.form['nome_cargo'].strip()
    padrao_vencimento = request.form['padrao_vencimento'] 
    id_cargo = Cargo.get_or_create(id_edital, nome_cargo, padrao_vencimento)
    
    nome = request.form['nome']
    inscricao = request.form['numero_inscricao']
    nota = request.form['nota']
    classificacao = request.form['classificacao']
    pcd = 'pcd' in request.form
    cotista = 'cotista' in request.form
    situacao = request.form['situacao']
    data_posse = request.form.get('data_posse')
    portaria = request.form.get('portaria')
    lotacao = request.form.get('lotacao')
    contatado = 'contatado' in request.form
    
    cod_vaga = request.form.get('cod_vaga')
    if cod_vaga == "": 
        cod_vaga = None

    success, message = Candidato.create(
        id_edital, id_cargo, nome, inscricao, nota, classificacao, 
        pcd, cotista, situacao, data_posse, 
        portaria, lotacao, contatado, cod_vaga
    ) 

    # --- NOVO: Atualiza a Vaga se foi selecionada ---
    if success and cod_vaga:
        Vaga.ocupar_por_codigo(cod_vaga, nome)
    # -----------------------------------------------

    flash(message, 'success' if success else 'error')
    return redirect(url_for('edital.painel'))


@edital_bp.route('/candidato/editar/<int:id_candidato>', methods=['POST'])
def editar_candidato(id_candidato):
    if not check_admin():
        return redirect(url_for('auth.login'))

    # --- NOVO: Busca dados ANTES da atualização para saber a vaga antiga ---
    candidato_antigo = Candidato.get_by_id(id_candidato)
    cod_vaga_antigo = candidato_antigo['cod_vaga'] if candidato_antigo else None
    # ---------------------------------------------------------------------

    id_edital = request.form['id_edital']
    nome_cargo = request.form['nome_cargo'].strip()
    padrao_vencimento = request.form['padrao_vencimento'] 
    id_cargo = Cargo.get_or_create(id_edital, nome_cargo, padrao_vencimento)

    nome = request.form['nome']
    inscricao = request.form['numero_inscricao']
    nota = request.form['nota']
    classificacao = request.form['classificacao']
    pcd = 'pcd' in request.form
    cotista = 'cotista' in request.form
    situacao = request.form['situacao']
    data_posse = request.form.get('data_posse') 
    portaria = request.form.get('portaria')
    lotacao = request.form.get('lotacao')
    contatado = 'contatado' in request.form
    
    cod_vaga_novo = request.form.get('cod_vaga')
    if cod_vaga_novo == "": 
        cod_vaga_novo = None

    success, message = Candidato.update(
        id_candidato, id_cargo, nome, inscricao, nota, classificacao, 
        pcd, cotista, situacao, data_posse, 
        portaria, lotacao, contatado, cod_vaga_novo
    ) 

    # --- NOVO: Lógica de Troca de Vagas ---
    if success:
        # 1. Se tinha vaga antes e mudou (ou removeu), libera a antiga
        if cod_vaga_antigo and cod_vaga_antigo != cod_vaga_novo:
            Vaga.desocupar_por_codigo(cod_vaga_antigo)
        
        # 2. Se tem vaga nova (e é diferente da antiga ou apenas atualização de nome), ocupa a nova
        if cod_vaga_novo:
            # Atualiza o ocupante (útil mesmo se a vaga for a mesma, caso o nome do candidato tenha mudado)
            Vaga.ocupar_por_codigo(cod_vaga_novo, nome)
    # --------------------------------------

    flash(message, 'success' if success else 'error')
    return redirect(url_for('edital.painel'))


@edital_bp.route('/candidato/remover/<int:id_candidato>', methods=['POST'])
def remover_candidato(id_candidato):
    if not check_admin():
        return redirect(url_for('auth.login'))
        
    # --- NOVO: Verifica se o candidato ocupava uma vaga ---
    candidato = Candidato.get_by_id(id_candidato)
    cod_vaga = candidato['cod_vaga'] if candidato else None
    # ----------------------------------------------------

    success, message = Candidato.delete(id_candidato)
    
    # --- NOVO: Libera a vaga se a exclusão funcionou ---
    if success and cod_vaga:
        Vaga.desocupar_por_codigo(cod_vaga)
    # ---------------------------------------------------

    flash(message, 'success' if success else 'error')
    return redirect(url_for('edital.painel'))

@edital_bp.route('/<int:id_edital>/candidato/adicionar_lote', methods=['POST'])
def adicionar_lote(id_edital):
    if not check_admin():
        flash('Acesso negado.', 'error')
        return redirect(url_for('edital.painel'))
    if 'planilha' not in request.files:
        flash('Nenhum arquivo enviado.', 'error')
        return redirect(url_for('edital.painel'))
    arquivo = request.files['planilha']
    if arquivo.filename == '':
        flash('Nenhum arquivo selecionado.', 'error')
        return redirect(url_for('edital.painel'))
    if not arquivo.filename.lower().endswith('.csv'):
        flash('Formato de arquivo inválido. Por favor, envie um arquivo .csv', 'error')
        return redirect(url_for('edital.painel'))
    try:
        stream = io.StringIO(arquivo.stream.read().decode("utf-8"), newline=None)
        reader = csv.reader(stream)
        next(reader, None) 
        candidatos_lidos = []
        erros_leitura = []
        for i, linha in enumerate(reader):
            if len(linha) < 5: 
                erros_leitura.append(f"Linha {i+2}: formato inválido (esperadas 5 colunas).") 
                continue
            nome, inscricao, nota_str, nome_cargo, padrao_vencimento = linha 
            padrao_vencimento = padrao_vencimento.strip().upper() 
            if padrao_vencimento not in ('D', 'E'):
                erros_leitura.append(f"Linha {i+2}: Padrão de Vencimento '{padrao_vencimento}' inválido (deve ser 'D' ou 'E').")
                continue
            try:
                nota = float(nota_str.replace(',', '.'))
                candidatos_lidos.append({
                    'nome': nome.strip(),
                    'inscricao': inscricao.strip(),
                    'nota': nota,
                    'nome_cargo': nome_cargo.strip(),
                    'padrao_vencimento': padrao_vencimento 
                })
            except ValueError:
                erros_leitura.append(f"Linha {i+2}: a nota '{nota_str}' não é um número válido.") 
        if erros_leitura:
            flash('Erros encontrados no arquivo: ' + " | ".join(erros_leitura), 'error') 
            return redirect(url_for('edital.painel'))
        candidatos_por_cargo = defaultdict(list)
        for candidato in candidatos_lidos:
            candidatos_por_cargo[candidato['nome_cargo']].append(candidato) 
        candidatos_adicionados = 0
        erros_insercao = []
        for nome_cargo, lista_candidatos in candidatos_por_cargo.items():
            try:
                padrao_vencimento_cargo = lista_candidatos[0]['padrao_vencimento']
                id_cargo = Cargo.get_or_create(id_edital, nome_cargo, padrao_vencimento_cargo)
                ultima_classificacao = Candidato.get_max_classificacao(id_edital, id_cargo) 
                classificacao_counter = ultima_classificacao + 1
                for candidato in lista_candidatos:
                    Candidato.create(
                        id_edital=id_edital,
                        id_cargo=id_cargo,
                        nome=candidato['nome'],
                        inscricao=candidato['inscricao'],
                        nota=candidato['nota'],
                        classificacao=classificacao_counter,
                        pcd=False, cotista=False, situacao='homologado', data_posse=None
                    ) 
                    candidatos_adicionados += 1
                    classificacao_counter += 1
            except Exception as e:
                erros_insercao.append(f"Cargo '{nome_cargo}': {e}")
        if candidatos_adicionados > 0:
            flash(f'{candidatos_adicionados} candidatos adicionados com sucesso!', 'success')
        if erros_insercao:
            flash(f'Ocorreram erros durante a inserção: ' + " | ".join(erros_insercao), 'error')
    except Exception as e:
        flash(f'Ocorreu um erro fatal ao processar o arquivo: {e}', 'error')
    return redirect(url_for('edital.painel'))

@edital_bp.route('/<int:id_edital>/candidato/nomear_lote', methods=['POST'])
def nomear_lote(id_edital):
    if not check_admin():
        flash('Acesso negado.', 'error')
        return redirect(url_for('auth.login'))
    ids_candidatos_selecionados = request.form.getlist('candidato_ids')
    if not ids_candidatos_selecionados:
        flash('Nenhum candidato foi selecionado.', 'error')
        return redirect(url_for('edital.painel'))
    nomeados_com_sucesso = 0
    for id_candidato in ids_candidatos_selecionados:
        if Candidato.nomear(id_candidato):
            nomeados_com_sucesso += 1
    if nomeados_com_sucesso > 0:
        flash(f'{nomeados_com_sucesso} candidato(s) nomeado(s) com sucesso!', 'success')
    return redirect(url_for('edital.painel'))

@edital_bp.route('/<int:id_edital>/candidato/empossar_lote', methods=['POST'])
def empossar_lote(id_edital):
    if not check_admin():
        flash('Acesso negado.', 'error')
        return redirect(url_for('auth.login'))
    ids_candidatos_selecionados = request.form.getlist('candidato_ids_empossar') 
    data_posse = request.form.get('data_posse_lote_empossar')
    if not data_posse:
        flash('A data de posse é obrigatória.', 'error')
        return redirect(url_for('edital.painel'))
    if not ids_candidatos_selecionados:
        flash('Nenhum candidato foi selecionado.', 'error')
        return redirect(url_for('edital.painel'))
    empossados_com_sucesso = 0
    for id_candidato in ids_candidatos_selecionados:
        if Candidato.empossar(id_candidato, data_posse): 
            empossados_com_sucesso += 1
    if empossados_com_sucesso > 0:
        flash(f'{empossados_com_sucesso} candidato(s) empossado(s) com sucesso para a data de {data_posse}!', 'success')
    return redirect(url_for('edital.painel'))