from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from config.settings import get_config, get_sanitized_config, save_config
from db import user_store

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/')
@login_required
def index():
    """Renderiza el panel de configuraciones."""
    return render_template('settings.html')

@settings_bp.route('/api/get', methods=['GET'])
@login_required
def api_get():
    """Retorna la configuración enmascarada (con estado de actividad de tokens/IDs)."""
    return jsonify(get_sanitized_config())


@settings_bp.route('/api/save', methods=['POST'])
@login_required
def api_save():
    """Guarda las nuevas configuraciones enviadas en el cuerpo POST."""
    new_data = request.get_json()
    if not new_data:
        return jsonify({"exito": False, "error": "Datos vacíos"}), 400
        
    exito = save_config(new_data)
    if exito:
        return jsonify({"exito": True, "mensaje": "Configuración guardada correctamente."})
    else:
        return jsonify({"exito": False, "error": "Error al guardar en el archivo config.json."}), 500

@settings_bp.route('/api/change-password', methods=['POST'])
@login_required
def change_password():
    """Permite al usuario autenticado cambiar su propia contraseña."""
    data = request.get_json()
    if not data:
        return jsonify({"exito": False, "error": "Datos inválidos"}), 400

    new_password = data.get('new_password', '').strip()
    if not new_password or len(new_password) < 6:
        return jsonify({"exito": False, "error": "La contraseña debe tener al menos 6 caracteres."}), 400

    success = user_store.reset_password(current_user.id, new_password)
    if success:
        return jsonify({"exito": True, "mensaje": "Contraseña actualizada correctamente."})
    else:
        return jsonify({"exito": False, "error": "Error al actualizar la contraseña."}), 500

