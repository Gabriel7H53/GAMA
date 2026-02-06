from flask import Blueprint, render_template, session, redirect, url_for

admin_bp = Blueprint('admin', __name__, template_folder='../templates')

@admin_bp.route('/painel_admin')
def painel_admin():
    if 'usuario_id' not in session or session['tipo'] != 'administrador':
        return redirect(url_for('auth.login'))
    return render_template('painel_admin.html', nome=session['nome'])


