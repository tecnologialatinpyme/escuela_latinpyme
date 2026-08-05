from flask import Blueprint, render_template, request, jsonify
from services import WhatsAppService

campaigns_bp = Blueprint('campaigns', __name__)
whatsapp_service = WhatsAppService()

@campaigns_bp.route('/')
def index():
    """Renderiza el panel de campañas."""
    return render_template('campaigns.html')

@campaigns_bp.route('/api/templates', methods=['GET'])
def get_templates():
    """
    Recupera las plantillas de Meta WhatsApp Cloud (reales o simuladas).
    """
    try:
        templates = whatsapp_service.obtener_plantillas()
        return jsonify({"exito": True, "templates": templates})
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500

@campaigns_bp.route('/api/enviar_individual', methods=['POST'])
def enviar_individual():
    """
    Envía una plantilla de WhatsApp a un destinatario individual.
    Facilita que el frontend controle la barra de progreso paso a paso.
    """
    datos = request.get_json()
    if not datos:
        return jsonify({"exito": False, "error": "Parámetros inválidos"}), 400

    telefono = datos.get("telefono")
    plantilla_nombre = datos.get("plantilla_nombre")
    parametros = datos.get("parametros", [])

    if not telefono or not plantilla_nombre:
        return jsonify({"exito": False, "error": "Teléfono y nombre de plantilla son requeridos."}), 400

    try:
        # Llamar al servicio oficial de WhatsApp de Meta
        res = whatsapp_service.enviar_mensaje_plantilla(
            telefono=telefono,
            plantilla_nombre=plantilla_nombre,
            parametros=parametros
        )
        return jsonify(res)
    except Exception as e:
        return jsonify({"exito": False, "error": f"Error interno del servidor: {str(e)}"}), 500
