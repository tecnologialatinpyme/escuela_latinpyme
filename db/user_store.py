"""
db/user_store.py
══════════════════════════════════════════════════════════════════
CRUD de usuarios del sistema (asesores, admins).
Usa el cliente supabase-py via HTTPS y bcrypt para contraseñas.
══════════════════════════════════════════════════════════════════
"""
import os
import bcrypt
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
                "SUPABASE_URL o SUPABASE_SECRET_KEY no están configuradas."
            )
        from supabase import create_client
        _client = create_client(_SUPABASE_URL, _SUPABASE_KEY)
    return _client


# ──────────────────────────────────────────────
# Contraseñas
# ──────────────────────────────────────────────
def hash_password(plain: str) -> str:
    """Retorna el hash bcrypt de una contraseña en texto plano."""
    return bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def check_password(plain: str, hashed: str) -> bool:
    """Verifica si la contraseña en texto plano coincide con el hash."""
    return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))


# ──────────────────────────────────────────────
# Lectura
# ──────────────────────────────────────────────
def get_user_by_id(user_id: int) -> dict | None:
    try:
        client = _get_client()
        response = client.table('users').select('*').eq('id', user_id).single().execute()
        return response.data
    except Exception as e:
        print(f"[USER_STORE] get_user_by_id error: {e}")
        return None


def get_user_by_username(username: str) -> dict | None:
    try:
        client = _get_client()
        response = client.table('users').select('*').eq('username', username).execute()
        if response.data:
            return response.data[0]
        return None
    except Exception as e:
        print(f"[USER_STORE] get_user_by_username error: {e}")
        return None


def list_users() -> list[dict]:
    try:
        client = _get_client()
        response = client.table('users').select(
            'id, username, email, full_name, role, is_active, created_at, last_login'
        ).order('created_at').execute()
        return response.data or []
    except Exception as e:
        print(f"[USER_STORE] list_users error: {e}")
        return []


def count_users() -> int:
    try:
        client = _get_client()
        response = client.table('users').select('id', count='exact').execute()
        return response.count or 0
    except Exception:
        return 0


# ──────────────────────────────────────────────
# Escritura
# ──────────────────────────────────────────────
def create_user(username: str, email: str, password: str, full_name: str, role: str = 'asesor') -> dict | None:
    """
    Crea un nuevo usuario con contraseña hasheada.
    Retorna el usuario creado o None si hay error (ej: username duplicado).
    """
    hashed = hash_password(password)
    try:
        client = _get_client()
        response = client.table('users').insert({
            'username': username,
            'email': email,
            'password': hashed,
            'full_name': full_name,
            'role': role,
        }).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        err_str = str(e)
        if 'duplicate' in err_str.lower() or '23505' in err_str:
            print(f"[USER_STORE] Usuario o email duplicado: {username} / {email}")
        else:
            print(f"[USER_STORE] create_user error: {e}")
        return None


def update_user(user_id: int, full_name: str = None, email: str = None, role: str = None) -> bool:
    """Actualiza datos no críticos de un usuario."""
    updates = {}
    if full_name is not None:
        updates['full_name'] = full_name
    if email is not None:
        updates['email'] = email
    if role is not None:
        updates['role'] = role
    if not updates:
        return False
    try:
        client = _get_client()
        client.table('users').update(updates).eq('id', user_id).execute()
        return True
    except Exception as e:
        print(f"[USER_STORE] update_user error: {e}")
        return False


def reset_password(user_id: int, new_password: str) -> bool:
    """Resetea la contraseña de un usuario."""
    hashed = hash_password(new_password)
    try:
        client = _get_client()
        client.table('users').update({'password': hashed}).eq('id', user_id).execute()
        return True
    except Exception as e:
        print(f"[USER_STORE] reset_password error: {e}")
        return False


def toggle_user(user_id: int) -> bool | None:
    """
    Activa o desactiva un usuario (toggle).
    Retorna el nuevo estado (True=activo, False=inactivo) o None si hay error.
    """
    try:
        client = _get_client()
        # Primero obtenemos el estado actual
        current = client.table('users').select('is_active').eq('id', user_id).single().execute()
        if not current.data:
            return None
        new_state = not current.data['is_active']
        client.table('users').update({'is_active': new_state}).eq('id', user_id).execute()
        return new_state
    except Exception as e:
        print(f"[USER_STORE] toggle_user error: {e}")
        return None


def update_last_login(user_id: int) -> None:
    """Registra el timestamp del último login exitoso."""
    try:
        from datetime import datetime, timezone
        client = _get_client()
        client.table('users').update({
            'last_login': datetime.now(timezone.utc).isoformat()
        }).eq('id', user_id).execute()
    except Exception as e:
        print(f"[USER_STORE] update_last_login error: {e}")
