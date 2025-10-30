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


@certificado_bp.route('/painel')
def painel_certificados():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    editais = Edital.get_all()
    
    candidatos_agrupados = defaultdict(lambda: defaultdict(list))
    todos_candidatos = Candidato.get_all_with_details() 

    for candidato in todos_candidatos:
        id_edital = candidato['id_edital']
        nome_cargo = candidato['nome_cargo']
        candidatos_agrupados[id_edital][nome_cargo].append(candidato)

    certificados_emitidos = Certificado.get_all()
    
    # --- BUSCAR OPÇÕES DINÂMICAS ---
    opcoes_reitor = Opcao.get_por_tipo('reitor')
    opcoes_local = Opcao.get_por_tipo('local')
    # --- FIM DA BUSCA ---

    return render_template(
        'certificados.html',
        nome=session.get('nome'),
        editais=editais,
        candidatos_por_edital_agrupado=candidatos_agrupados,
        certificados_emitidos=certificados_emitidos,
        opcoes_reitor=opcoes_reitor, # Passa para o template
        opcoes_local=opcoes_local   # Passa para o template
    )

@certificado_bp.route('/painel_declaracoes')
def painel_declaracoes():
    return render_template('painel_declaracoes.html', nome=session.get('nome'))

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
        local = request.form.get('local')
        reitor = request.form.get('reitor')

        # --- BLOCO DE VALIDAÇÃO ---
        campos_obrigatorios = {
            'Candidato': id_candidato,
            'Template': template_selecionado,
            'Data de Nomeação': data_nomeacao_str,
            'Data de Emissão': data_emissao_str,
            'Portaria': request.form.get('portaria'),
            'Local': local,
            'Reitor': reitor
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

        # 3. Formatar as datas
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
        
        data_nomeacao_obj = datetime.strptime(data_nomeacao_str, '%Y-%m-%d')
        dia_extenso = numero_por_extenso(data_nomeacao_obj.day)
        mes_extenso = data_nomeacao_obj.strftime('%B')
        ano_extenso = data_nomeacao_obj.strftime('%Y')
        
        data_emissao_obj = datetime.strptime(data_emissao_str, '%Y-%m-%d')
        data_emissao_extenso = data_emissao_obj.strftime('%d de %B de %Y')

        # 4. Criar o dicionário de contexto (ATUALIZADO)
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
            'dou': '', # Removido
            'carga_horaria': request.form.get('carga_horaria'),
            'lotacao': request.form.get('lotacao'),
            # 'origem': request.form.get('origem'), # <-- REMOVIDO
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
        
        # --- VALIDAÇÃO DE COLUNAS ATUALIZADA ---
        # Removido 'origem' da lista de colunas necessárias
        required_cols = ['nivel', 'local', 'reitor', 'data', 'data_1', 'nome', 'cargo', 'portaria']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            flash(f"Erro na planilha: Coluna(s) não encontrada(s): {', '.join(missing_cols)}.", 'error')
            return redirect(url_for('certificado.painel_certificados'))
        
        if 'dou' in df.columns:
            flash("Aviso: A coluna 'dou' na planilha foi ignorada.", 'info')
        if 'origem' in df.columns:
            flash("Aviso: A coluna 'origem' na planilha foi ignorada.", 'info')

        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for index, row in df.iterrows():
                
                # --- LÓGICA DE DATA ---
                data_nomeacao_obj = row['data']
                dia_extenso = numero_por_extenso(data_nomeacao_obj.day)
                mes_extenso = data_nomeacao_obj.strftime('%B')
                ano_extenso = data_nomeacao_obj.strftime('%Y')
                
                data_emissao_obj = row['data_1']
                data_emissao_extenso = data_emissao_obj.strftime('%d de %B de %Y')

                # Dicionário de contexto (ATUALIZADO)
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
                    'dou': '', # Removido
                    'carga_horaria': row['carga_horaria'],
                    'lotacao': row['lotacao'],
                    # 'origem': row.get('origem', ''), # <-- REMOVIDO
                    'codigo_vaga': row['codigo_vaga'],
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