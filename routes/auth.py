"""
routes/auth.py
══════════════════════════════════════════════════════════════════
Blueprint de autenticación: login y logout.
Usa Flask-Login para gestionar la sesión del usuario.
══════════════════════════════════════════════════════════════════
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from db import user_store

auth_bp = Blueprint('auth', __name__)


# ──────────────────────────────────────────────
# Clase User para Flask-Login
# ──────────────────────────────────────────────
class User:
    """
    Wrapper sobre el dict de usuario de la BD para que Flask-Login
    pueda manejarlo como objeto.
    """
    def __init__(self, data: dict):
        self.id        = data['id']
        self.username  = data['username']
        self.email     = data['email']
        self.full_name = data['full_name']
        self.role      = data['role']
        self.is_active_flag = data.get('is_active', True)

    # — Propiedades requeridas por Flask-Login —
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return bool(self.is_active_flag)

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def is_admin(self):
        return self.role == 'admin'


# ──────────────────────────────────────────────
# Rutas
# ──────────────────────────────────────────────
@auth_bp.route('/login', methods=['GET'])
def login():
    """Renderiza la pantalla de login."""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))
    return render_template('login.html')


@auth_bp.route('/login', methods=['POST'])
def login_post():
    """Procesa el formulario de login."""
    username = request.form.get('username', '').strip().lower()
    password = request.form.get('password', '').strip()
    remember = request.form.get('remember') == 'on'

    if not username or not password:
        flash('Por favor ingresa usuario y contraseña.', 'error')
        return redirect(url_for('auth.login'))

    # Buscar usuario en la BD
    user_data = user_store.get_user_by_username(username)

    if not user_data:
        flash('Usuario o contraseña incorrectos.', 'error')
        return redirect(url_for('auth.login'))

    if not user_data.get('is_active', False):
        flash('Tu cuenta está desactivada. Contacta al administrador.', 'error')
        return redirect(url_for('auth.login'))

    if not user_store.check_password(password, user_data['password']):
        flash('Usuario o contraseña incorrectos.', 'error')
        return redirect(url_for('auth.login'))

    # Login exitoso
    user_obj = User(user_data)
    login_user(user_obj, remember=remember)
    user_store.update_last_login(user_data['id'])

    # Redirigir a la página que intentaba visitar (o al dashboard)
    next_page = request.args.get('next')
    if next_page and next_page.startswith('/'):
        return redirect(next_page)
    return redirect(url_for('dashboard.index'))


@auth_bp.route('/logout')
@login_required
def logout():
    """Cierra la sesión del usuario."""
    logout_user()
    flash('Has cerrado sesión correctamente.', 'success')
    return redirect(url_for('auth.login'))
