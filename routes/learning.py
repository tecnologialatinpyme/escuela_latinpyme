import uuid
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify

learning_bp = Blueprint('learning', __name__)

# ──────────────────────────────────────────────
# Almacenamiento en memoria — Cursos y Eventos
# ──────────────────────────────────────────────
courses_store = [
    {
        "id": str(uuid.uuid4()),
        "name": "Diplomado en Liderazgo Empresarial",
        "type": "Diplomado",
        "instructor": "Dr. Hernán Castillo",
        "date_start": "2026-08-15",
        "date_end": "2026-09-26",
        "quota": 30,
        "enrolled": 24,
        "status": "Activo",
        "certificates": 0
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Gestión del Talento Humano",
        "type": "Diplomado",
        "instructor": "Mg. Paola Vanegas",
        "date_start": "2026-09-01",
        "date_end": "2026-10-13",
        "quota": 25,
        "enrolled": 10,
        "status": "Programado",
        "certificates": 0
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Finanzas Corporativas para Directivos",
        "type": "Curso",
        "instructor": "Esp. Ricardo Morales",
        "date_start": "2026-06-01",
        "date_end": "2026-07-15",
        "quota": 20,
        "enrolled": 20,
        "status": "Finalizado",
        "certificates": 18
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Cumbre LatinPyme 2026",
        "type": "Evento",
        "instructor": "Varios Ponentes",
        "date_start": "2026-10-10",
        "date_end": "2026-10-11",
        "quota": 200,
        "enrolled": 87,
        "status": "Programado",
        "certificates": 0
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Marketing Digital B2B",
        "type": "Curso",
        "instructor": "Mg. Sofía León",
        "date_start": "2026-05-01",
        "date_end": "2026-06-10",
        "quota": 18,
        "enrolled": 18,
        "status": "Finalizado",
        "certificates": 16
    },
]


# ──────────────────────────────────────────────
# Página principal
# ──────────────────────────────────────────────
@learning_bp.route('/')
def index():
    """Renderiza el módulo académico/aprendizaje."""
    return render_template('learning.html')


# ──────────────────────────────────────────────
# API — Listar todos los cursos
# ──────────────────────────────────────────────
@learning_bp.route('/api/courses', methods=['GET'])
def api_get_courses():
    """Retorna la lista de todos los cursos/diplomados/eventos."""
    return jsonify(courses_store)


# ──────────────────────────────────────────────
# API — Agregar un nuevo curso
# ──────────────────────────────────────────────
@learning_bp.route('/api/courses', methods=['POST'])
def api_add_course():
    """Agrega un nuevo curso al store."""
    data = request.get_json(silent=True) or {}

    required = ['name', 'type', 'instructor', 'date_start', 'date_end', 'quota']
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"Campo requerido: {field}"}), 400

    new_course = {
        "id": str(uuid.uuid4()),
        "name": data['name'],
        "type": data['type'],
        "instructor": data['instructor'],
        "date_start": data['date_start'],
        "date_end": data['date_end'],
        "quota": int(data['quota']),
        "enrolled": 0,
        "status": data.get('status', 'Programado'),
        "certificates": 0
    }
    courses_store.append(new_course)
    return jsonify(new_course), 201


# ──────────────────────────────────────────────
# API — Emitir certificados para un curso
# ──────────────────────────────────────────────
@learning_bp.route('/api/courses/<course_id>/certify', methods=['POST'])
def api_certify(course_id):
    """Marca todos los inscritos como certificados."""
    for c in courses_store:
        if c['id'] == course_id:
            c['certificates'] = c['enrolled']
            return jsonify(c), 200
    return jsonify({"error": "Curso no encontrado"}), 404


# ──────────────────────────────────────────────
# API — Eliminar un curso
# ──────────────────────────────────────────────
@learning_bp.route('/api/courses/<course_id>', methods=['DELETE'])
def api_delete_course(course_id):
    """Elimina un curso del store."""
    global courses_store
    original_len = len(courses_store)
    courses_store = [c for c in courses_store if c['id'] != course_id]
    if len(courses_store) < original_len:
        return jsonify({"status": "deleted"}), 200
    return jsonify({"error": "Curso no encontrado"}), 404
