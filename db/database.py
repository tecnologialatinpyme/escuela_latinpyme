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
    """
    Verifica la conexión a Supabase y crea la tabla 'conversations'
    si no existe mediante una operación de lectura segura.
    Las tablas 'users' y 'activity_log' deben crearse manualmente
    en el SQL Editor de Supabase (ver instrucciones en la consola).
    """
    try:
        client = _get_client()
        # Prueba de conexión: intentar leer la tabla conversations
        client.table('conversations').select('phone').limit(1).execute()
        print("[DB] Conexion a Supabase establecida correctamente.")
    except Exception as e:
        err_str = str(e)
        if 'relation "conversations" does not exist' in err_str or '42P01' in err_str:
            print("[DB] AVISO: La tabla 'conversations' no existe en Supabase.")
            print("[DB] >> Ejecuta el SQL del archivo db/schema.sql en el SQL Editor de Supabase")
            print("[DB]    en el SQL Editor de Supabase: https://supabase.com/dashboard/project/_/sql")
        else:
            print(f"[DB] Error de conexión a Supabase: {e}")
            raise


# ──────────────────────────────────────────────
# Conversaciones — lectura / escritura
# ──────────────────────────────────────────────
def load_store(include_deleted: bool = False) -> dict:
    """
    Carga las conversaciones desde Supabase.
    Por defecto omite las marcadas como eliminadas (soft delete).
    Retorna un dict { phone: data_dict }.
    """
    try:
        client = _get_client()
        query = client.table('conversations').select('phone, data, deleted_at')
        if not include_deleted:
            query = query.is_('deleted_at', 'null')
        response = query.execute()
        return {row['phone']: row['data'] for row in response.data if row.get('data')}
    except Exception as e:
        print(f"[DB] Error cargando conversaciones: {e}")
        return {}


def save_conversation(phone: str, data: dict) -> None:
    """
    Inserta o actualiza (upsert) una sola conversación.
    Restablece deleted_at a null para asegurar que quede activa.
    """
    try:
        client = _get_client()
        client.table('conversations').upsert({
            'phone': phone,
            'data': data,
            'updated_at': 'now()',
            'deleted_at': None
        }).execute()
    except Exception as e:
        print(f"[DB] Error guardando conversación {phone}: {e}")


def save_store(store: dict) -> None:
    """
    Sobreescribe TODAS las conversaciones.
    Úsalo solo en migraciones o inicialización de datos semilla.
    """
    try:
        client = _get_client()
        rows = [{
            'phone': phone,
            'data': data,
            'updated_at': 'now()',
            'deleted_at': None
        } for phone, data in store.items()]
        if rows:
            client.table('conversations').upsert(rows).execute()
    except Exception as e:
        print(f"[DB] Error en save_store: {e}")


def delete_conversation(phone: str) -> None:
    """Realiza Soft Delete marcando deleted_at con la fecha actual."""
    try:
        client = _get_client()
        client.table('conversations').update({'deleted_at': 'now()'}).eq('phone', phone).execute()
        print(f"[DB] Conversación {phone} marcada como inactiva (Soft Delete).")
    except Exception as e:
        print(f"[DB] Error marcando inactiva conversación {phone}: {e}")


def restore_conversation(phone: str) -> bool:
    """Restaura una conversación previamente eliminada (Soft Delete)."""
    try:
        client = _get_client()
        client.table('conversations').update({'deleted_at': None}).eq('phone', phone).execute()
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
    tables = ['conversations', 'users', 'ai_prompts', 'ai_conversation_config', 'activity_log']
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


