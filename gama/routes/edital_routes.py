# gama/routes/edital_routes.py
from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from gama.models.edital import Edital, Cargo, Candidato
from datetime import datetime, timedelta
from collections import defaultdict # <- Importe esta linha
import csv
import io

edital_bp = Blueprint('edital', __name__, template_folder='../templates')

def check_admin():
    return 'usuario_id' in session and session.get('tipo') == 'administrador'

# --- FUNÇÃO PAINEL ATUALIZADA ---

@edital_bp.route('/painel')
def painel():
    if not check_admin():
        flash('Acesso negado. Apenas administradores podem gerenciar editais.', 'error')
        return redirect(url_for('auth.login'))

    editais = Edital.get_all()
    candidatos_por_edital = {}
    for edital in editais:
        todos_candidatos_do_edital = Candidato.get_by_edital(edital[0])
        
        candidatos_agrupados_por_cargo = defaultdict(list)
        for candidato in todos_candidatos_do_edital:
            nome_cargo = candidato[11] # O nome do cargo está na posição 11
            candidatos_agrupados_por_cargo[nome_cargo].append(candidato)
            
        # Armazena o dicionário de candidatos já agrupados por cargo
        candidatos_por_edital[edital[0]] = dict(sorted(candidatos_agrupados_por_cargo.items()))

    return render_template(
        'edital.html', 
        nome=session.get('nome'), 
        editais=editais,
        candidatos_por_edital=candidatos_por_edital
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
    return redirect(url_for('edital.painel'))


@edital_bp.route('/candidato/editar/<int:id_candidato>', methods=['POST'])
def editar_candidato(id_candidato):
    if not check_admin():
        return redirect(url_for('auth.login'))
    
    id_edital = request.form['id_edital']
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

    success, message = Candidato.update(id_candidato, id_cargo, nome, inscricao, nota, classificacao, pcd, cotista, situacao, data_posse)
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
        return redirect(url_for('auth.login'))

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

    # Processamento do arquivo CSV
    try:
        # Decodifica o arquivo em memória
        stream = io.StringIO(arquivo.stream.read().decode("windows-1252"), newline=None)
        reader = csv.reader(stream)

        # Pula o cabeçalho (opcional, mas recomendado)
        next(reader, None)

        # Busca a última classificação para continuar a sequência
        ultima_classificacao = Candidato.get_max_classificacao(id_edital)
        
        candidatos_adicionados = 0
        erros = []

        for i, linha in enumerate(reader):
            if len(linha) < 4:
                erros.append(f"Linha {i+2}: formato inválido (esperado 4 colunas).")
                continue

            nome, inscricao, nota_str, nome_cargo = linha
            
            try:
                # Validação dos dados
                nota = float(nota_str.replace(',', '.'))
                classificacao_atual = ultima_classificacao + i + 1

                # Cria ou obtém o ID do cargo
                id_cargo = Cargo.get_or_create(id_edital, nome_cargo.strip())

                # Adiciona o candidato com valores padrão
                Candidato.create(
                    id_edital=id_edital,
                    id_cargo=id_cargo,
                    nome=nome.strip(),
                    inscricao=inscricao.strip(),
                    nota=nota,
                    classificacao=classificacao_atual,
                    pcd=False,        # Valor padrão
                    cotista=False,    # Valor padrão
                    situacao='a_nomear', # Valor padrão
                    data_posse=None   # Valor padrão
                )
                candidatos_adicionados += 1
            except ValueError:
                erros.append(f"Linha {i+2}: a nota '{nota_str}' não é um número válido.")
            except Exception as e:
                erros.append(f"Linha {i+2} ({nome}): {e}")

        # Mensagem de feedback
        if candidatos_adicionados > 0:
            flash(f'{candidatos_adicionados} candidatos adicionados com sucesso!', 'success')
        if erros:
            msg_erro = f'Ocorreram {len(erros)} erros durante a importação: ' + " | ".join(erros)
            flash(msg_erro, 'error')

    except Exception as e:
        flash(f'Ocorreu um erro ao processar o arquivo: {e}', 'error')

    return redirect(url_for('edital.painel'))