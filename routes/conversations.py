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
    """Guarda/actualiza una sola conversación en PostgreSQL (más eficiente) y sincroniza su contacto."""
    db.save_conversation(phone, data)
    try:
        from db import contact_store
        aula_info = data.get('aula_info') or {}
        contact_store.upsert_contact_from_conversation(
            phone=phone,
            name=data.get('name'),
            email=data.get('email') or aula_info.get('email_usuario'),
            company=data.get('company') or aula_info.get('empresa_patrocinadora'),
            aula_id=aula_info.get('space_id') or aula_info.get('aula_id'),
            aula_nombre=aula_info.get('aula_nombre')
        )
    except Exception:
        pass


# Inicializar store directamente desde Supabase sin datos de prueba
conversations_store = {}
try:
    conversations_store = _load_store()
except Exception as e:
    print(f"[CONVERSATIONS] Advertencia cargando conversaciones en arranque: {e}")
    conversations_store = {}




from datetime import datetime, timezone

def _now_ts():
    return datetime.now(timezone.utc).isoformat()



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

                # Procesar status updates de Meta (visto de WhatsApp: sent, delivered, read, failed)
                for status_obj in value.get('statuses', []):
                    recipient_id = status_obj.get('recipient_id', '')
                    wa_msg_id    = status_obj.get('id', '')
                    msg_status   = status_obj.get('status', '')  # 'sent', 'delivered', 'read', 'failed'

                    if recipient_id:
                        real_phone = '+' + recipient_id if not recipient_id.startswith('+') else recipient_id
                        for key, conv in list(conversations_store.items()):
                            if not key.startswith('+') and not conv.get('real_phone') and not conv.get('wa_id'):
                                conv['wa_id'] = recipient_id
                                conv['real_phone'] = real_phone
                            elif conv.get('wa_id') == recipient_id or conv.get('real_phone') == real_phone:
                                conv['wa_id'] = recipient_id
                                conv['real_phone'] = real_phone

                    # Actualizar estado de visto (sent, delivered, read, failed)
                    if wa_msg_id and msg_status:
                        for p_key, conv_item in conversations_store.items():
                            for m in conv_item.get('messages', []):
                                if m.get('id') == wa_msg_id or m.get('wa_message_id') == wa_msg_id:
                                    m['status'] = msg_status
                                    break
                        db.update_message_status(wa_msg_id, msg_status)
                        current_app.logger.info(f"[WEBHOOK] Visto WhatsApp actualizado ({wa_msg_id} -> {msg_status})")

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

                    # Registrar/actualizar automáticamente en el Módulo de Contactos
                    try:
                        from db import contact_store
                        contact_store.upsert_contact_from_conversation(
                            phone=phone_key,
                            name=name if name != display_phone else None
                        )
                    except Exception as c_err:
                        current_app.logger.warning(f"[WEBHOOK] Error auto-guardando contacto {phone_key}: {c_err}")

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
        meta_msg_id = wa_result.get('message_id') or str(uuid.uuid4())
        initial_status = 'sent' if wa_result.get('exito') else 'failed'

        ai_msg = {
            'id':           meta_msg_id,
            'wa_message_id': meta_msg_id,
            'direction':    'out',
            'body':         respuesta_texto,
            'ts':           _now_ts(),
            'ia_generated': True,
            'disparador':   disparador,
            'wa_sent':      wa_result.get('exito', False),
            'simulado':     resultado.get('modo_simulacion', False),
            'status':       initial_status,
            'aula_info':    resultado.get('aula_info', {})
        }
        conv['messages'].append(ai_msg)
        conv['last_message'] = respuesta_texto
        conv['last_ts'] = _now_ts()
        _save_one(phone_key, conv)
        db.add_message(
            phone=phone_key, direction='out', body=respuesta_texto, ts=ai_msg['ts'],
            ia_generated=True, disparador=disparador, wa_sent=ai_msg['wa_sent'],
            simulado=ai_msg['simulado'], msg_id=meta_msg_id, wa_message_id=meta_msg_id,
            status=initial_status
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

    # Actualizar la ficha en el Módulo de Contactos con los datos enriquecidos del Aula
    try:
        from db import contact_store
        contact_store.upsert_contact_from_conversation(
            phone=phone,
            name=aula_info.get('nombre_usuario') if (aula_info.get('nombre_usuario') and aula_info.get('nombre_usuario') != 'Estudiante') else conv_data.get('name'),
            email=aula_info.get('email_usuario'),
            company=aula_info.get('empresa_patrocinadora'),
            aula_id=aula_info.get('space_id') or aula_info.get('aula_id'),
            aula_nombre=aula_info.get('aula_nombre')
        )
    except Exception as c_err:
        print(f"[API-AULA-INFO] Error auto-actualizando contacto: {c_err}")

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

    # Ordenar los chats por fecha/hora de la última actividad (más reciente de primeras)
    def _parse_ts_sort(c):
        ts_val = c.get('last_ts') or ''
        ts_str = str(ts_val).strip()
        if not ts_str:
            return 0.0
        try:
            dt = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            return dt.timestamp()
        except Exception:
            pass
        if ':' in ts_str and len(ts_str) <= 8:
            try:
                parts = ts_str.split(':')
                h, m = int(parts[0]), int(parts[1])
                now = datetime.now(timezone.utc)
                dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
                return dt.timestamp()
            except Exception:
                pass
        return 0.0

    chat_list.sort(key=_parse_ts_sort, reverse=True)


    from db.database import normalize_phone_number

    active_phone_key = None
    if phone:
        clean_phone = phone.strip()
        if clean_phone.startswith(' '):
            clean_phone = '+' + clean_phone.lstrip()
        norm_phone = normalize_phone_number(clean_phone)

        for k in conversations_store.keys():
            if k == clean_phone or k == norm_phone or normalize_phone_number(k) == norm_phone:
                active_phone_key = k
                break

    active_msgs = []
    active_name = ""

    if active_phone_key and active_phone_key in conversations_store:
        # Marcar como leído al abrir el chat
        conversations_store[active_phone_key]["unread"] = 0
        active_msgs = conversations_store[active_phone_key].get("messages", [])
        active_name = conversations_store[active_phone_key].get("name", "")

    # Salvaguarda: Consulta directa a la base de datos de mensajes si no se encontró en memoria
    if phone and not active_msgs:
        try:
            from db.database import _get_client
            client = _get_client()
            clean_p = phone.strip().replace(' ', '+')
            norm_p = normalize_phone_number(clean_p)
            
            m_res = client.table('messages').select('*').or_(f"conversation_phone.eq.{clean_p},conversation_phone.eq.{norm_p}").is_('deleted_at', 'null').order('ts', desc=False).execute()
            if m_res.data:
                active_msgs = [{
                    "id": m.get('id'),
                    "wa_message_id": m.get('wa_message_id'),
                    "direction": m.get('direction'),
                    "body": m.get('body'),
                    "ts": m.get('ts'),
                    "ia_generated": m.get('ia_generated', False),
                    "disparador": m.get('disparador'),
                    "wa_sent": m.get('wa_sent', True),
                    "simulado": m.get('simulado', False),
                    "status": m.get('status', 'sent')
                } for m in m_res.data]
                if not active_name and active_phone_key:
                    active_name = conversations_store.get(active_phone_key, {}).get("name", clean_p)
        except Exception as fetch_err:
            print(f"[API-MESSAGES] Salvaguarda de mensajes error: {fetch_err}")

    return jsonify({"chats": chat_list, "active_messages": active_msgs, "active_name": active_name})


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
    raw_phone = data.get('phone', '').strip()

    if not raw_phone:
        return jsonify({"error": "Falta el campo phone"}), 400

    from db.database import normalize_phone_number
    norm_phone = normalize_phone_number(raw_phone)

    # Eliminar de conversations_store probando todas las variantes de claves
    keys_to_del = [k for k in conversations_store.keys() if k == raw_phone or k == norm_phone or normalize_phone_number(k) == norm_phone]
    for k in keys_to_del:
        conversations_store.pop(k, None)

    db.delete_conversation(raw_phone)
    if norm_phone and norm_phone != raw_phone:
        db.delete_conversation(norm_phone)

    return jsonify({"status": "deleted", "phone": raw_phone}), 200


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
    meta_msg_id = wa_result.get("message_id") or str(uuid.uuid4())
    initial_status = "sent" if wa_result.get("exito") else "failed"

    new_msg = {
        "id": meta_msg_id,
        "wa_message_id": meta_msg_id,
        "direction": "out",
        "body": body,
        "ts": _now_ts(),
        "wa_sent": wa_result.get("exito", False),
        "simulado": wa_result.get("simulado", False),
        "status": initial_status
    }
    conv["messages"].append(new_msg)
    conv["last_message"] = body
    conv["last_ts"] = _now_ts()
    _save_one(phone, conv)
    db.add_message(phone=phone, direction="out", body=body, ts=new_msg["ts"],
                    wa_sent=new_msg["wa_sent"], simulado=new_msg["simulado"], msg_id=meta_msg_id,
                    wa_message_id=meta_msg_id, status=initial_status)

    return jsonify({
        "status": "sent",
        "message": new_msg,
        "whatsapp": wa_result
    }), 200


# ──────────────────────────────────────────────
# API — Simular visto de WhatsApp (sent -> delivered -> read)
# ──────────────────────────────────────────────
@conversations_bp.route('/api/simular-visto', methods=['POST'])
@login_required
def api_simular_visto():
    """
    Endpoint de pruebas para simular cambio de estado de visto (sent, delivered, read, failed).
    Recibe JSON: { "msg_id": "wamid...", "status": "read" }
    """
    data   = request.get_json(silent=True) or {}
    msg_id = data.get('msg_id', '').strip()
    status = data.get('status', 'read').strip()

    if not msg_id:
        return jsonify({"error": "Falta el campo msg_id"}), 400

    updated = False
    for p_key, conv in conversations_store.items():
        for m in conv.get('messages', []):
            if m.get('id') == msg_id or m.get('wa_message_id') == msg_id:
                m['status'] = status
                updated = True
                break

    db.update_message_status(msg_id, status)
    return jsonify({"exito": True, "msg_id": msg_id, "status": status, "updated_in_memory": updated}), 200


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

