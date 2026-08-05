import uuid
from flask import Blueprint, render_template, request, jsonify

business_bp = Blueprint('business', __name__)

# ──────────────────────────────────────────────
# Almacenamiento en memoria — Pipeline CRM
# Etapas: Prospecto → Calificado → Propuesta → Cerrado
# ──────────────────────────────────────────────
deals_store = [
    {
        "id": str(uuid.uuid4()),
        "company": "Grupo Empresarial Andino",
        "contact": "Andrés Mendoza",
        "phone": "+573144187269",
        "value": 8500000,
        "stage": "Propuesta",
        "days": 12,
        "program": "Diplomado en Liderazgo"
    },
    {
        "id": str(uuid.uuid4()),
        "company": "Constructora Diamante S.A.S",
        "contact": "Diana Duarte",
        "phone": "+573105584725",
        "value": 4200000,
        "stage": "Calificado",
        "days": 5,
        "program": "Gestión del Talento"
    },
    {
        "id": str(uuid.uuid4()),
        "company": "Tesorería Nacional Ltda.",
        "contact": "Carlos Restrepo",
        "phone": "+573215896325",
        "value": 6100000,
        "stage": "Prospecto",
        "days": 2,
        "program": "Finanzas Corporativas"
    },
    {
        "id": str(uuid.uuid4()),
        "company": "Inversiones Bolívar",
        "contact": "Marcela Torres",
        "phone": "+573001234567",
        "value": 12000000,
        "stage": "Cerrado",
        "days": 30,
        "program": "Diplomado en Liderazgo"
    },
    {
        "id": str(uuid.uuid4()),
        "company": "Logística Express Caribe",
        "contact": "Felipe Herrera",
        "phone": "+573009876543",
        "value": 5500000,
        "stage": "Calificado",
        "days": 8,
        "program": "Marketing Digital B2B"
    },
    {
        "id": str(uuid.uuid4()),
        "company": "Aceros del Pacífico",
        "contact": "Laura Gómez",
        "phone": "+573112233445",
        "value": 9800000,
        "stage": "Cerrado",
        "days": 45,
        "program": "Finanzas Corporativas"
    },
]

VALID_STAGES = ["Prospecto", "Calificado", "Propuesta", "Cerrado"]


# ──────────────────────────────────────────────
# Página principal — CRM Kanban
# ──────────────────────────────────────────────
@business_bp.route('/')
def index():
    """Renderiza el CRM de Negocios."""
    return render_template('business.html')


# ──────────────────────────────────────────────
# API — Listar todas las oportunidades
# ──────────────────────────────────────────────
@business_bp.route('/api/deals', methods=['GET'])
def api_get_deals():
    """Retorna todas las oportunidades del pipeline."""
    return jsonify(deals_store)


# ──────────────────────────────────────────────
# API — Agregar nueva oportunidad
# ──────────────────────────────────────────────
@business_bp.route('/api/deals', methods=['POST'])
def api_add_deal():
    """Agrega una nueva oportunidad al pipeline."""
    data = request.get_json(silent=True) or {}

    required = ['company', 'contact', 'value', 'stage', 'program']
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"Campo requerido: {field}"}), 400

    if data['stage'] not in VALID_STAGES:
        return jsonify({"error": f"Etapa inválida. Usar: {VALID_STAGES}"}), 400

    new_deal = {
        "id": str(uuid.uuid4()),
        "company": data['company'],
        "contact": data['contact'],
        "phone": data.get('phone', ''),
        "value": int(data['value']),
        "stage": data['stage'],
        "days": 0,
        "program": data['program']
    }
    deals_store.append(new_deal)
    return jsonify(new_deal), 201


# ──────────────────────────────────────────────
# API — Actualizar etapa (mover en el kanban)
# ──────────────────────────────────────────────
@business_bp.route('/api/deals/<deal_id>', methods=['PATCH'])
def api_update_deal(deal_id):
    """Actualiza la etapa o campos de una oportunidad."""
    data = request.get_json(silent=True) or {}
    for deal in deals_store:
        if deal['id'] == deal_id:
            if 'stage' in data:
                if data['stage'] not in VALID_STAGES:
                    return jsonify({"error": "Etapa inválida"}), 400
                deal['stage'] = data['stage']
            if 'value' in data:
                deal['value'] = int(data['value'])
            if 'contact' in data:
                deal['contact'] = data['contact']
            return jsonify(deal), 200
    return jsonify({"error": "Oportunidad no encontrada"}), 404


# ──────────────────────────────────────────────
# API — Eliminar oportunidad
# ──────────────────────────────────────────────
@business_bp.route('/api/deals/<deal_id>', methods=['DELETE'])
def api_delete_deal(deal_id):
    """Elimina una oportunidad del pipeline."""
    global deals_store
    original_len = len(deals_store)
    deals_store = [d for d in deals_store if d['id'] != deal_id]
    if len(deals_store) < original_len:
        return jsonify({"status": "deleted"}), 200
    return jsonify({"error": "Oportunidad no encontrada"}), 404
