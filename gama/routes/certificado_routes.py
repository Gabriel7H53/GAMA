from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from gama.models.edital import Edital
from gama.models.candidato import Candidato
from gama.models.certificado import Certificado
from collections import defaultdict # Importe esta linha
import io
import locale
from datetime import datetime
from docxtpl import DocxTemplate
from flask import send_file
import pandas as pd
import zipfile

certificado_bp = Blueprint('certificado', __name__, template_folder='../templates')

@certificado_bp.route('/painel')
def painel_certificados():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    # 1. Buscar todos os editais
    editais = Edital.get_all()
    
    # 2. Agrupar candidatos por edital e depois por cargo
    candidatos_agrupados = defaultdict(lambda: defaultdict(list))
    todos_candidatos = Candidato.get_all_with_details()

    for candidato in todos_candidatos:
        id_edital = candidato['id_edital']
        nome_cargo = candidato['nome_cargo']
        candidatos_agrupados[id_edital][nome_cargo].append(candidato)

    # 3. Buscar o histórico de certificados já emitidos
    certificados_emitidos = Certificado.get_all()

    return render_template(
        'certificados.html',
        nome=session.get('nome'),
        editais=editais,
        candidatos_por_edital_agrupado=candidatos_agrupados,
        certificados_emitidos=certificados_emitidos
    )

@certificado_bp.route('/painel_declaracoes')
def painel_declaracoes():
    return render_template('painel_declaracoes.html', nome=session.get('nome'))

# A rota para gerar o DOCX virá aqui no futuro
@certificado_bp.route('/gerar', methods=['POST'])
def gerar_certificado():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    try:
        # 1. Obter dados do formulário
        id_candidato = request.form.get('id_candidato')
        template_selecionado = request.form.get('template_selecionado')
        data_nomeacao_str = request.form.get('data')
        data_emissao_str = request.form.get('data_1')

        # --- BLOCO DE VALIDAÇÃO ADICIONADO ---
        # Verifica se algum dos campos obrigatórios (especialmente as datas) está vazio
        campos_obrigatorios = {
            'Candidato': id_candidato,
            'Template': template_selecionado,
            'Data de Nomeação': data_nomeacao_str,
            'Data de Emissão': data_emissao_str,
            'Portaria': request.form.get('portaria'),
            # Adicione outros campos que você considera essenciais aqui
        }
        
        for nome_campo, valor in campos_obrigatorios.items():
            if not valor:
                flash(f'O campo "{nome_campo}" é obrigatório e não foi preenchido.', 'error')
                return redirect(url_for('certificado.painel_certificados'))
        # --- FIM DO BLOCO DE VALIDAÇÃO ---

        # 2. Obter dados do banco
        candidato = Candidato.get_by_id(id_candidato)
        if not candidato:
            flash('Candidato não encontrado.', 'error')
            return redirect(url_for('certificado.painel_certificados'))

        # 3. Formatar as datas (agora temos certeza que não são nulas)
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
        data_nomeacao_obj = datetime.strptime(data_nomeacao_str, '%Y-%m-%d')
        data_emissao_obj = datetime.strptime(data_emissao_str, '%Y-%m-%d')
        
        data_nomeacao_extenso = data_nomeacao_obj.strftime('%d de %B de %Y')
        data_emissao_extenso = data_emissao_obj.strftime('%d de %B de %Y')

        # 4. Criar o dicionário de contexto
        context = {
            'nome': candidato['nome'],
            'cargo': candidato['nome_cargo'],
            'data': data_nomeacao_extenso,
            'portaria': request.form.get('portaria'),
            'dou': request.form.get('dou'),
            'carga_horaria': request.form.get('carga_horaria'),
            'lotacao': request.form.get('lotacao'),
            'origem': request.form.get('origem'),
            'codigo_vaga': request.form.get('codigo_vaga'),
            'data_1': data_emissao_extenso,
        }

        # 5. Processar o template .docx
        doc = DocxTemplate(f'gama/docx_templates/{template_selecionado}')
        doc.render(context)

        # 6. Salvar o documento em memória
        file_stream = io.BytesIO()
        doc.save(file_stream)
        file_stream.seek(0)

        # 7. Registrar a emissão no banco
        Certificado.create(
            nome_template=template_selecionado,
            id_candidato=id_candidato,
            id_usuario_emissor=session['usuario_id']
        )

        # 8. Enviar o arquivo para download
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
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Itera sobre cada linha da planilha
            for index, row in df.iterrows():
                data_nomeacao_extenso = row['data'].strftime('%d de %B de %Y')
                data_emissao_extenso = row['data_1'].strftime('%d de %B de %Y')

                context = {
                    'nome': row['nome'],
                    'cargo': row['cargo'],
                    'data': data_nomeacao_extenso,
                    'portaria': row['portaria'],
                    'dou': row['dou'],
                    'carga_horaria': row['carga_horaria'],
                    'lotacao': row['lotacao'],
                    'origem': row['origem'],
                    'codigo_vaga': row['codigo_vaga'],
                    'data_1': data_emissao_extenso,
                }

                doc = DocxTemplate('gama/docx_templates/modeloposse.docx')
                doc.render(context)
                
                # Define o nome do arquivo .docx de saída
                nome_arquivo_saida = f"Termo de Posse - {row['nome']}.docx"

                # Salva o .docx diretamente em um buffer de memória
                docx_buffer = io.BytesIO()
                doc.save(docx_buffer)
                docx_buffer.seek(0)
                
                # Adiciona o .docx em memória ao arquivo .zip
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