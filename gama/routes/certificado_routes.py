from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from gama.models.edital import Edital
from gama.models.candidato import Candidato
from gama.models.certificado import Certificado
from gama.models.configuracao import Opcao 
from collections import defaultdict, OrderedDict 
import io
import locale
from datetime import datetime
from docxtpl import DocxTemplate, RichText
from flask import send_file
import zipfile

certificado_bp = Blueprint('certificado', __name__, template_folder='../templates')

def numero_por_extenso(n):
    unidades = {
        1: 'um', 2: 'dois', 3: 'três', 4: 'quatro', 5: 'cinco',
        6: 'seis', 7: 'sete', 8: 'oito', 9: 'nove', 10: 'dez',
        11: 'onze', 12: 'doze', 13: 'treze', 14: 'catorze', 15: 'quinze',
        16: 'dezesseis', 17: 'dezessete', 18: 'dezoito', 19: 'dezenove'
    }
    dezenas = {
        20: 'vinte', 30: 'trinta'
    }
    
    texto_numero = ""

    if n in unidades:
        texto_numero = unidades[n]
    elif n in dezenas:
        texto_numero = dezenas[n]
    elif 20 < n < 30:
        texto_numero = f"vinte e {unidades[n-20]}"
    elif 30 < n <= 31:
        texto_numero = f"trinta e {unidades[n-30]}"
    else:
        return str(n)

    if n == 1:
        return "Ao primeiro dia do mês de"
    else:
        return f"Aos {texto_numero} dias do mês de"

def gerar_documentos_zip(candidato_id, reitor_nome, local_posse):
    """
    Busca um candidato e gera um ZIP com o Termo de Posse e o Termo de Apresentação.
    Retorna um (BytesIO, nome_arquivo) ou (None, None) em caso de erro.
    """
    candidato = Candidato.get_by_id(candidato_id)
    if not candidato:
        flash(f'Candidato com ID {candidato_id} não encontrado.', 'error')
        return None, None
        
    campos_obrigatorios = {
        'Data de Posse': candidato['data_posse'],
        'Portaria': candidato['portaria'],
        'Lotação (Unidade)': candidato['lotacao']
    }
    for nome_campo, valor in campos_obrigatorios.items():
        if not valor:
            flash(f'Não foi possível gerar: O candidato {candidato["nome"]} está com o campo "{nome_campo}" vazio.', 'error')
            return None, None

    try:
        locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
        
        data_posse_obj = datetime.strptime(candidato['data_posse'], '%Y-%m-%d')
        dia_extenso = numero_por_extenso(data_posse_obj.day)
        mes_extenso = data_posse_obj.strftime('%B')
        ano_extenso = data_posse_obj.strftime('%Y')
        
        context_posse = {
            'nome': candidato['nome'],
            'cargo': candidato['nome_cargo'],
            'nivel': candidato['padrao_vencimento'],
            'dia': dia_extenso,
            'mês': mes_extenso,
            'ano': ano_extenso,
            'local': local_posse, 
            'reitor': reitor_nome, 
            'portaria': candidato['portaria'],
            'dou': '', 
            'carga_horaria': '40', 
            'lotacao': candidato['lotacao'],
            'codigo_vaga': candidato['cod_vaga'],
            'data_1': data_posse_obj.strftime('%d de %B de %Y'),
        }
        doc_posse = DocxTemplate('gama/docx_templates/modeloposse.docx')
        doc_posse.render(context_posse)
        buffer_posse = io.BytesIO()
        doc_posse.save(buffer_posse)
        buffer_posse.seek(0)

        context_apresentacao = {
            'data': data_posse_obj.strftime('%d/%m/%Y'),
            'unidade': candidato['lotacao'], 
            'nome': candidato['nome'],
            'cargo': candidato['nome_cargo'],
            'nivel': candidato['padrao_vencimento'],
            'reitor': reitor_nome 
        }
        doc_apresentacao = DocxTemplate('gama/docx_templates/modeloapresentacao.docx')
        doc_apresentacao.render(context_apresentacao)
        buffer_apresentacao = io.BytesIO()
        doc_apresentacao.save(buffer_apresentacao)
        buffer_apresentacao.seek(0)
        
        Certificado.create(
            nome_template='Termos Unificados (Posse+Apresentação)',
            id_candidato=candidato_id,
            id_usuario_emissor=session['usuario_id']
        )
        
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            nome_posse = f'Termo_de_Posse - {candidato["nome"]}.docx'
            nome_apres = f'Termo_de_Apresentacao - {candidato["nome"]}.docx'
            zip_file.writestr(nome_posse, buffer_posse.read())
            zip_file.writestr(nome_apres, buffer_apresentacao.read())
        
        zip_buffer.seek(0)
        zip_filename = f'Documentos_Posse_{candidato["nome"]}.zip'
        
        return zip_buffer, zip_filename

    except Exception as e:
        flash(f'Erro ao gerar documentos para {candidato["nome"]}: {e}', 'error')
        print(f"ERRO: {e}")
        return None, None

@certificado_bp.route('/painel')
def painel_certificados():
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    editais = Edital.get_all()
    candidatos_agrupados = defaultdict(lambda: defaultdict(list))
    
    todos_candidatos_raw = Candidato.get_all_with_details() 
    candidatos_filtrados = [
        c for c in todos_candidatos_raw if c['situacao'] in ('nomeado', 'empossado')
    ]

    for candidato in candidatos_filtrados:
        id_edital = candidato['id_edital']
        nome_cargo = candidato['nome_cargo']
        candidatos_agrupados[id_edital][nome_cargo].append(candidato)

    certificados_emitidos = Certificado.get_all()
    opcoes_reitor = Opcao.get_por_tipo('reitor')
    opcoes_local = Opcao.get_por_tipo('local')

    default_reitor = next((r['valor_opcao'] for r in opcoes_reitor if r['is_default']), None)
    default_local = next((l['valor_opcao'] for l in opcoes_local if l['is_default']), None)

    return render_template(
        'certificados.html',
        nome=session.get('nome'),
        editais=editais,
        candidatos_por_edital_agrupado=candidatos_agrupados,
        certificados_emitidos=certificados_emitidos,
        opcoes_reitor=opcoes_reitor, 
        opcoes_local=opcoes_local,
        default_reitor=default_reitor,
        default_local=default_local
    )

@certificado_bp.route('/painel_declaracoes')
def painel_declaracoes():
    return render_template('painel_declaracoes.html', nome=session.get('nome'))

@certificado_bp.route('/gerar/individual/<int:id_candidato>', methods=['POST'])
def gerar_certificado_individual(id_candidato):
    """
    Gera um ZIP (Posse + Apresentação) para um único candidato.
    """
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    reitor = request.form.get('reitor')
    local = request.form.get('local')
    
    if not reitor or not local:
        flash('Reitor e Local são obrigatórios (Configure-os como Padrão na tela de Configurações).', 'error')
        return redirect(url_for('certificado.painel_certificados'))

    zip_buffer, zip_filename = gerar_documentos_zip(id_candidato, reitor, local)
    
    if zip_buffer:
        return send_file(
            zip_buffer,
            as_attachment=True,
            download_name=zip_filename,
            mimetype='application/zip'
        )
    else:
        return redirect(url_for('certificado.painel_certificados'))
    
@certificado_bp.route('/gerar/lote', methods=['POST'])
def gerar_certificado_lote():
    """
    Gera um ZIP contendo os ZIPs individuais de múltiplos candidatos selecionados.
    """
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    candidatos_ids = request.form.getlist('candidatos_ids')
    reitor = request.form.get('reitor')
    local = request.form.get('local')
    
    if not candidatos_ids:
        flash('Nenhum candidato selecionado.', 'error')
        return redirect(url_for('certificado.painel_certificados'))

    if not reitor or not local:
        flash('Reitor e Local são obrigatórios.', 'error')
        return redirect(url_for('certificado.painel_certificados'))

    master_zip_buffer = io.BytesIO()
    sucesso_count = 0
    erros = []

    try:
        with zipfile.ZipFile(master_zip_buffer, 'w', zipfile.ZIP_DEFLATED) as master_zip:
            for id_candidato in candidatos_ids:
                zip_buffer_individual, zip_filename = gerar_documentos_zip(id_candidato, reitor, local)
                
                if zip_buffer_individual:
                    master_zip.writestr(zip_filename, zip_buffer_individual.getvalue())
                    sucesso_count += 1
                else:
                    cand = Candidato.get_by_id(id_candidato)
                    nome_erro = cand['nome'] if cand else f"ID {id_candidato}"
                    erros.append(nome_erro)

        if sucesso_count == 0:
            flash('Não foi possível gerar nenhum documento. Verifique os dados dos candidatos (Data de Posse, etc).', 'error')
            return redirect(url_for('certificado.painel_certificados'))

        if erros:
            flash(f'Gerado com sucesso para {sucesso_count} candidatos. Erro ao gerar para: {", ".join(erros)}', 'warning')
        
        master_zip_buffer.seek(0)
        data_hoje = datetime.now().strftime('%Y-%m-%d')
        nome_arquivo_final = f'Lote_Termos_Posse_{data_hoje}.zip'

        return send_file(
            master_zip_buffer,
            as_attachment=True,
            download_name=nome_arquivo_final,
            mimetype='application/zip'
        )

    except Exception as e:
        flash(f'Erro fatal ao gerar lote: {e}', 'error')
        return redirect(url_for('certificado.painel_certificados'))

# ─────────────────────────────────────────────────────────────────────────────
# MÓDULO: Termo de Posse Coletivo
# ─────────────────────────────────────────────────────────────────────────────

@certificado_bp.route('/termo_coletivo')
def painel_termo_coletivo():
    """Exibe a tela de seleção de candidatos para o Termo de Posse Coletivo."""
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    editais = Edital.get_all()
    candidatos_agrupados = defaultdict(lambda: defaultdict(list))

    todos_candidatos_raw = Candidato.get_all_with_details()
    candidatos_filtrados = [
        c for c in todos_candidatos_raw if c['situacao'] in ('nomeado', 'empossado')
    ]

    for candidato in candidatos_filtrados:
        id_edital = candidato['id_edital']
        nome_cargo = candidato['nome_cargo']
        candidatos_agrupados[id_edital][nome_cargo].append(candidato)

    opcoes_reitor = Opcao.get_por_tipo('reitor')
    opcoes_local = Opcao.get_por_tipo('local')
    default_reitor = next((r['valor_opcao'] for r in opcoes_reitor if r['is_default']), None)
    default_local = next((l['valor_opcao'] for l in opcoes_local if l['is_default']), None)

    return render_template(
        'termo_coletivo.html',
        nome=session.get('nome'),
        editais=editais,
        candidatos_por_edital_agrupado=candidatos_agrupados,
        opcoes_reitor=opcoes_reitor,
        opcoes_local=opcoes_local,
        default_reitor=default_reitor,
        default_local=default_local
    )


@certificado_bp.route('/gerar/coletivo', methods=['POST'])
def gerar_termo_coletivo():
    """
    Gera o Termo de Posse Coletivo (.docx) para múltiplos candidatos selecionados.
    Todos os candidatos devem ter a mesma data de posse.
    """
    if 'usuario_id' not in session:
        return redirect(url_for('auth.login'))

    candidatos_ids = request.form.getlist('candidatos_ids')
    reitor = request.form.get('reitor', '').strip()
    local = request.form.get('local', '').strip()
    portaria = request.form.get('portaria', '').strip()

    # ── Validações básicas ────────────────────────────────────────────────────
    if not candidatos_ids:
        flash('Nenhum candidato selecionado.', 'error')
        return redirect(url_for('certificado.painel_termo_coletivo'))

    if not reitor or not local:
        flash('Reitor e Local padrão são obrigatórios. Configure-os em Configurações.', 'error')
        return redirect(url_for('certificado.painel_termo_coletivo'))

    if not portaria:
        flash('O campo Portaria é obrigatório para o Termo Coletivo.', 'error')
        return redirect(url_for('certificado.painel_termo_coletivo'))

    # ── Busca e valida os candidatos ──────────────────────────────────────────
    candidatos_dados = []
    for id_c in candidatos_ids:
        c = Candidato.get_by_id(id_c)
        if not c:
            flash(f'Candidato com ID {id_c} não encontrado.', 'error')
            return redirect(url_for('certificado.painel_termo_coletivo'))
        # Campos obrigatórios por candidato
        faltantes = []
        if not c.get('data_posse'):
            faltantes.append('Data de Posse')
        if not c.get('lotacao'):
            faltantes.append('Lotação')
        if faltantes:
            flash(
                f'Candidato "{c["nome"]}" está com campos obrigatórios vazios: '
                f'{", ".join(faltantes)}.',
                'error'
            )
            return redirect(url_for('certificado.painel_termo_coletivo'))
        c['_id'] = id_c
        candidatos_dados.append(c)

    # ── Valida que todos têm a mesma data de posse ────────────────────────────
    datas_unicas = set(c['data_posse'] for c in candidatos_dados)
    if len(datas_unicas) > 1:
        datas_fmt = ', '.join(
            datetime.strptime(d, '%Y-%m-%d').strftime('%d/%m/%Y') for d in sorted(datas_unicas)
        )
        flash(
            f'Não é possível gerar o Termo Coletivo: os candidatos selecionados possuem '
            f'datas de posse divergentes ({datas_fmt}). Todos devem ter a mesma data.',
            'error'
        )
        return redirect(url_for('certificado.painel_termo_coletivo'))

    # ── Formata a data por extenso ────────────────────────────────────────────
    try:
        try:
            locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
        except locale.Error:
            locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil.1252')

        data_posse_str = list(datas_unicas)[0]
        data_posse_obj = datetime.strptime(data_posse_str, '%Y-%m-%d')
        dia_extenso = numero_por_extenso(data_posse_obj.day)
        mes_extenso = data_posse_obj.strftime('%B')
        ano_extenso = data_posse_obj.strftime('%Y')
        data_nome_arquivo = data_posse_obj.strftime('%d-%m-%Y')
    except Exception as e:
        flash(f'Erro ao processar a data de posse: {e}', 'error')
        return redirect(url_for('certificado.painel_termo_coletivo'))

    # ── Agrupa candidatos por cargo (mantendo ordem de inserção) ──────────────
    grupos_cargos = OrderedDict()
    for c in candidatos_dados:
        cargo_nome = c['nome_cargo'].upper()
        if cargo_nome not in grupos_cargos:
            grupos_cargos[cargo_nome] = []
        grupos_cargos[cargo_nome].append(c)

    # ── Monta estrutura de grupos para o template ─────────────────────────────
    # Cada grupo: "- NOME DO CARGO:" seguido de candidatos separados por uma linha
    # Pontuação: ";" entre candidatos do mesmo cargo, "." no último de cada grupo
    grupos_template = OrderedDict()
    rt = RichText()
    total_grupos = len(grupos_cargos)

    for idx_grupo, (cargo_nome, lista_cands) in enumerate(grupos_cargos.items()):
        total_cands = len(lista_cands)
        cands_formatados = []
        rt.add(f'- {cargo_nome}:\n\n', bold=True)

        for idx_cand, cand in enumerate(lista_cands):
            eh_ultimo = (idx_cand == total_cands - 1)
            pontuacao = '.' if eh_ultimo else ';'
            cands_formatados.append({
                'nome': cand['nome'],
                'lotacao': cand['lotacao'],
                'pontuacao': pontuacao
            })
            rt.add('- ')
            rt.add(f'{cand["nome"]}', bold=True)
            rt.add(f', com lotação na {cand["lotacao"]}{pontuacao}')
            if not (eh_ultimo and idx_grupo == total_grupos - 1):
                rt.add('\n\n')

        grupos_template[cargo_nome] = cands_formatados

    # ── Renderiza o template Word ─────────────────────────────────────────────
    try:
        context = {
            'dia': dia_extenso,
            'mês': mes_extenso,
            'ano': ano_extenso,
            'local': local,
            'portaria': portaria,
            'reitor': reitor,
            'grupos': grupos_template,
            'corpo_empossados': rt,
        }

        doc = DocxTemplate('gama/docx_templates/modelocoletivo.docx')
        doc.render(context)

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        # ── Registra auditoria para cada candidato ────────────────────────────
        for cand in candidatos_dados:
            try:
                Certificado.create(
                    nome_template='Termo de Posse Coletivo',
                    id_candidato=cand['_id'],
                    id_usuario_emissor=session['usuario_id']
                )
            except Exception as e_audit:
                print(f'AVISO: Erro ao registrar auditoria para candidato {cand["nome"]}: {e_audit}')

        nome_arquivo = f'Termo_de_Posse_Coletivo_{data_nome_arquivo}.docx'

        return send_file(
            buffer,
            as_attachment=True,
            download_name=nome_arquivo,
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    except Exception as e:
        flash(f'Erro ao gerar o Termo de Posse Coletivo: {e}', 'error')
        print(f'ERRO gerar_termo_coletivo: {e}')
        return redirect(url_for('certificado.painel_termo_coletivo'))
