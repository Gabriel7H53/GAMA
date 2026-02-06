from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from gama.models.configuracao import Opcao

config_bp = Blueprint('config', __name__, template_folder='../templates')

@config_bp.route('/gerenciar_opcoes', methods=['GET', 'POST'])
def gerenciar_opcoes():
    if 'usuario_id' not in session or session.get('tipo') != 'administrador':
        flash('Acesso negado.', 'error')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        tipo_opcao = request.form.get('tipo_opcao')
        valor_opcao = request.form.get('valor_opcao')

        if not tipo_opcao or not valor_opcao:
            flash('Tipo ou valor da opção não podem ser vazios.', 'error')
        else:
            success, message = Opcao.create(tipo_opcao, valor_opcao)
            flash(message, 'success' if success else 'error')
        
        return redirect(url_for('config.gerenciar_opcoes'))

    try:
        opcoes_reitor = Opcao.get_por_tipo('reitor')
        opcoes_local = Opcao.get_por_tipo('local')
        opcoes_unidade = Opcao.get_por_tipo('unidade') 
    except Exception as e:
        flash(f'Erro ao carregar opções: {e}', 'error')
        opcoes_reitor = []
        opcoes_local = []
        opcoes_unidade = []

    return render_template(
        'config_opcoes.html', 
        nome=session.get('nome'),
        opcoes_reitor=opcoes_reitor,
        opcoes_local=opcoes_local,
        opcoes_unidade=opcoes_unidade 
    )

@config_bp.route('/remover_opcao/<int:id_opcao>', methods=['POST'])
def remover_opcao(id_opcao):
    if 'usuario_id' not in session or session.get('tipo') != 'administrador':
        flash('Acesso negado.', 'error')
        return redirect(url_for('auth.login'))

    success, message = Opcao.delete(id_opcao)
    flash(message, 'success' if success else 'error')
    
    return redirect(url_for('config.gerenciar_opcoes'))

@config_bp.route('/set_default/<int:id_opcao>', methods=['POST'])
def set_default(id_opcao):
    """Define uma opção como padrão."""
    if 'usuario_id' not in session or session.get('tipo') != 'administrador':
        flash('Acesso negado.', 'error')
        return redirect(url_for('auth.login'))

    success, message = Opcao.set_default(id_opcao)
    flash(message, 'success' if success else 'error')
    
    return redirect(url_for('config.gerenciar_opcoes'))
