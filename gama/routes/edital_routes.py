# gama/routes/edital_routes.py
from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify
from gama.models.edital import Edital, Cargo
from gama.models.candidato import Candidato
from datetime import datetime, timedelta, date
from collections import defaultdict
import csv
import io

edital_bp = Blueprint('edital', __name__, template_folder='../templates')

def check_admin():
    return 'usuario_id' in session and session.get('tipo') == 'administrador' or 'usuario'

# --- FUNÇÃO PAINEL ATUALIZADA ---
# Sua função 'painel' adaptada com a nova lógica
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

    return render_template(
        'edital.html', 
        nome=session.get('nome'), 
        editais=editais_com_status_vencimento,
        candidatos_por_edital_agrupado=candidatos_agrupados,
        candidatos_por_edital_simples=candidatos_simples
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

# --- FUNÇÃO EDITAR EDITAL ATUALIZADA COM A NOVA LÓGICA ---
@edital_bp.route('/editar/<int:id_edital>', methods=['POST'])
def editar_edital(id_edital):
    if not check_admin():
        return redirect(url_for('auth.login'))
        
    # 1. Coleta dos dados do formulário
    numero_edital = request.form['numero_edital']
    data_edital = request.form['data_edital']
    data_publicacao = request.form['data_publicacao']
    vencimento_edital_str = request.form['vencimento_edital']
    status_do_formulario = request.form['status']

    # Converte o prazo de prorrogação para inteiro de forma segura
    try:
        prazo_prorrogacao = int(request.form.get('prazo_prorrogacao') or 0)
    except (ValueError, TypeError):
        prazo_prorrogacao = 0

    # Variáveis finais que serão salvas no banco
    status_final = status_do_formulario
    vencimento_final_str = vencimento_edital_str

    # 2. Aplicação da nova lógica de prorrogação
    if prazo_prorrogacao > 0:
        # Requisito: Muda o status para "prorrogado" automaticamente
        status_final = 'prorrogado'
        
        # Requisito: Atualiza a data de vencimento
        try:
            data_base_vencimento = datetime.strptime(vencimento_edital_str, '%Y-%m-%d')
            data_vencimento_nova = data_base_vencimento + timedelta(days=prazo_prorrogacao)
            vencimento_final_str = data_vencimento_nova.strftime('%Y-%m-%d')
            flash(f'Edital prorrogado! Novo vencimento: {vencimento_final_str}.', 'info')
        except ValueError:
            # Caso a data no formulário seja inválida
            flash('Formato de data de vencimento inválido. A prorrogação não pôde ser calculada.', 'error')
            return redirect(url_for('edital.painel'))

    # 3. Chamada ao banco de dados com os valores atualizados
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
    padrao_vencimento = request.form['padrao_vencimento'] # <-- GET the new field from form
    # Pass it to get_or_create
    id_cargo = Cargo.get_or_create(id_edital, nome_cargo, padrao_vencimento)
    # ... (rest of the function remains the same) ...
    nome = request.form['nome']
    inscricao = request.form['numero_inscricao']
    nota = request.form['nota']
    classificacao = request.form['classificacao']
    pcd = 'pcd' in request.form
    cotista = 'cotista' in request.form
    situacao = request.form['situacao']
    data_posse = request.form.get('data_posse')
    success, message = Candidato.create(id_edital, id_cargo, nome, inscricao, nota, classificacao, pcd, cotista, situacao, data_posse) #

    flash(message, 'success' if success else 'error')
    return redirect(url_for('edital.painel'))


@edital_bp.route('/candidato/editar/<int:id_candidato>', methods=['POST'])
def editar_candidato(id_candidato):
    if not check_admin():
        return redirect(url_for('auth.login'))

    id_edital = request.form['id_edital']
    nome_cargo = request.form['nome_cargo'].strip()
    padrao_vencimento = request.form['padrao_vencimento'] # <-- GET the new field from form
    # Pass it to get_or_create
    id_cargo = Cargo.get_or_create(id_edital, nome_cargo, padrao_vencimento)
    # ... (rest of the function remains the same) ...
    nome = request.form['nome']
    inscricao = request.form['numero_inscricao']
    nota = request.form['nota']
    classificacao = request.form['classificacao']
    pcd = 'pcd' in request.form
    cotista = 'cotista' in request.form
    situacao = request.form['situacao']
    data_posse = request.form.get('data_posse') #

    success, message = Candidato.update(id_candidato, id_cargo, nome, inscricao, nota, classificacao, pcd, cotista, situacao, data_posse) #
    flash(message, 'success' if success else 'error')
    return redirect(url_for('edital.painel'))


@edital_bp.route('/candidato/remover/<int:id_candidato>', methods=['POST'])
def remover_candidato(id_candidato):
    if not check_admin():
        return redirect(url_for('auth.login'))
        
    success, message = Candidato.delete(id_candidato)
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
        next(reader, None) # Pula o cabeçalho

        candidatos_lidos = []
        erros_leitura = []

        for i, linha in enumerate(reader):
            # Expect 5 columns now
            if len(linha) < 5: # <-- UPDATED Check
                erros_leitura.append(f"Linha {i+2}: formato inválido (esperadas 5 colunas).") # <-- UPDATED Message
                continue

            # Unpack 5 values
            nome, inscricao, nota_str, nome_cargo, padrao_vencimento = linha # <-- UPDATED Unpacking
            padrao_vencimento = padrao_vencimento.strip().upper() # Ensure it's uppercase D or E

            # Validate padrao_vencimento
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
                    'padrao_vencimento': padrao_vencimento # <-- STORE the value
                })
            except ValueError:
                erros_leitura.append(f"Linha {i+2}: a nota '{nota_str}' não é um número válido.") #

        if erros_leitura:
            flash('Erros encontrados no arquivo: ' + " | ".join(erros_leitura), 'error') #
            return redirect(url_for('edital.painel'))

        # Grouping remains the same
        candidatos_por_cargo = defaultdict(list)
        for candidato in candidatos_lidos:
            candidatos_por_cargo[candidato['nome_cargo']].append(candidato) #

        candidatos_adicionados = 0
        erros_insercao = []

        for nome_cargo, lista_candidatos in candidatos_por_cargo.items():
            try:
                # Assume the first candidate in the list for this cargo has the correct pattern
                # (Alternatively, you could add logic to ensure all candidates for the same cargo
                # in the CSV have the same pattern, or handle conflicts)
                padrao_vencimento_cargo = lista_candidatos[0]['padrao_vencimento']

                # Pass the pattern when getting/creating the cargo ID
                id_cargo = Cargo.get_or_create(id_edital, nome_cargo, padrao_vencimento_cargo)
                ultima_classificacao = Candidato.get_max_classificacao(id_edital, id_cargo) #
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
                    ) #
                    candidatos_adicionados += 1
                    classificacao_counter += 1
            
            except Exception as e:
                erros_insercao.append(f"Cargo '{nome_cargo}': {e}")

        # Mensagens de feedback
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

    data_posse = request.form.get('data_posse_lote')
    # request.form.getlist() é usado para obter todos os valores de checkboxes com o mesmo nome
    ids_candidatos_selecionados = request.form.getlist('candidato_ids')

    if not data_posse:
        flash('A data de posse é obrigatória.', 'error')
        return redirect(url_for('edital.painel'))

    if not ids_candidatos_selecionados:
        flash('Nenhum candidato foi selecionado.', 'error')
        return redirect(url_for('edital.painel'))

    nomeados_com_sucesso = 0
    for id_candidato in ids_candidatos_selecionados:
        if Candidato.nomear(id_candidato, data_posse):
            nomeados_com_sucesso += 1
    
    if nomeados_com_sucesso > 0:
        flash(f'{nomeados_com_sucesso} candidato(s) nomeado(s) com sucesso para a data de {data_posse}!', 'success')

    return redirect(url_for('edital.painel'))

@edital_bp.route('/api/candidatos/search')
def search_candidatos():
    # Pega o texto digitado que veio como parâmetro na URL (ex: /api/candidatos/search?query=Joao)
    query = request.args.get('query', '')
    if len(query) < 2: # Só busca se tiver pelo menos 2 caracteres
        return jsonify([])

    nomes = Candidato.search_by_name(query)
    return jsonify(nomes)