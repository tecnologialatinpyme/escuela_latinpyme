"""
routes/contacts.py
══════════════════════════════════════════════════════════════════
Rutas del Módulo de Contactos — Escuela LatinPyme.
Ofrece vista web y API REST para CRUD de contactos.
══════════════════════════════════════════════════════════════════
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from db import contact_store

contacts_bp = Blueprint('contacts', __name__)


@contacts_bp.route('/')
@login_required
def index():
    """Renderiza la vista principal del Módulo de Contactos."""
    return render_template('contacts.html')


@contacts_bp.route('/api', methods=['GET'])
@login_required
def api_list_contacts():
    """Retorna la lista JSON de contactos con soporte para búsqueda ?q=query."""
    query = request.args.get('q', '').strip()
    contacts = contact_store.list_contacts(query=query)
    
    # Calcular estadísticas rápidas
    total = len(contacts)
    with_email = sum(1 for c in contacts if c.get('email'))
    with_aula = sum(1 for c in contacts if c.get('aula_nombre') or c.get('aula_id'))

    return jsonify({
        "exito": True,
        "contacts": contacts,
        "stats": {
            "total": total,
            "with_email": with_email,
            "with_aula": with_aula
        }
    })


@contacts_bp.route('/api/create', methods=['POST'])
@login_required
def api_create_contact():
    """Crea un nuevo contacto manualmente desde el formulario web."""
    data = request.get_json(silent=True) or {}
    phone = data.get('phone', '').strip()
    name = data.get('name', '').strip()

    if not phone or not name:
        return jsonify({"exito": False, "error": "El nombre y el teléfono son campos obligatorios"}), 400

    created = contact_store.create_contact(
        phone=phone,
        name=name,
        email=data.get('email'),
        company=data.get('company'),
        cargo=data.get('cargo'),
        ciudad=data.get('ciudad'),
        aula_id=data.get('aula_id'),
        aula_nombre=data.get('aula_nombre')
    )

    if created:
        return jsonify({"exito": True, "contact": created, "mensaje": "Contacto creado exitosamente"}), 201
    return jsonify({"exito": False, "error": "No se pudo crear el contacto en la base de datos"}), 500


@contacts_bp.route('/api/update/<int:contact_id>', methods=['PUT'])
@login_required
def api_update_contact(contact_id: int):
    """Actualiza la información de un contacto existente."""
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"exito": False, "error": "No se enviaron datos para actualizar"}), 400

    ok = contact_store.update_contact(contact_id, data)
    if ok:
        updated_contact = contact_store.get_contact_by_id(contact_id)
        return jsonify({"exito": True, "contact": updated_contact, "mensaje": "Contacto actualizado correctamente"}), 200
    return jsonify({"exito": False, "error": "Error actualizando el contacto"}), 500


@contacts_bp.route('/api/delete/<int:contact_id>', methods=['DELETE'])
@login_required
def api_delete_contact(contact_id: int):
    """Elimina un contacto (Soft Delete)."""
    ok = contact_store.delete_contact(contact_id)
    if ok:
        return jsonify({"exito": True, "contact_id": contact_id, "mensaje": "Contacto eliminado exitosamente"}), 200
    return jsonify({"exito": False, "error": "Error al eliminar el contacto"}), 500
