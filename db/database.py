"""
db/database.py
══════════════════════════════════════════════════════════════════
Capa de acceso a Supabase para conversaciones de WhatsApp.
Usa el cliente oficial supabase-py via HTTPS (REST API).
No requiere conexión directa PostgreSQL.
══════════════════════════════════════════════════════════════════
"""
import os
import json
from dotenv import load_dotenv

load_dotenv()

_SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
_SUPABASE_KEY = os.environ.get('SUPABASE_SECRET_KEY', '')

_client = None


def _get_client():
    """Retorna el cliente Supabase (singleton)."""
    global _client
    if _client is None:
        if not _SUPABASE_URL or not _SUPABASE_KEY:
            raise RuntimeError(
                "SUPABASE_URL o SUPABASE_SECRET_KEY no están configuradas. "
                "Agrégalas en el archivo .env"
            )
        from supabase import create_client
        _client = create_client(_SUPABASE_URL, _SUPABASE_KEY)
    return _client


# ──────────────────────────────────────────────
# Inicialización — crear tablas si no existen
# ──────────────────────────────────────────────
def init_db() -> None:
    """Verifica la conexión a Supabase y comprueba la presencia de las tablas."""
    try:
        client = _get_client()
        client.table('conversations').select('phone').limit(1).execute()
        print("[DB] Conexión a Supabase establecida correctamente (conversations OK).")
        try:
            client.table('contacts').select('id').limit(1).execute()
            print("[DB] Tabla 'contacts' verificada en Supabase.")
        except Exception:
            print("[DB] AVISO: La tabla 'contacts' no existe en Supabase aún. Se utilizará el respaldo data/contacts.json.")
            print("[DB] >> Para crear la tabla en Supabase, ejecuta el SQL del archivo db/schema.sql en el SQL Editor.")
    except Exception as e:
        print(f"[DB] Error de conexión a Supabase: {e}")


# ──────────────────────────────────────────────
# Registro de Actividad (Auditoría)
# ──────────────────────────────────────────────
def log_activity(user_id: int | None, action: str, detail: str = None) -> bool:
    """Registra un evento de auditoría en la tabla activity_log."""
    try:
        client = _get_client()
        client.table('activity_log').insert({
            'user_id': user_id,
            'action': action,
            'detail': detail,
            'ts': 'now()'
        }).execute()
        return True
    except Exception as e:
        print(f"[DB] Error registrando activity_log ({action}): {e}")
        return False


def get_activity_logs(limit: int = 50) -> list:
    """Retorna los últimos registros de actividad para la vista de auditoría/dashboard."""
    try:
        client = _get_client()
        res = client.table('activity_log').select('*, users(full_name, username)').order('ts', desc=True).limit(limit).execute()
        return res.data or []
    except Exception as e:
        print(f"[DB] Error obteniendo activity_logs: {e}")
        return []


from datetime import datetime, timezone

def _format_iso_ts(ts_val: str | None) -> str:
    """Convierte cualquier timestamp a formato ISO 8601 compatible con PostgreSQL TIMESTAMPTZ."""
    if not ts_val:
        return datetime.now(timezone.utc).isoformat()
    ts_str = str(ts_val).strip()
    if 'T' in ts_str or (len(ts_str) >= 19 and '-' in ts_str):
        return ts_str
    # Si es solo una hora formato "09:31" o "HH:MM", formatear a timestamp ISO actual
    return datetime.now(timezone.utc).isoformat()

# ──────────────────────────────────────────────
# Conversaciones y Mensajes (Normalizados)
# ──────────────────────────────────────────────
def load_store(include_deleted: bool = False) -> dict:
    """
    Carga las conversaciones desde Supabase uniendo la tabla 'conversations'
    con los mensajes normalizados de la tabla 'messages'.
    Retorna un dict { phone: data_dict }.
    """
    try:
        client = _get_client()

        # 1. Cargar conversaciones (con fallback si no existe el FK de users aún)
        try:
            query = client.table('conversations').select('*, users(id, full_name, username)').order('updated_at', desc=True)
            if not include_deleted:
                query = query.is_('deleted_at', 'null')
            conv_res = query.execute()
        except Exception:
            query = client.table('conversations').select('*').order('updated_at', desc=True)
            if not include_deleted:
                query = query.is_('deleted_at', 'null')
            conv_res = query.execute()

        store = {}
        for row in conv_res.data or []:
            phone = row['phone']
            data = row.get('data') or {}

            # Campos estructurados con fallback a JSONB data si aplica
            name = row.get('name') or data.get('name', phone)
            avatar = row.get('avatar') or data.get('avatar', name[:2].upper())
            unread = row.get('unread') if row.get('unread') is not None else data.get('unread', 0)
            last_message = row.get('last_message') or data.get('last_message', '')
            last_ts = row.get('last_ts') or data.get('last_ts', '')
            human_required = row.get('human_required') if row.get('human_required') is not None else data.get('human_required', False)
            assigned_to = row.get('assigned_to')
            assigned_user_name = row.get('users', {}).get('full_name') if row.get('users') else None

            store[phone] = {
                "name": name,
                "avatar": avatar,
                "messages": [],
                "unread": unread or 0,
                "last_message": last_message,
                "last_ts": last_ts,
                "human_required": human_required,
                "assigned_to": assigned_to,
                "assigned_user_name": assigned_user_name,
                "last_trigger": data.get("last_trigger", ""),
                "wa_id": data.get("wa_id", ""),
                "real_phone": data.get("real_phone", ""),
                "display_phone": data.get("display_phone", phone),
                "aula_info": data.get("aula_info", {})
            }

        if not store:
            return {}

        # 2. Cargar mensajes normalizados de la tabla 'messages'
        try:
            msg_query = client.table('messages').select('*').is_('deleted_at', 'null').order('ts', desc=False).limit(10000)
            msg_res = msg_query.execute()
            messages_by_phone = {}
            for m in msg_res.data or []:
                p = m['conversation_phone']
                if p not in messages_by_phone:
                    messages_by_phone[p] = []
                msg_item = {
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
                }
                if m.get('media_type'): msg_item['media_type'] = m.get('media_type')
                if m.get('media_url'): msg_item['media_url'] = m.get('media_url')
                if m.get('filename'): msg_item['filename'] = m.get('filename')
                if m.get('transcription'): msg_item['transcription'] = m.get('transcription')
                messages_by_phone[p].append(msg_item)

            # Asociar mensajes a cada conversación (con coincidencia de teléfono normalizado)
            for msg_phone, msgs in messages_by_phone.items():
                norm_msg_phone = normalize_phone_number(msg_phone)
                matched_key = None
                for store_phone in store.keys():
                    if store_phone == msg_phone or store_phone == norm_msg_phone or normalize_phone_number(store_phone) == norm_msg_phone:
                        matched_key = store_phone
                        break
                if matched_key:
                    store[matched_key]["messages"] = msgs

            # Fallback o fusión con mensajes en JSON para preservar atributos multimedia
            for row in (conv_res.data or []):
                phone = row['phone']
                if phone in store:
                    data = row.get('data') or {}
                    json_messages = data.get('messages', [])
                    if json_messages:
                        if not store[phone].get("messages"):
                            store[phone]["messages"] = json_messages
                        else:
                            # Fusionar metadatos multimedia de json_messages si faltan
                            current_list = store[phone]["messages"]
                            for jm in json_messages:
                                jid = jm.get('id') or jm.get('wa_message_id')
                                jbody = jm.get('body')
                                jts = jm.get('ts')
                                # Buscar coincidencia por id, wa_message_id o cuerpo+ts
                                for cur in current_list:
                                    if (jid and (cur.get('id') == jid or cur.get('wa_message_id') == jid)) or (jbody and cur.get('body') == jbody and cur.get('direction') == jm.get('direction')):
                                        for mk in ['media_type', 'media_url', 'filename', 'transcription']:
                                            if jm.get(mk) and not cur.get(mk):
                                                cur[mk] = jm.get(mk)
                                        break

            # Ordenar los mensajes de cada conversación cronológicamente
            for phone_key in list(store.keys()):
                def _parse_ts_m(m):
                    ts_val = m.get('ts') or ''
                    try:
                        return datetime.fromisoformat(str(ts_val).replace('Z', '+00:00')).timestamp()
                    except Exception:
                        return 0.0
                store[phone_key]["messages"].sort(key=_parse_ts_m)

        except Exception as msg_err:
            print(f"[DB] Aviso cargando mensajes normalizados: {msg_err}")

        return store
    except Exception as e:
        print(f"[DB] Error cargando conversaciones: {e}")
        return {}


def normalize_phone_number(phone: str) -> str:
    """
    Normaliza un número de teléfono a formato E.164 (+57XXXXXXXXXX).
    Si es un identificador de privacidad de Meta (ej: CO.123...), lo conserva tal cual.
    """
    if not phone:
        return ''
    cleaned = str(phone).strip()
    if cleaned.startswith('+') and cleaned[1:].isdigit():
        return cleaned
    if cleaned.isdigit():
        return '+' + cleaned
    # Si contiene caracteres de formato pero es número real
    digits = ''.join(c for c in cleaned if c.isdigit())
    if digits and len(digits) >= 8:
        return '+' + digits
    return cleaned


def add_message(
    phone: str,
    direction: str,
    body: str,
    ts: str = None,
    ia_generated: bool = False,
    disparador: str = None,
    wa_sent: bool = True,
    simulado: bool = False,
    msg_id: str = None,
    wa_message_id: str = None,
    status: str = 'sent'
) -> dict:
    """
    Inserta un mensaje individual en la tabla normalizada 'messages'.
    Utiliza `wa_message_id` para garantizar idempotencia y prevenir duplicados
    provocados por reintentos de webhooks de WhatsApp.
    """
    norm_phone = normalize_phone_number(phone)
    wa_id = wa_message_id or msg_id

    try:
        client = _get_client()
        payload = {
            'conversation_phone': norm_phone,
            'direction': direction,
            'body': body,
            'ia_generated': ia_generated,
            'disparador': disparador,
            'wa_sent': wa_sent,
            'simulado': simulado,
            'deleted_at': None
        }
        if wa_id:
            payload['wa_message_id'] = str(wa_id)
        if ts:
            payload['ts'] = _format_iso_ts(ts)

        try:
            payload_with_status = dict(payload)
            payload_with_status['status'] = status
            res = client.table('messages').insert(payload_with_status).execute()
            return res.data[0] if res.data else payload
        except Exception as st_err:
            if 'PGRST204' in str(st_err) or 'status' in str(st_err):
                res = client.table('messages').insert(payload).execute()
                return res.data[0] if res.data else payload
            raise st_err
    except Exception as e:
        err_str = str(e)
        if 'duplicate' in err_str.lower() or '23505' in err_str or 'wa_message_id' in err_str:
            print(f"[DB] Mensaje duplicado omitido (idempotencia webhook wa_message_id={wa_id})")
        else:
            print(f"[DB] Error insertando mensaje individual para {norm_phone}: {e}")
        return {'conversation_phone': norm_phone, 'direction': direction, 'body': body, 'status': status}


def update_message_status(wa_message_id: str, status: str) -> bool:
    """
    Actualiza el estado del visto de WhatsApp ('sent', 'delivered', 'read', 'failed')
    para un mensaje por su wa_message_id o id interno.
    """
    if not wa_message_id:
        return False
    try:
        client = _get_client()
        wa_str = str(wa_message_id)
        res = client.table('messages').update({'status': status}).eq('wa_message_id', wa_str).execute()
        if not res.data:
            client.table('messages').update({'status': status}).eq('id', wa_str).execute()
        return True
    except Exception as e:
        print(f"[DB] Error actualizando estado de mensaje {wa_message_id} a '{status}': {e}")
        return False



def save_conversation(phone: str, data: dict) -> None:
    """
    Inserta o actualiza la metadata de una conversación en columnas estructuradas
    utilizando el teléfono normalizado E.164.
    """
    norm_phone = normalize_phone_number(phone)
    try:
        client = _get_client()

        # Preservar los últimos 100 mensajes en data JSONB para respaldar metadatos multimedia
        light_data = {k: v for k, v in data.items() if k != 'messages'}
        if data.get('messages'):
            light_data['messages'] = data['messages'][-100:]

        row = {
            'phone': norm_phone,
            'name': data.get('name'),
            'avatar': data.get('avatar'),
            'unread': data.get('unread', 0),
            'last_message': data.get('last_message', ''),
            'last_ts': _format_iso_ts(data.get('last_ts')),
            'human_required': data.get('human_required', False),
            'assigned_to': data.get('assigned_to'),
            'data': light_data,
            'updated_at': 'now()',
            'deleted_at': None
        }
        client.table('conversations').upsert(row).execute()
        client.table('messages').update({'deleted_at': None}).or_(f"conversation_phone.eq.{phone},conversation_phone.eq.{norm_phone}").execute()
    except Exception as e:
        print(f"[DB] Error guardando conversación {norm_phone}: {e}")



def assign_conversation(phone: str, user_id: int | None) -> bool:
    """Asigna o desasigna un asesor (user_id) a una conversación."""
    try:
        client = _get_client()
        client.table('conversations').update({
            'assigned_to': user_id,
            'updated_at': 'now()'
        }).eq('phone', phone).execute()
        return True
    except Exception as e:
        print(f"[DB] Error asignando conversación {phone} a asesor {user_id}: {e}")
        return False


def save_store(store: dict) -> None:
    """
    Guarda las conversaciones y sus mensajes en la BD.
    Úsalo en inicializaciones o migraciones.
    """
    for phone, data in store.items():
        save_conversation(phone, data)
        for m in data.get('messages', []):
            add_message(
                phone=phone,
                direction=m.get('direction', 'in'),
                body=m.get('body', ''),
                ts=m.get('ts'),
                ia_generated=m.get('ia_generated', False),
                disparador=m.get('disparador'),
                wa_sent=m.get('wa_sent', True),
                simulado=m.get('simulado', False),
                msg_id=m.get('id')
            )


def delete_conversation(phone: str) -> None:
    """Realiza Soft Delete marcando deleted_at en la conversación y sus mensajes."""
    norm_phone = normalize_phone_number(phone)
    try:
        client = _get_client()
        now_iso = datetime.now(timezone.utc).isoformat()
        
        # Eliminar conversación en Supabase
        client.table('conversations').update({'deleted_at': now_iso}).eq('phone', phone).execute()
        if norm_phone and norm_phone != phone:
            client.table('conversations').update({'deleted_at': now_iso}).eq('phone', norm_phone).execute()

        # Eliminar mensajes en Supabase
        client.table('messages').update({'deleted_at': now_iso}).eq('conversation_phone', phone).execute()
        if norm_phone and norm_phone != phone:
            client.table('messages').update({'deleted_at': now_iso}).eq('conversation_phone', norm_phone).execute()

        print(f"[DB] Conversación {phone} ({norm_phone}) y sus mensajes marcados como inactivos (Soft Delete).")
    except Exception as e:
        print(f"[DB] Error marcando inactiva conversación {phone}: {e}")


def restore_conversation(phone: str) -> bool:
    """Restaura una conversación previamente eliminada (Soft Delete)."""
    try:
        client = _get_client()
        client.table('conversations').update({'deleted_at': None}).eq('phone', phone).execute()
        client.table('messages').update({'deleted_at': None}).eq('conversation_phone', phone).execute()
        return True
    except Exception as e:
        print(f"[DB] Error restaurando conversación {phone}: {e}")
        return False



# ──────────────────────────────────────────────
# AI Prompts por Aula
# ──────────────────────────────────────────────
def get_ai_prompts(include_deleted: bool = False) -> list:
    """Retorna todos los prompts configurados por aula."""
    try:
        client = _get_client()
        query = client.table('ai_prompts').select('*')
        if not include_deleted:
            query = query.is_('deleted_at', 'null')
        res = query.order('aula_nombre').execute()
        return res.data or []
    except Exception as e:
        print(f"[DB] Error obteniendo ai_prompts: {e}")
        return []


def get_ai_prompt_by_aula(aula_id: str) -> dict | None:
    """Retorna el prompt configurado para un aula_id específico si está activo y no eliminado."""
    try:
        client = _get_client()
        res = (
            client.table('ai_prompts')
            .select('*')
            .eq('aula_id', str(aula_id))
            .is_('deleted_at', 'null')
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[DB] Error obteniendo prompt para aula {aula_id}: {e}")
        return None


def save_ai_prompt(aula_id: str, aula_nombre: str, prompt: str, activo: bool = True) -> bool:
    """Inserta o actualiza (upsert) el prompt de un aula."""
    try:
        client = _get_client()
        client.table('ai_prompts').upsert({
            'aula_id':     str(aula_id),
            'aula_nombre': aula_nombre,
            'prompt':      prompt,
            'activo':      activo,
            'updated_at':  'now()',
            'deleted_at':  None
        }, on_conflict='aula_id').execute()
        return True
    except Exception as e:
        print(f"[DB] Error guardando prompt para aula {aula_id}: {e}")
        return False


def delete_ai_prompt(aula_id: str) -> bool:
    """Realiza Soft Delete al prompt de un aula."""
    try:
        client = _get_client()
        client.table('ai_prompts').update({'deleted_at': 'now()', 'activo': False}).eq('aula_id', str(aula_id)).execute()
        return True
    except Exception as e:
        print(f"[DB] Error eliminando prompt para aula {aula_id}: {e}")
        return False


def restore_ai_prompt(aula_id: str) -> bool:
    """Restaura un prompt de aula previamente eliminado."""
    try:
        client = _get_client()
        client.table('ai_prompts').update({'deleted_at': None, 'activo': True}).eq('aula_id', str(aula_id)).execute()
        return True
    except Exception as e:
        print(f"[DB] Error restaurando prompt aula {aula_id}: {e}")
        return False


def toggle_ai_prompt(aula_id: str, activo: bool) -> bool:
    """Activa o desactiva el prompt de un aula."""
    try:
        client = _get_client()
        client.table('ai_prompts').update({'activo': activo}).eq('aula_id', str(aula_id)).execute()
        return True
    except Exception as e:
        print(f"[DB] Error toggling prompt aula {aula_id}: {e}")
        return False


# ──────────────────────────────────────────────
# AI Config por Conversación
# ──────────────────────────────────────────────
def get_ai_conversation_config(phone: str) -> dict | None:
    """Retorna la configuración de IA para una conversación (enabled/disabled)."""
    try:
        client = _get_client()
        res = (
            client.table('ai_conversation_config')
            .select('*')
            .eq('phone', phone)
            .is_('deleted_at', 'null')
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[DB] Error obteniendo ai_conversation_config para {phone}: {e}")
        return None


def set_ai_conversation_enabled(phone: str, enabled: bool) -> bool:
    """Activa o desactiva la IA para una conversación específica."""
    try:
        client = _get_client()
        client.table('ai_conversation_config').upsert({
            'phone':      phone,
            'ai_enabled': enabled,
            'updated_at': 'now()',
            'deleted_at': None
        }, on_conflict='phone').execute()
        return True
    except Exception as e:
        print(f"[DB] Error seteando ai_conversation_config para {phone}: {e}")
        return False


# ──────────────────────────────────────────────
# Exportación de Base de Datos para Migración
# ──────────────────────────────────────────────
def export_all_tables() -> dict:
    """
    Exporta los datos de todas las tablas de la BD para migración/backup.
    Retorna un diccionario estructurado por tabla.
    """
    exported = {}
    tables = ['conversations', 'messages', 'users', 'ai_prompts', 'ai_conversation_config', 'activity_log']
    client = _get_client()
    for tbl in tables:
        try:
            res = client.table(tbl).select('*').execute()
            # Omitir contraseñas sensibles en users al exportar o conservarlas hasheadas
            data = res.data or []
            exported[tbl] = data
        except Exception as e:
            print(f"[DB] Error exportando tabla {tbl}: {e}")
            exported[tbl] = []
    return exported



