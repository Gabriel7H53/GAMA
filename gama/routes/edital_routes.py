# gama/routes/edital_routes.py
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify
from gama.models.edital import Edital, Cargo, PortariaRascunho, HistoricoEdital
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

def usuario_logado():
    return session.get('nome', 'Usuário')

def registrar_historico(id_edital, tipo, descricao):
    if id_edital:
        HistoricoEdital.create(id_edital, usuario_logado(), tipo, descricao)

@edital_bp.route('/api/historico')
@edital_bp.route('/api/historico/<int:id_edital>')
def api_historico(id_edital=None):
    if not check_admin():
        return jsonify([]), 403
    return jsonify(Edital.get_historico(id_edital))

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
    rascunhos_portaria = PortariaRascunho.get_all_dict()

    return render_template(
        'edital.html', 
        nome=session.get('nome'), 
        editais=editais_com_status_vencimento,
        candidatos_por_edital_agrupado=candidatos_agrupados,
        candidatos_por_edital_simples=candidatos_simples,
        opcoes_unidade=opcoes_unidade,
        vagas_livres=vagas_livres,
        rascunhos_portaria=rascunhos_portaria
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
    if success:
        novo = Edital.get_by_numero(numero_edital)
        if novo:
            registrar_historico(novo[0], 'criacao', f"Criou o edital '{numero_edital}' (status: {status}, vencimento: {vencimento_edital})")
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

    # O campo de vencimento do formulário já vem com a prorrogação anterior embutida.
    # Só recalcula quando o prazo foi AUMENTADO em relação ao valor salvo, somando apenas a diferença.
    edital_atual = Edital.get_by_id(id_edital)
    try:
        prazo_anterior = int(edital_atual[5] or 0) if edital_atual else 0
    except (ValueError, TypeError):
        prazo_anterior = 0

    if prazo_prorrogacao > prazo_anterior:
        dias_adicionais = prazo_prorrogacao - prazo_anterior
        status_final = 'prorrogado'

        try:
            data_base_vencimento = datetime.strptime(vencimento_edital_str, '%Y-%m-%d')
            data_vencimento_nova = data_base_vencimento + timedelta(days=dias_adicionais)
            vencimento_final_str = data_vencimento_nova.strftime('%Y-%m-%d')
            flash(f'Edital prorrogado em {dias_adicionais} dia(s)! Novo vencimento: {vencimento_final_str}.', 'info')
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
        status_final,
        usuario_responsavel=session.get('nome', 'Usuário')
    )
    
    flash(message, 'success' if success else 'error')
    return redirect(url_for('edital.painel'))


@edital_bp.route('/remover/<int:id_edital>', methods=['POST'])
def remover_edital(id_edital):
    if not check_admin():
        return redirect(url_for('auth.login'))
        
    edital_atual = Edital.get_by_id(id_edital)
    qtd_candidatos = len(Candidato.get_by_edital(id_edital)) if edital_atual else 0

    success, message = Edital.delete(id_edital)
    if success and edital_atual:
        registrar_historico(id_edital, 'remocao', f"Removeu o edital '{edital_atual[1]}' e seus {qtd_candidatos} candidato(s)")
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
    if portaria:
        PortariaRascunho.save(id_edital, portaria)

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

    if success:
        registrar_historico(id_edital, 'candidato_adicionado', f"Adicionou o candidato '{nome}' (inscrição {inscricao}, cargo '{nome_cargo}', situação: {situacao})")

    if success and cod_vaga:
        Vaga.ocupar_por_codigo(cod_vaga, nome)

    flash(message, 'success' if success else 'error')
    return redirect(url_for('edital.painel', open=id_edital))


@edital_bp.route('/candidato/editar/<int:id_candidato>', methods=['POST'])
def editar_candidato(id_candidato):
    if not check_admin():
        return redirect(url_for('auth.login'))
    candidato_antigo = Candidato.get_by_id(id_candidato)
    cod_vaga_antigo = candidato_antigo['cod_vaga'] if candidato_antigo else None
    id_edital = int(request.form['id_edital'])
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
    if portaria:
        PortariaRascunho.save(id_edital, portaria)

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

    if success and candidato_antigo:
        def _v(x):
            return '' if x is None else str(x)
        comparacoes = [
            ('nome', candidato_antigo['nome'], nome),
            ('inscrição', candidato_antigo['numero_inscricao'], inscricao),
            ('cargo', candidato_antigo['nome_cargo'], nome_cargo),
            ('nota', candidato_antigo['nota'], nota),
            ('classificação', candidato_antigo['classificacao'], classificacao),
            ('situação', candidato_antigo['situacao'], situacao),
            ('data de posse', candidato_antigo['data_posse'], data_posse),
            ('lotação', candidato_antigo['lotacao'], lotacao),
            ('código da vaga', candidato_antigo['cod_vaga'], cod_vaga_novo),
        ]
        alteracoes = []
        for rotulo, antigo, novo in comparacoes:
            if rotulo == 'nota':
                try:
                    if float(antigo) == float(novo):
                        continue
                except (ValueError, TypeError):
                    pass
            if _v(antigo).strip() != _v(novo).strip():
                alteracoes.append(f"{rotulo}: '{_v(antigo)}' ➝ '{_v(novo)}'")
        if bool(candidato_antigo['contatado']) != contatado:
            ant = 'Sim' if candidato_antigo['contatado'] else 'Não'
            novo_c = 'Sim' if contatado else 'Não'
            alteracoes.append(f"contatado: '{ant}' ➝ '{novo_c}'")
        if alteracoes:
            registrar_historico(id_edital, 'candidato_editado', f"Alterou o candidato '{candidato_antigo['nome']}' — " + '; '.join(alteracoes))

    if success:
        if cod_vaga_antigo and cod_vaga_antigo != cod_vaga_novo:
            Vaga.desocupar_por_codigo(cod_vaga_antigo)
        
        if cod_vaga_novo:
            Vaga.ocupar_por_codigo(cod_vaga_novo, nome)

    flash(message, 'success' if success else 'error')
    return redirect(url_for('edital.painel', open=id_edital))


@edital_bp.route('/candidato/remover/<int:id_candidato>', methods=['POST'])
def remover_candidato(id_candidato):
    if not check_admin():
        return redirect(url_for('auth.login'))
    
    candidato = Candidato.get_by_id(id_candidato)
    id_edital_destino = candidato['id_edital'] if candidato else None

    success, message = Candidato.delete(id_candidato)

    if success and candidato:
        registrar_historico(id_edital_destino, 'candidato_removido', f"Removeu o candidato '{candidato['nome']}' (inscrição {candidato['numero_inscricao']}, cargo '{candidato['nome_cargo']}')")
    
    if success and candidato and candidato['cod_vaga']:
        from gama.models.vaga import Vaga 
        Vaga.desocupar_por_codigo(candidato['cod_vaga'])

    flash(message, 'success' if success else 'error')
    
    if id_edital_destino:
        return redirect(url_for('edital.painel', open=id_edital_destino))
    else:
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
            registrar_historico(id_edital, 'candidato_adicionado', f"Importou {candidatos_adicionados} candidato(s) via planilha CSV ({arquivo.filename})")
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
    nomes_nomeados = []
    for id_candidato in ids_candidatos_selecionados:
        info = Candidato.get_by_id(id_candidato)
        if Candidato.nomear(id_candidato):
            nomeados_com_sucesso += 1
            if info:
                nomes_nomeados.append(info['nome'])
    if nomeados_com_sucesso > 0:
        registrar_historico(id_edital, 'candidato_nomeado', f"Nomeou {nomeados_com_sucesso} candidato(s): " + ', '.join(nomes_nomeados))
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
    nomes_empossados = []
    for id_candidato in ids_candidatos_selecionados:
        info = Candidato.get_by_id(id_candidato)
        if Candidato.empossar(id_candidato, data_posse):
            empossados_com_sucesso += 1
            if info:
                nomes_empossados.append(info['nome'])
    if empossados_com_sucesso > 0:
        registrar_historico(id_edital, 'candidato_empossado', f"Empossou {empossados_com_sucesso} candidato(s) em {data_posse}: " + ', '.join(nomes_empossados))
        flash(f'{empossados_com_sucesso} candidato(s) empossado(s) com sucesso para a data de {data_posse}!', 'success')
    return redirect(url_for('edital.painel'))