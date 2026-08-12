from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from db import database as db
from config.settings import app_config

ai_assistant_bp = Blueprint('ai_assistant', __name__)


# ──────────────────────────────────────────────
# Página principal del módulo
# ──────────────────────────────────────────────
@ai_assistant_bp.route('/')
@login_required
def index():
    """Renderiza el panel del Asistente IA."""
    return render_template('ai_assistant.html')


# ──────────────────────────────────────────────
# API — Listar todos los prompts
# ──────────────────────────────────────────────
@ai_assistant_bp.route('/api/prompts', methods=['GET'])
@login_required
def api_get_prompts():
    """Retorna todos los prompts de aulas configurados."""
    prompts = db.get_ai_prompts()
    return jsonify({'prompts': prompts})


# ──────────────────────────────────────────────
# API — Guardar / actualizar prompt
# ──────────────────────────────────────────────
@ai_assistant_bp.route('/api/prompts/save', methods=['POST'])
@login_required
def api_save_prompt():
    """Guarda o actualiza el prompt para un aula."""
    data = request.get_json(silent=True) or {}
    aula_id     = str(data.get('aula_id', '')).strip()
    aula_nombre = data.get('aula_nombre', '').strip()
    prompt      = data.get('prompt', '').strip()
    activo      = data.get('activo', True)

    if not aula_id or not aula_nombre or not prompt:
        return jsonify({'exito': False, 'error': 'Faltan campos: aula_id, aula_nombre o prompt'}), 400

    ok = db.save_ai_prompt(aula_id, aula_nombre, prompt, activo)
    if ok:
        return jsonify({'exito': True, 'mensaje': f'Prompt para "{aula_nombre}" guardado correctamente.'})
    return jsonify({'exito': False, 'error': 'Error al guardar en la base de datos.'}), 500


# ──────────────────────────────────────────────
# API — Eliminar prompt
# ──────────────────────────────────────────────
@ai_assistant_bp.route('/api/prompts/<aula_id>', methods=['DELETE'])
@login_required
def api_delete_prompt(aula_id):
    """Elimina el prompt de un aula."""
    ok = db.delete_ai_prompt(aula_id)
    if ok:
        return jsonify({'exito': True, 'mensaje': 'Prompt eliminado.'})
    return jsonify({'exito': False, 'error': 'Error al eliminar.'}), 500


# ──────────────────────────────────────────────
# API — Toggle activo/inactivo
# ──────────────────────────────────────────────
@ai_assistant_bp.route('/api/prompts/<aula_id>/toggle', methods=['POST'])
@login_required
def api_toggle_prompt(aula_id):
    """Activa o desactiva el prompt de un aula."""
    data   = request.get_json(silent=True) or {}
    activo = data.get('activo', True)
    ok = db.toggle_ai_prompt(aula_id, activo)
    if ok:
        estado = 'activado' if activo else 'desactivado'
        return jsonify({'exito': True, 'mensaje': f'Prompt {estado}.'})
    return jsonify({'exito': False, 'error': 'Error al actualizar estado.'}), 500


# ──────────────────────────────────────────────
# API — Lookup: buscar aula por teléfono
# ──────────────────────────────────────────────
@ai_assistant_bp.route('/api/aula-lookup', methods=['GET'])
@login_required
def api_aula_lookup():
    """
    Busca el aula de un usuario por su número de teléfono.
    Útil para debug y para pre-cargar datos en el simulador.
    """
    from services.ai_assistant_service import AiAssistantService
    telefono = request.args.get('telefono', '').strip()
    if not telefono:
        return jsonify({'error': 'Falta el parámetro telefono'}), 400

    svc = AiAssistantService()
    resultado = svc.buscar_aula_por_telefono(telefono)
    return jsonify(resultado)


# ──────────────────────────────────────────────
# API — Probar la IA con teléfono + mensaje
# ──────────────────────────────────────────────
@ai_assistant_bp.route('/api/test', methods=['POST'])
@login_required
def api_test_ia():
    """
    Prueba el Asistente IA con un número de teléfono y un mensaje.
    No envía nada por WhatsApp — solo genera y devuelve la respuesta.
    """
    from services.ai_assistant_service import AiAssistantService
    data     = request.get_json(silent=True) or {}
    telefono = data.get('telefono', '').strip()
    mensaje  = data.get('mensaje', '').strip()

    if not telefono or not mensaje:
        return jsonify({'exito': False, 'error': 'Faltan campos: telefono o mensaje'}), 400

    svc = AiAssistantService()
    # Construir un historial ficticio con solo ese mensaje
    mensajes_prueba = [{'direction': 'in', 'body': mensaje}]
    resultado = svc.generar_respuesta(telefono, mensajes_prueba)
    return jsonify(resultado)


# ──────────────────────────────────────────────
# API — Obtener / guardar configuración global de IA
# ──────────────────────────────────────────────
@ai_assistant_bp.route('/api/config', methods=['GET'])
@login_required
def api_get_config():
    """Retorna la configuración actual del Asistente IA."""
    from config.settings import get_config
    cfg = get_config()
    return jsonify({
        'ai_assistant_enabled': cfg.get('AI_ASSISTANT_ENABLED', 'true'),
        'ai_auto_reply':        cfg.get('AI_AUTO_REPLY', 'true'),
        'ai_default_prompt':    cfg.get('AI_DEFAULT_PROMPT', ''),
        'aulas_api_url':        cfg.get('AULAS_API_URL', ''),
        'aulas_api_token':      cfg.get('AULAS_API_TOKEN', ''),
        'openai_model':         cfg.get('OPENAI_MODEL', 'gpt-4o-mini'),
    })


@ai_assistant_bp.route('/api/config', methods=['POST'])
@login_required
def api_save_config():
    """Guarda la configuración global del Asistente IA."""
    from config.settings import save_config
    data = request.get_json(silent=True) or {}
    # Mapear claves del frontend a claves del config
    config_map = {
        'ai_assistant_enabled': 'AI_ASSISTANT_ENABLED',
        'ai_auto_reply':        'AI_AUTO_REPLY',
        'ai_default_prompt':    'AI_DEFAULT_PROMPT',
        'aulas_api_url':        'AULAS_API_URL',
        'aulas_api_token':      'AULAS_API_TOKEN',
        'openai_model':         'OPENAI_MODEL',
    }
    payload = {}
    for frontend_key, config_key in config_map.items():
        if frontend_key in data:
            payload[config_key] = data[frontend_key]

    ok = save_config(payload)
    if ok:
        return jsonify({'exito': True, 'mensaje': 'Configuración guardada.'})
    return jsonify({'exito': False, 'error': 'Error al guardar configuración.'}), 500
