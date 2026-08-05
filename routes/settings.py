from flask import Blueprint, render_template, request, jsonify
from config.settings import get_config, save_config

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/')
def index():
    """Renderiza el panel de configuraciones."""
    return render_template('settings.html')

@settings_bp.route('/api/get', methods=['GET'])
def api_get():
    """Retorna la configuración actual en JSON."""
    return jsonify(get_config())

@settings_bp.route('/api/save', methods=['POST'])
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
