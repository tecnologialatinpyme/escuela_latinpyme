from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from services import WhatsAppService

campaigns_bp = Blueprint('campaigns', __name__)
whatsapp_service = WhatsAppService()

@campaigns_bp.route('/')
@login_required
def index():
    """Renderiza el panel de campañas."""
    return render_template('campaigns.html')

@campaigns_bp.route('/api/templates', methods=['GET'])
@login_required
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
@login_required
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


@campaigns_bp.route('/api/crear_plantilla', methods=['POST'])
@login_required
def crear_plantilla():
    """
    Envía una nueva plantilla de WhatsApp a Meta para su proceso de revisión y aprobación.
    """
    data = request.get_json(silent=True) or {}
    nombre = data.get("nombre", "").strip()
    categoria = data.get("categoria", "UTILITY").strip()
    texto_body = data.get("texto_body", "").strip()

    if not nombre or not texto_body:
        return jsonify({"exito": False, "error": "El nombre y el texto del cuerpo son obligatorios."}), 400

    try:
        res = whatsapp_service.crear_plantilla(
            nombre=nombre,
            categoria=categoria,
            texto_body=texto_body
        )
        return jsonify(res)
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500

