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
def load_store() -> dict:
    """
    Carga todas las conversaciones desde Supabase.
    Retorna un dict { phone: data_dict }.
    """
    try:
        client = _get_client()
        response = client.table('conversations').select('phone, data').execute()
        return {row['phone']: row['data'] for row in response.data}
    except Exception as e:
        print(f"[DB] Error cargando conversaciones: {e}")
        return {}


def save_conversation(phone: str, data: dict) -> None:
    """
    Inserta o actualiza (upsert) una sola conversación.
    """
    try:
        client = _get_client()
        client.table('conversations').upsert({
            'phone': phone,
            'data': data,
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
        rows = [{'phone': phone, 'data': data} for phone, data in store.items()]
        if rows:
            client.table('conversations').upsert(rows).execute()
    except Exception as e:
        print(f"[DB] Error en save_store: {e}")


def delete_conversation(phone: str) -> None:
    """Elimina permanentemente una conversación de la BD."""
    try:
        client = _get_client()
        client.table('conversations').delete().eq('phone', phone).execute()
    except Exception as e:
        print(f"[DB] Error eliminando conversación {phone}: {e}")
