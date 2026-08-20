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


# Inicializar store directamente desde Supabase sin datos de prueba
conversations_store = {}
try:
    conversations_store = _load_store()
except Exception as e:
    print(f"[CONVERSATIONS] Advertencia cargando conversaciones en arranque: {e}")
    conversations_store = {}




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

                    # Detectar intención explícita de asesor humano en el mensaje entrante
                    body_lower = (body or '').lower()
                    human_keywords = [
                        'asesor humano', 'hablar con asesor', 'hablar con un asesor',
                        'hablar con alguien', 'asesor de ventas', 'asesor de soporte',
                        'comunicarme con un humano', 'atencion humana', 'atención humana',
                        'quiero un asesor', 'necesito un asesor', 'pasar a un asesor',
                        'asesor_humano'
                    ]
                    if any(kw in body_lower for kw in human_keywords):
                        conversations_store[phone_key]["human_required"] = True
                        try:
                            from db.database import set_ai_conversation_enabled
                            set_ai_conversation_enabled(phone_key, False)
                        except Exception as e:
                            print(f"[WEBHOOK] Error pausando IA para {phone_key}: {e}")

                    _save_one(phone_key, conversations_store[phone_key])
                    db.add_message(phone=phone_key, direction="in", body=body, ts=new_msg["ts"], msg_id=msg_id)

                    current_app.logger.info(f"[WEBHOOK] Mensaje de {phone_key} ({name}): {body}")

                    # ── Respuesta Automática de IA ──
                    _trigger_ai_reply(phone_key, conversations_store[phone_key])


    except Exception as e:
        # Siempre responder 200 para que Meta no reintente el evento
        current_app.logger.error(f"Error procesando webhook: {e}")

    return jsonify({"status": "ok"}), 200


def _trigger_ai_reply(phone_key: str, conv: dict) -> None:
    """
    Genera y envía una respuesta automática de IA si está habilitado.
    Se ejecuta después de recibir un mensaje entrante vía webhook.
    """
    try:
        from config.settings import app_config
        # Verificar si el asistente IA y el modo auto-reply están activos
        if not app_config.ai_assistant_enabled or not app_config.ai_auto_reply:
            return

        from services.ai_assistant_service import AiAssistantService
        svc = AiAssistantService()

        # Verificar si la IA está habilitada para esta conversación específica
        if not svc.esta_habilitada_para_conversacion(phone_key):
            return

        # Generar respuesta
        mensajes = conv.get('messages', [])
        resultado = svc.generar_respuesta(phone_key, mensajes)

        if not resultado.get('exito') or not resultado.get('respuesta'):
            return

        respuesta_texto = resultado['respuesta']
        disparador = resultado.get('disparador', 'ninguno')
        pausar_ia  = resultado.get('pausar_ia', False)

        if disparador and disparador != 'ninguno':
            conv['last_trigger'] = disparador

        is_human_transfer = (
            pausar_ia or 
            (disparador and 'asesor_humano' in str(disparador).lower()) or
            disparador in ['asesor_humano_soporte', 'asesor_humano_ventas', 'soluciones_patrocinador']
        )

        if is_human_transfer:
            conv['human_required'] = True
            _save_one(phone_key, conv)
            try:
                from db.database import set_ai_conversation_enabled
                set_ai_conversation_enabled(phone_key, False)
            except Exception as e:
                print(f"[IA-REPLY] Error pausando IA para {phone_key}: {e}")

        # Determinar el número real al que enviar
        if phone_key.startswith('+') and phone_key[1:].isdigit():
            send_to = phone_key
        else:
            real = conv.get('real_phone') or conv.get('wa_id', '')
            if not real:
                return
            send_to = real if real.startswith('+') else '+' + real

        # Enviar por WhatsApp
        from services.whatsapp_service import WhatsAppService
        wa = WhatsAppService()
        wa_result = wa.enviar_mensaje_texto(send_to, respuesta_texto)

        # Guardar la respuesta de la IA en el store
        ai_msg = {
            'id':           str(uuid.uuid4()),
            'direction':    'out',
            'body':         respuesta_texto,
            'ts':           _now_ts(),
            'ia_generated': True,
            'disparador':   disparador,
            'wa_sent':      wa_result.get('exito', False),
            'aula_info':    resultado.get('aula_info', {}),
            'simulado':     resultado.get('modo_simulacion', False)
        }
        conv['messages'].append(ai_msg)
        conv['last_message'] = respuesta_texto
        conv['last_ts'] = _now_ts()
        _save_one(phone_key, conv)
        db.add_message(
            phone=phone_key, direction='out', body=respuesta_texto, ts=ai_msg['ts'],
            ia_generated=True, disparador=disparador, wa_sent=ai_msg['wa_sent'],
            simulado=ai_msg['simulado'], msg_id=ai_msg['id']
        )

        from flask import current_app
        current_app.logger.info(
            f"[IA-REPLY] Respuesta enviada a {phone_key} | "
            f"Aula: {resultado.get('aula_info', {}).get('aula_nombre', 'N/A')} | "
            f"Simulado: {resultado.get('modo_simulacion', False)}"
        )

    except Exception as e:
        try:
            from flask import current_app
            current_app.logger.error(f"[IA-REPLY] Error generando respuesta IA para {phone_key}: {e}")
        except Exception:
            print(f"[IA-REPLY] Error: {e}")




# ──────────────────────────────────────────────
# API — Consultar información del aula y usuario por teléfono
# ──────────────────────────────────────────────
@conversations_bp.route('/api/user-aula-info', methods=['GET'])
@login_required
def api_user_aula_info():
    """
    Consulta la API externa de Aulas con el teléfono de la conversación
    y retorna la información completa del estudiante (Nombre, Email, Aula, space_id, dominio)
    junto con los estados de IA y disparadores del chat.
    """
    phone = request.args.get('phone', '').strip()
    if not phone:
        return jsonify({"error": "Falta el parámetro phone"}), 400

    from services.ai_assistant_service import AiAssistantService
    from db.database import get_ai_conversation_config

    svc = AiAssistantService()
    aula_info = svc.buscar_aula_por_telefono(phone)

    # Si hay una conversación, guardar o actualizar la información del aula
    conv_data = conversations_store.get(phone, {})
    if conv_data:
        conv_data['aula_info'] = aula_info
        if aula_info.get('nombre_usuario') and aula_info['nombre_usuario'] != 'Estudiante':
            conv_data['name'] = aula_info['nombre_usuario']
        _save_one(phone, conv_data)

    ai_cfg = get_ai_conversation_config(phone)
    ai_enabled = ai_cfg.get('ai_enabled', True) if ai_cfg else True

    return jsonify({
        "exito": True,
        "phone": phone,
        "ai_enabled": ai_enabled,
        "human_required": conv_data.get("human_required", False),
        "last_trigger": conv_data.get("last_trigger", ""),
        "aula_info": aula_info
    })


# ──────────────────────────────────────────────
# API — Listar todas las conversaciones (polling UI)
# ──────────────────────────────────────────────
@conversations_bp.route('/api/messages', methods=['GET'])
@login_required
def api_get_messages():
    """
    Retorna la lista de conversaciones para el panel izquierdo
    y los mensajes del chat activo si se pasa ?phone=<numero>.
    Sincroniza dinámicamente con Supabase en cada consulta.
    """
    phone = request.args.get('phone')

    global conversations_store
    try:
        db_store = _load_store()
        if db_store is not None:
            conversations_store = db_store
    except Exception as e:
        print(f"[API-MESSAGES] Aviso sincronizando conversaciones con BD: {e}")

    from db.database import get_ai_conversation_config

    chat_list = []
    for num, data in conversations_store.items():
        ai_cfg = get_ai_conversation_config(num)
        ai_enabled = ai_cfg.get('ai_enabled', True) if ai_cfg else True

        chat_list.append({
            "phone":          num,
            "name":           data["name"],
            "avatar":         data["avatar"],
            "last_message":   data["last_message"],
            "last_ts":        data["last_ts"],
            "unread":         data["unread"],
            "human_required": data.get("human_required", False),
            "last_trigger":   data.get("last_trigger", ""),
            "ai_enabled":     ai_enabled
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
            db.add_message(phone=phone, direction="out", body=body, ts=new_msg["ts"],
                            wa_sent=False, simulado=False, msg_id=new_msg["id"])
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
    db.add_message(phone=phone, direction="out", body=body, ts=new_msg["ts"],
                    wa_sent=new_msg["wa_sent"], simulado=new_msg["simulado"], msg_id=new_msg["id"])

    return jsonify({
        "status": "sent",
        "message": new_msg,
        "whatsapp": wa_result
    }), 200


# ──────────────────────────────────────────────
# API — Toggle IA en conversación
# ──────────────────────────────────────────────
@conversations_bp.route('/api/ai-toggle', methods=['POST'])
@login_required
def api_ai_toggle():
    """
    Activa o desactiva la IA para una conversación específica.
    Recibe JSON: { "phone": "+57XXX", "ai_enabled": true/false }
    """
    data       = request.get_json(silent=True) or {}
    phone      = data.get('phone', '').strip()
    ai_enabled = data.get('ai_enabled', True)

    if not phone:
        return jsonify({"error": "Falta el campo phone"}), 400

    try:
        from db.database import set_ai_conversation_enabled
        ok = set_ai_conversation_enabled(phone, ai_enabled)
        estado = "activada" if ai_enabled else "desactivada"
        if ok:
            return jsonify({"status": "ok", "ai_enabled": ai_enabled, "mensaje": f"IA {estado} para esta conversación."})
        return jsonify({"error": "Error al actualizar en BD"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────
# API — Sugerencia de respuesta IA (sin enviar)
# ──────────────────────────────────────────────
@conversations_bp.route('/api/ai-suggestion', methods=['GET'])
@login_required
def api_ai_suggestion():
    """
    Genera una sugerencia de respuesta de IA para una conversación
    pero NO la envía por WhatsApp. El asesor la puede revisar y enviar manualmente.
    """
    phone = request.args.get('phone', '').strip()
    if not phone:
        return jsonify({"error": "Falta el parámetro phone"}), 400

    if phone not in conversations_store:
        return jsonify({"error": "Conversación no encontrada"}), 404

    try:
        from services.ai_assistant_service import AiAssistantService
        svc = AiAssistantService()
        mensajes  = conversations_store[phone].get('messages', [])
        resultado = svc.generar_respuesta(phone, mensajes)
        return jsonify(resultado)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ──────────────────────────────────────────────
# API — Toggle Atención Humana Requerida
# ──────────────────────────────────────────────
@conversations_bp.route('/api/human-toggle', methods=['POST'])
@login_required
def api_human_toggle():
    """
    Marca o desmarca una conversación como 'human_required' (Atención de Asesor).
    Recibe JSON: { "phone": "+57XXX", "human_required": true/false }
    """
    data = request.get_json(silent=True) or {}
    phone = data.get('phone', '').strip()
    human_required = bool(data.get('human_required', True))
    reactivate_ai = data.get('reactivate_ai', False)

    if not phone or phone not in conversations_store:
        return jsonify({"exito": False, "error": "Conversación no encontrada"}), 404

    conversations_store[phone]["human_required"] = human_required
    _save_one(phone, conversations_store[phone])

    if not human_required and reactivate_ai:
        try:
            from db.database import set_ai_conversation_enabled
            set_ai_conversation_enabled(phone, True)
        except Exception as e:
            print(f"[HUMAN-TOGGLE] Error re-enabling AI: {e}")

    return jsonify({
        "exito": True,
        "phone": phone,
        "human_required": human_required,
        "mensaje": f"Estado de atención humana actualizado para {phone}."
    })

