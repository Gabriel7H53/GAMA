from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from gama.models.edital import Edital
from gama.models.candidato import Candidato
from gama.models.certificado import Certificado
from gama.models.configuracao import Opcao # Importa o modelo de Opcao
from collections import defaultdict 
import io
import locale
from datetime import datetime
from docxtpl import DocxTemplate
from flask import send_file
import pandas as pd
import zipfile

certificado_bp = Blueprint('certificado', __name__, template_folder='../templates')

# --- FUNÇÃO AUXILIAR ---
def numero_por_extenso(n):
    """Converte um número (dia do mês, 1-31) para português por extenso."""
    unidades = {
        1: 'um', 2: 'dois', 3: 'três', 4: 'quatro', 5: 'cinco',
        6: 'seis', 7: 'sete', 8: 'oito', 9: 'nove', 10: 'dez',
        11: 'onze', 12: 'doze', 13: 'treze', 14: 'catorze', 15: 'quinze',
        16: 'dezesseis', 17: 'dezessete', 18: 'dezoito', 19: 'dezenove'
    }
    dezenas = {
        20: 'vinte', 30: 'trinta'
    }
    if n in unidades:
        return unidades[n]
    if n in dezenas:
        return dezenas[n]
    if 20 < n < 30:
        return f'vinte e {unidades[n-20]}'
    if 30 < n < 40: # Cobre apenas o 31
        return f'trinta e {unidades[n-30]}'
    return str(n) # Fallback
# --- FIM DA FUNÇÃO AUXILIAR ---


# ===============================================
# ROTAS DO TERMO DE POSSE
# ===============================================

@certificado_bp.route('/painel')
def painel_certificados():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    editais = Edital.get_all()
    
    candidatos_agrupados = defaultdict(lambda: defaultdict(list))
    todos_candidatos_raw = Candidato.get_all_with_details() 

    # Filtra a lista para incluir APENAS candidatos com situação 'nomeado'
    todos_candidatos_filtrados = [c for c in todos_candidatos_raw if c['situacao'] == 'nomeado']

    # Agrupa os candidatos já filtrados e ordenados (pela query do SQL)
    for candidato in todos_candidatos_filtrados:
        id_edital = candidato['id_edital']
        nome_cargo = candidato['nome_cargo']
        candidatos_agrupados[id_edital][nome_cargo].append(candidato)

    certificados_emitidos = Certificado.get_all()
    
    # ======================================================
    # ALTERAÇÃO AQUI: Buscando os valores padrão
    # ======================================================
    opcoes_reitor = Opcao.get_por_tipo('reitor')
    opcoes_local = Opcao.get_por_tipo('local')

    # Encontra o valor padrão em cada lista (ou usa None se não houver)
    # A função next() para o primeiro item que satisfaz a condição
    default_reitor = next((r['valor_opcao'] for r in opcoes_reitor if r['is_default']), None)
    default_local = next((l['valor_opcao'] for l in opcoes_local if l['is_default']), None)
    # ======================================================
    # FIM DA ALTERAÇÃO
    # ======================================================

    return render_template(
        'certificados.html',
        nome=session.get('nome'),
        editais=editais,
        candidatos_por_edital_agrupado=candidatos_agrupados,
        certificados_emitidos=certificados_emitidos,
        opcoes_reitor=opcoes_reitor,
        opcoes_local=opcoes_local,
        # ======================================================
        # ALTERAÇÃO AQUI: Passando os padrões para o template
        # ======================================================
        default_reitor=default_reitor,
        default_local=default_local
        # ======================================================
        # FIM DA ALTERAÇÃO
        # ======================================================
    )

@certificado_bp.route('/painel_declaracoes')
def painel_declaracoes():
    return render_template('painel_declaracoes.html', nome=session.get('nome'))

@certificado_bp.route('/gerar', methods=['POST'])
def gerar_certificado():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    try:
        id_candidato = request.form.get('id_candidato')
        template_selecionado = request.form.get('template_selecionado') # 'modeloposse.docx'
        data_nomeacao_str = request.form.get('data') 
        data_emissao_str = request.form.get('data_1') # Este campo não parece estar sendo usado no modal
        local = request.form.get('local')
        reitor = request.form.get('reitor')

        campos_obrigatorios = {
            'Candidato': id_candidato,
            'Template': template_selecionado,
            'Data de Posse': data_nomeacao_str, # O label no form é 'Data de Posse'
            'Portaria': request.form.get('portaria'),
            'Local': local,
            'Reitor': reitor
        }
        
        for nome_campo, valor in campos_obrigatorios.items():
            if not valor:
                flash(f'O campo "{nome_campo}" é obrigatório e não foi preenchido.', 'error')
                return redirect(url_for('certificado.painel_certificados'))

        # O 'get_by_id' agora também busca 'portaria' e 'lotacao', mas não precisamos deles aqui
        candidato = Candidato.get_by_id(id_candidato)
        if not candidato:
            flash('Candidato não encontrado.', 'error')
            return redirect(url_for('certificado.painel_certificados'))

        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
        
        data_nomeacao_obj = datetime.strptime(data_nomeacao_str, '%Y-%m-%d')
        dia_extenso = numero_por_extenso(data_nomeacao_obj.day)
        mes_extenso = data_nomeacao_obj.strftime('%B')
        ano_extenso = data_nomeacao_obj.strftime('%Y')
        
        data_emissao_extenso = data_nomeacao_obj.strftime('%d de %B de %Y')

        context = {
            'nome': candidato['nome'],
            'cargo': candidato['nome_cargo'],
            'nivel': candidato['padrao_vencimento'],
            'dia': dia_extenso,
            'mês': mes_extenso,
            'ano': ano_extenso,
            'local': local,
            'reitor': reitor,
            'portaria': request.form.get('portaria'),
            'dou': '',
            'carga_horaria': request.form.get('carga_horaria'),
            'lotacao': request.form.get('lotacao'),
            'codigo_vaga': request.form.get('codigo_vaga'),
            'data_1': data_emissao_extenso,
        }

        doc = DocxTemplate(f'gama/docx_templates/{template_selecionado}')
        doc.render(context)

        file_stream = io.BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)

        Certificado.create(
            nome_template=template_selecionado,
            id_candidato=id_candidato,
            id_usuario_emissor=session['usuario_id']
        )

        return send_file(
            file_stream,
            as_attachment=True,
            download_name=f'Termo de Posse - {candidato["nome"]}.docx',
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    except Exception as e:
        flash(f'Ocorreu um erro ao gerar o documento: {e}', 'error')
        print(f"ERRO: {e}")
        return redirect(url_for('certificado.painel_certificados'))
    
@certificado_bp.route('/gerar-lote', methods=['POST'])
def gerar_lote():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    if 'planilha' not in request.files or request.files['planilha'].filename == '':
        flash('Nenhum arquivo de planilha enviado.', 'error')
        return redirect(url_for('certificado.painel_certificados'))

    planilha = request.files['planilha']
    if not planilha.filename.endswith('.xlsx'):
        flash('Formato de arquivo inválido. Por favor, envie um arquivo .xlsx', 'error')
        return redirect(url_for('certificado.painel_certificados'))

    try:
        df = pd.read_excel(planilha)
        
        required_cols = ['nivel', 'local', 'reitor', 'data', 'nome', 'cargo', 'portaria']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            flash(f"Erro na planilha: Coluna(s) não encontrada(s): {', '.join(missing_cols)}.", 'error')
            return redirect(url_for('certificado.painel_certificados'))
        
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for index, row in df.iterrows():
                
                data_nomeacao_obj = row['data']
                dia_extenso = numero_por_extenso(data_nomeacao_obj.day)
                mes_extenso = data_nomeacao_obj.strftime('%B')
                ano_extenso = data_nomeacao_obj.strftime('%Y')
                
                data_emissao_extenso = data_nomeacao_obj.strftime('%d de %B de %Y')

                context = {
                    'nome': row['nome'],
                    'cargo': row['cargo'],
                    'nivel': row['nivel'],
                    'dia': dia_extenso,
                    'mês': mes_extenso,
                    'ano': ano_extenso,
                    'local': row['local'],
                    'reitor': row['reitor'],
                    'portaria': row['portaria'],
                    'dou': '', 
                    'carga_horaria': row.get('carga_horaria', '40'), # Valor padrão caso não exista
                    'lotacao': row.get('lotacao', ''),
                    'codigo_vaga': row.get('codigo_vaga', ''),
                    'data_1': data_emissao_extenso,
                }

                doc = DocxTemplate('gama/docx_templates/modeloposse.docx')
                doc.render(context)
                
                nome_arquivo_saida = f"Termo de Posse - {row['nome']}.docx"

                docx_buffer = io.BytesIO()
                doc.save(docx_buffer)
                docx_buffer.seek(0)
                
                zip_file.writestr(nome_arquivo_saida, docx_buffer.read())
        
        zip_buffer.seek(0)
        
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name='Termos_de_Posse_Lote.zip',
            mimetype='application/zip'
        )

    except Exception as e:
        flash(f'Ocorreu um erro ao processar a planilha: {e}', 'error')
        print(f"ERRO NO LOTE: {e}")
        return redirect(url_for('certificado.painel_certificados'))

# ===============================================
# NOVAS ROTAS P/ TERMO DE APRESENTAÇÃO
# ===============================================

@certificado_bp.route('/painel_apresentacao')
def painel_apresentacao():
    """Exibe a página de geração de Termos de Apresentação."""
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    editais = Edital.get_all()
    
    # Busca candidatos (que agora tem 'data_posse' e 'padrao_vencimento')
    candidatos_agrupados = defaultdict(lambda: defaultdict(list))
    todos_candidatos = Candidato.get_all_with_details() 

    for candidato in todos_candidatos:
        # Filtra apenas candidatos que já tomaram posse (têm data_posse)
        if candidato['data_posse']:
            id_edital = candidato['id_edital']
            nome_cargo = candidato['nome_cargo']
            candidatos_agrupados[id_edital][nome_cargo].append(candidato)

    # Busca as opções dinâmicas necessárias
    opcoes_reitor = Opcao.get_por_tipo('reitor')
    opcoes_unidade = Opcao.get_por_tipo('unidade')

    return render_template(
        'termo_apresentacao.html', # Novo template
        nome=session.get('nome'),
        editais=editais,
        candidatos_por_edital_agrupado=candidatos_agrupados,
        opcoes_reitor=opcoes_reitor,
        opcoes_unidade=opcoes_unidade
    )

@certificado_bp.route('/gerar_apresentacao', methods=['POST'])
def gerar_apresentacao():
    """Gera um Termo de Apresentação individual."""
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    try:
        id_candidato = request.form.get('id_candidato')
        reitor = request.form.get('reitor')
        unidade = request.form.get('unidade')
        template_selecionado = 'modeloapresentacao.docx' # Template fixo

        # Validação
        if not id_candidato or not reitor or not unidade:
            flash('Todos os campos são obrigatórios.', 'error')
            return redirect(url_for('certificado.painel_apresentacao'))

        # Busca dados do candidato (incluindo data_posse, cargo, nivel)
        candidato = Candidato.get_by_id(id_candidato)
        if not candidato or not candidato['data_posse']:
            flash('Candidato não encontrado ou sem data de posse.', 'error')
            return redirect(url_for('certificado.painel_apresentacao'))

        # Formata a data de posse
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
        data_posse_obj = datetime.strptime(candidato['data_posse'], '%Y-%m-%d')
        data_formatada = data_posse_obj.strftime('%d/%m/%Y')

        context = {
            'data': data_formatada,
            'unidade': unidade,
            'nome': candidato['nome'],
            'cargo': candidato['nome_cargo'],
            'nivel': candidato['padrao_vencimento'],
            'reitor': reitor
        }

        doc = DocxTemplate(f'gama/docx_templates/{template_selecionado}')
        doc.render(context)

        file_stream = io.BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)

        # (Opcional) Você pode querer registrar este documento na tabela Certificado também
        # Certificado.create(
        #     nome_template=template_selecionado,
        #     id_candidato=id_candidato,
        #     id_usuario_emissor=session['usuario_id']
        # )

        return send_file(
            file_stream,
            as_attachment=True,
            download_name=f'Termo de Apresentação - {candidato["nome"]}.docx',
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    except Exception as e:
        flash(f'Ocorreu um erro ao gerar o documento: {e}', 'error')
        print(f"ERRO: {e}")
        return redirect(url_for('certificado.painel_apresentacao'))

@certificado_bp.route('/gerar_apresentacao_lote', methods=['POST'])
def gerar_apresentacao_lote():
    """Gera Termos de Apresentação em lote a partir de um XLSX."""
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    if 'planilha' not in request.files or request.files['planilha'].filename == '':
        flash('Nenhum arquivo de planilha enviado.', 'error')
        return redirect(url_for('certificado.painel_apresentacao'))

    planilha = request.files['planilha']
    if not planilha.filename.endswith('.xlsx'):
        flash('Formato de arquivo inválido. Por favor, envie um arquivo .xlsx', 'error')
        return redirect(url_for('certificado.painel_apresentacao'))

    try:
        df = pd.read_excel(planilha, dtype=str) # Lê tudo como string para evitar problemas
        
        required_cols = ['nome', 'cargo', 'nivel', 'data_posse', 'unidade', 'reitor']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            flash(f"Erro na planilha: Coluna(s) não encontrada(s): {', '.join(missing_cols)}.", 'error')
            return redirect(url_for('certificado.painel_apresentacao'))

        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for index, row in df.iterrows():
                
                # Formata a data de posse
                try:
                    data_posse_obj = pd.to_datetime(row['data_posse'])
                    data_formatada = data_posse_obj.strftime('%d/%m/%Y')
                except Exception:
                    data_formatada = row['data_posse'] # Usa o texto original se falhar

                context = {
                    'data': data_formatada,
                    'unidade': row['unidade'],
                    'nome': row['nome'],
                    'cargo': row['cargo'],
                    'nivel': row['nivel'],
                    'reitor': row['reitor']
                }

                doc = DocxTemplate('gama/docx_templates/modeloapresentacao.docx')
                doc.render(context)
                
                nome_arquivo_saida = f"Termo de Apresentação - {row['nome']}.docx"

                docx_buffer = io.BytesIO()
                doc.save(docx_buffer)
                docx_buffer.seek(0)
                
                zip_file.writestr(nome_arquivo_saida, docx_buffer.read())
        
        zip_buffer.seek(0)
        
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name='Termos_de_Apresentacao_Lote.zip',
            mimetype='application/zip'
        )

    except Exception as e:
        flash(f'Ocorreu um erro ao processar a planilha: {e}', 'error')
        print(f"ERRO NO LOTE: {e}")
        return redirect(url_for('certificado.painel_apresentacao'))