from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from werkzeug.security import generate_password_hash

edital_bp = Blueprint('edital', __name__, template_folder='../templates')

@edital_bp.route('/painel_edital')
def painel_edital():
    return render_template('edital.html', nome=session.get('nome'))
