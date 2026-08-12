import uuid
import os
import json
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required
from db import database as db

conversations_bp = Blueprint('conversations', __name__)

# ──────────────────────────────────────────────
# Persistencia en PostgreSQL (via db.database)
# ──────────────────────────────────────────────

def _load_store() -> dict:
    """Carga el store desde PostgreSQL."""
    return db.load_store()


def _save_store(store: dict) -> None:
    """Guarda el store completo en PostgreSQL (usado solo en seed inicial)."""
    db.save_store(store)


def _save_one(phone: str, data: dict) -> None:
    """Guarda/actualiza una sola conversación en PostgreSQL (más eficiente)."""
    db.save_conversation(phone, data)


# Datos semilla — solo se insertan si el archivo no existe aún
_SEED_DATA = {
    "+573144187269": {
        "name": "Andrés Mendoza",
        "avatar": "AM",
        "messages": [
            {"id": str(uuid.uuid4()), "direction": "out", "body": "Hola Andrés, te contactamos desde la Escuela LatinPyme. ¿Tienes disponibilidad para conocer nuestro Diplomado en Liderazgo?", "ts": "09:14"},
            {"id": str(uuid.uuid4()), "direction": "in",  "body": "¡Hola! Sí, me interesa mucho. ¿Cuándo inicia?", "ts": "09:22"},
            {"id": str(uuid.uuid4()), "direction": "out", "body": "El próximo cohorte inicia el 15 de agosto. Son 6 semanas en modalidad virtual. ¿Te envío el brochure?", "ts": "09:25"},
            {"id": str(uuid.uuid4()), "direction": "in",  "body": "Perfecto, sí envíame la información por favor.", "ts": "09:31"},
        ],
        "unread": 1,
        "last_message": "Perfecto, sí envíame la información por favor.",
        "last_ts": "09:31"
    },
    "+573105584725": {
        "name": "Diana Duarte",
        "avatar": "DD",
        "messages": [
            {"id": str(uuid.uuid4()), "direction": "out", "body": "Diana, buenos días. Le escribimos para informarle sobre el Diplomado en Gestión del Talento Humano.", "ts": "10:05"},
            {"id": str(uuid.uuid4()), "direction": "in",  "body": "Gracias por contactarme. ¿Tiene modalidad presencial?", "ts": "10:48"},
        ],
        "unread": 1,
        "last_message": "Gracias por contactarme. ¿Tiene modalidad presencial?",
        "last_ts": "10:48"
    },
    "+573215896325": {
        "name": "Carlos Restrepo",
        "avatar": "CR",
        "messages": [
            {"id": str(uuid.uuid4()), "direction": "out", "body": "Carlos, le escribimos desde LatinPyme. Notamos que registró interés en el área de Finanzas Corporativas.", "ts": "11:30"},
        ],
        "unread": 0,
        "last_message": "Carlos, le escribimos desde LatinPyme.",
        "last_ts": "11:30"
    },
}

# Inicializar store: cargar desde disco; si está vacío, sembrar datos de ejemplo
conversations_store = _load_store()
if not conversations_store:
    conversations_store.update(_SEED_DATA)
    _save_store(conversations_store)


def _now_ts():
    return datetime.now().strftime("%H:%M")


# ──────────────────────────────────────────────
# Página principal — WhatsApp Web Clone
# ──────────────────────────────────────────────
@conversations_bp.route('/')
@login_required
def index():
    """Renderiza el clon de WhatsApp Web."""
    return render_template('conversations.html')


# ──────────────────────────────────────────────
# Webhook de Meta — Verificación (GET)
# ──────────────────────────────────────────────
@conversations_bp.route('/webhook', methods=['GET'])
def webhook_verify():
    """
    Punto de verificación del Webhook de Meta (WhatsApp Cloud API).
    Meta envía: hub.mode=subscribe, hub.verify_token=<token>, hub.challenge=<challenge>
    Si el token coincide, respondemos con el challenge para activar el webhook.
    """
    mode      = request.args.get('hub.mode')
    token     = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    verify_token = current_app.config.get('META_WA_WEBHOOK_VERIFY_TOKEN', 'latinpyme_secret_token')

    if mode == 'subscribe' and token == verify_token:
        return challenge, 200
    return jsonify({"error": "Token de verificación incorrecto"}), 403


# ──────────────────────────────────────────────
# Webhook de Meta — Recepción de mensajes (POST)
# ──────────────────────────────────────────────
@conversations_bp.route('/webhook', methods=['POST'])
def webhook_receive():
    """
    Recibe eventos del Webhook de Meta (WhatsApp Cloud API).
    Soporta: mensajes de texto entrantes y actualizaciones de estado.
    """
    payload = request.get_json(silent=True) or {}

    # Log completo para debugging
    current_app.logger.info(f"[WEBHOOK] Payload recibido: {payload}")

    try:
        for entry in payload.get('entry', []):
            for change in entry.get('changes', []):
                value = change.get('value', {})

                # Procesar status updates para capturar numero real del destinatario
                for status in value.get('statuses', []):
                    recipient_id = status.get('recipient_id', '')
                    if not recipient_id:
                        continue
                    real_phone = '+' + recipient_id if not recipient_id.startswith('+') else recipient_id
                    for key, conv in list(conversations_store.items()):
                        if not key.startswith('+') and not conv.get('real_phone') and not conv.get('wa_id'):
                            conv['wa_id'] = recipient_id
                            conv['real_phone'] = real_phone
                        elif conv.get('wa_id') == recipient_id or conv.get('real_phone') == real_phone:
                            conv['wa_id'] = recipient_id
                            conv['real_phone'] = real_phone

                # Procesar mensajes entrantes
                for msg in value.get('messages', []):
                    raw_phone     = msg.get('from', '')
                    from_user_id  = msg.get('from_user_id', '')
                    body          = msg.get('text', {}).get('body', '[mensaje sin texto]')
                    msg_id        = msg.get('id', str(uuid.uuid4()))

                    # Obtener nombre y wa_id del contacto
                    contacts = value.get('contacts', [])
                    contact  = contacts[0] if contacts else {}
                    name     = contact.get('profile', {}).get('name', '')
                    wa_id    = contact.get('wa_id', '')
                    user_id  = contact.get('user_id', from_user_id)

                    # Determinar el identificador del remitente en orden de preferencia:
                    # 1. msg.from  (número real E.164)
                    # 2. contacts[0].wa_id  (número en formato wa)
                    # 3. user_id  (identificador de privacidad de Meta)
                    if raw_phone and raw_phone.strip().lstrip('+').isdigit():
                        phone_key = raw_phone.strip()
                        if not phone_key.startswith('+'):
                            phone_key = '+' + phone_key
                        display_phone = phone_key
                    elif wa_id and wa_id.strip().isdigit():
                        phone_key = '+' + wa_id.strip()
                        display_phone = phone_key
                    elif user_id:
                        # Modo privacidad: usamos user_id como clave, sin número real
                        phone_key = user_id
                        display_phone = '(número privado)'
                    else:
                        current_app.logger.warning(f"[WEBHOOK] Mensaje sin identificador: msg={msg}")
                        continue

                    if not name:
                        name = display_phone

                    # Crear o actualizar conversación
                    if phone_key not in conversations_store:
                        conversations_store[phone_key] = {
                            "name": name,
                            "avatar": name[:2].upper(),
                            "messages": [],
                            "unread": 0,
                            "last_message": "",
                            "last_ts": _now_ts(),
                            "display_phone": display_phone,
                            "wa_id": wa_id or '',
                            "user_id": user_id or ''
                        }
                    else:
                        # Actualizar nombre/datos si llegaron
                        if name and name != display_phone:
                            conversations_store[phone_key]["name"] = name
                        if wa_id:
                            conversations_store[phone_key]["wa_id"] = wa_id

                    new_msg = {
                        "id": msg_id,
                        "direction": "in",
                        "body": body,
                        "ts": _now_ts()
                    }
                    conversations_store[phone_key]["messages"].append(new_msg)
                    conversations_store[phone_key]["unread"] += 1
                    conversations_store[phone_key]["last_message"] = body
                    conversations_store[phone_key]["last_ts"] = _now_ts()
                    _save_one(phone_key, conversations_store[phone_key])

                    current_app.logger.info(f"[WEBHOOK] Mensaje de {phone_key} ({name}): {body}")


    except Exception as e:
        # Siempre responder 200 para que Meta no reintente el evento
        current_app.logger.error(f"Error procesando webhook: {e}")

    return jsonify({"status": "ok"}), 200


# ──────────────────────────────────────────────
# API — Listar todas las conversaciones (polling UI)
# ──────────────────────────────────────────────
@conversations_bp.route('/api/messages', methods=['GET'])
@login_required
def api_get_messages():
    """
    Retorna la lista de conversaciones para el panel izquierdo
    y los mensajes del chat activo si se pasa ?phone=<numero>.
    """
    phone = request.args.get('phone')

    # Lista de chats para el sidebar
    chat_list = []
    for num, data in conversations_store.items():
        chat_list.append({
            "phone": num,
            "name": data["name"],
            "avatar": data["avatar"],
            "last_message": data["last_message"],
            "last_ts": data["last_ts"],
            "unread": data["unread"]
        })

    if phone and phone in conversations_store:
        # Marcar como leído al abrir el chat
        conversations_store[phone]["unread"] = 0
        return jsonify({
            "chats": chat_list,
            "active_messages": conversations_store[phone]["messages"],
            "active_name": conversations_store[phone]["name"]
        })

    return jsonify({"chats": chat_list, "active_messages": [], "active_name": ""})


# ──────────────────────────────────────────────
# API — Eliminar conversación
# ──────────────────────────────────────────────
@conversations_bp.route('/api/delete', methods=['DELETE'])
@login_required
def api_delete_conversation():
    """
    Elimina permanentemente una conversación del store en memoria.
    Recibe JSON: { "phone": "+57XXXXXXXXXX" }
    """
    data = request.get_json(silent=True) or {}
    phone = data.get('phone', '').strip()

    if not phone:
        return jsonify({"error": "Falta el campo phone"}), 400

    if phone not in conversations_store:
        return jsonify({"error": "Conversación no encontrada"}), 404

    del conversations_store[phone]
    db.delete_conversation(phone)
    return jsonify({"status": "deleted", "phone": phone}), 200


# ──────────────────────────────────────────────
# API — Vincular número real a conversación por user_id
# ──────────────────────────────────────────────
@conversations_bp.route('/api/link-phone', methods=['POST'])
@login_required
def api_link_phone():
    """
    Vincula un número de teléfono real a una conversación identificada por user_id.
    Recibe JSON: { "user_id": "CO.xxx", "real_phone": "+573002711932" }
    """
    data      = request.get_json(silent=True) or {}
    user_id   = data.get('user_id', '').strip()
    real_phone = data.get('real_phone', '').strip()

    if not user_id or not real_phone:
        return jsonify({"error": "Faltan campos user_id o real_phone"}), 400

    if user_id not in conversations_store:
        return jsonify({"error": "Conversación no encontrada"}), 404

    wa_id = real_phone.lstrip('+')
    conversations_store[user_id]['real_phone'] = real_phone
    conversations_store[user_id]['wa_id'] = wa_id
    _save_one(user_id, conversations_store[user_id])
    current_app.logger.info(f"[LINK-PHONE] Vinculado {user_id} → {real_phone}")
    return jsonify({"status": "linked", "user_id": user_id, "real_phone": real_phone}), 200


# ──────────────────────────────────────────────
@conversations_bp.route('/api/send', methods=['POST'])
@login_required
def api_send_message():
    """
    Guarda el mensaje del asesor en el store local Y lo envía realmente
    por WhatsApp Cloud API usando el WhatsAppService.
    """
    from services.whatsapp_service import WhatsAppService

    data  = request.get_json(silent=True) or {}
    phone = data.get('phone', '').strip()
    body  = data.get('body', '').strip()

    if not phone or not body:
        return jsonify({"error": "Faltan campos phone o body"}), 400

    if phone not in conversations_store:
        return jsonify({"error": "Conversación no encontrada"}), 404

    conv = conversations_store[phone]

    # Determinar el número real al que enviar:
    # Si el phone es un user_id (CO.xxx) buscamos el wa_id o real_phone guardado
    if phone.startswith('+') and phone[1:].isdigit():
        # Es un número real E.164 directo
        send_to = phone
    else:
        # Es un user_id — buscar número real guardado en la conversación
        real = conv.get('real_phone') or conv.get('wa_id', '')
        if real:
            send_to = real if real.startswith('+') else '+' + real
        else:
            # Sin número real disponible — no podemos enviar
            current_app.logger.warning(f"[SEND] user_id sin número real: {phone}")
            new_msg = {
                "id": str(uuid.uuid4()),
                "direction": "out",
                "body": body,
                "ts": _now_ts(),
                "wa_sent": False,
                "simulado": False
            }
            conv["messages"].append(new_msg)
            conv["last_message"] = body
            conv["last_ts"] = _now_ts()
            _save_one(phone, conv)
            return jsonify({
                "status": "sent",
                "message": new_msg,
                "whatsapp": {
                    "exito": False,
                    "error": "El número de este contacto está oculto por privacidad. Agrega su número real en Meta Developers → Destinatarios de prueba para poder responder."
                }
            }), 200

    # ── Intentar enviar por WhatsApp Cloud API ──
    wa_result = {"exito": False, "simulado": True}
    try:
        wa = WhatsAppService()
        wa_result = wa.enviar_mensaje_texto(send_to, body)
        if not wa_result.get("exito"):
            current_app.logger.warning(
                f"[SEND] Meta respondió error para {send_to}: {wa_result}"
            )
    except Exception as e:
        current_app.logger.error(f"[SEND] Excepción enviando a {send_to}: {e}")
        wa_result = {"exito": False, "error": str(e)}

    # ── Guardar siempre en el store local ──
    new_msg = {
        "id": str(uuid.uuid4()),
        "direction": "out",
        "body": body,
        "ts": _now_ts(),
        "wa_sent": wa_result.get("exito", False),
        "simulado": wa_result.get("simulado", False)
    }
    conv["messages"].append(new_msg)
    conv["last_message"] = body
    conv["last_ts"] = _now_ts()
    _save_one(phone, conv)

    return jsonify({
        "status": "sent",
        "message": new_msg,
        "whatsapp": wa_result
    }), 200

