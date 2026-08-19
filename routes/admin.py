from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, Response
from flask_login import login_required, current_user
from db import user_store, database as db
import json
from functools import wraps

admin_bp = Blueprint('admin', __name__)


# ──────────────────────────────────────────────
# Decorador: solo admins
# ──────────────────────────────────────────────
def admin_required(f):
    """Decorador que bloquea el acceso a usuarios no admins."""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not current_user.is_admin():
            flash('Acceso restringido. Solo administradores.', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated


# ──────────────────────────────────────────────
# Rutas
# ──────────────────────────────────────────────
@admin_bp.route('/users')
@admin_required
def users():
    """Panel principal: lista de todos los usuarios."""
    all_users = user_store.list_users()
    return render_template('admin_users.html', users=all_users)


@admin_bp.route('/users/create', methods=['POST'])
@admin_required
def create_user():
    """Crea un nuevo usuario."""
    username  = request.form.get('username', '').strip().lower()
    email     = request.form.get('email', '').strip().lower()
    full_name = request.form.get('full_name', '').strip()
    role      = request.form.get('role', 'asesor')
    password  = request.form.get('password', '').strip()

    # Validaciones básicas
    if not all([username, email, full_name, password]):
        flash('Todos los campos son obligatorios.', 'error')
        return redirect(url_for('admin.users'))

    if role not in ('admin', 'asesor'):
        role = 'asesor'

    result = user_store.create_user(username, email, password, full_name, role)

    if result:
        flash(f'Usuario "{username}" creado exitosamente.', 'success')
    else:
        flash(f'Error: el usuario o email "{username}" ya existe.', 'error')

    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/edit', methods=['POST'])
@admin_required
def edit_user(user_id: int):
    """Edita nombre, email o rol de un usuario."""
    full_name = request.form.get('full_name', '').strip() or None
    email     = request.form.get('email', '').strip().lower() or None
    role      = request.form.get('role') or None

    if role and role not in ('admin', 'asesor'):
        role = None

    success = user_store.update_user(user_id, full_name=full_name, email=email, role=role)

    if success:
        flash('Usuario actualizado.', 'success')
    else:
        flash('Error actualizando el usuario.', 'error')

    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@admin_required
def toggle_user(user_id: int):
    """Activa o desactiva un usuario."""
    # Impedir desactivarse a sí mismo
    if user_id == current_user.id:
        flash('No puedes desactivar tu propia cuenta.', 'error')
        return redirect(url_for('admin.users'))

    new_state = user_store.toggle_user(user_id)
    if new_state is None:
        flash('Error cambiando el estado del usuario.', 'error')
    elif new_state:
        flash('Usuario activado.', 'success')
    else:
        flash('Usuario desactivado.', 'success')

    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id: int):
    """Realiza un borrado lógico (Soft Delete) en un usuario."""
    if user_id == current_user.id:
        flash('No puedes eliminar tu propia cuenta.', 'error')
        return redirect(url_for('admin.users'))

    success = user_store.delete_user(user_id)
    if success:
        flash('Usuario marcado como inactivo/eliminado (Soft Delete).', 'success')
    else:
        flash('Error al eliminar el usuario.', 'error')

    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def reset_password(user_id: int):
    """Genera una nueva contraseña temporal y la muestra al admin."""
    new_password = request.form.get('new_password', '').strip()

    if not new_password or len(new_password) < 6:
        flash('La contraseña debe tener al menos 6 caracteres.', 'error')
        return redirect(url_for('admin.users'))

    success = user_store.reset_password(user_id, new_password)

    if success:
        flash(f'Contraseña actualizada correctamente.', 'success')
    else:
        flash('Error actualizando la contraseña.', 'error')

    return redirect(url_for('admin.users'))


# ──────────────────────────────────────────────
# Exportación de Base de Datos para Migración
# ──────────────────────────────────────────────
@admin_bp.route('/database/export', methods=['GET'])
@admin_required
def export_database():
    """
    Ruta para exportar toda la base de datos en un archivo JSON estructurado para migración.
    """
    try:
        data = db.export_all_tables()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"latinpyme_database_export_{timestamp}.json"
        
        json_output = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        
        return Response(
            json_output,
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )
    except Exception as e:
        flash(f"Error exportando la base de datos: {e}", "error")
        return redirect(url_for('admin.users'))

