"""
db/contact_store.py
══════════════════════════════════════════════════════════════════
CRUD de Contactos de la Escuela LatinPyme.
Sincronización automática con conversaciones de WhatsApp y Aulas.
══════════════════════════════════════════════════════════════════
"""
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from db.database import _get_client, normalize_phone_number, log_activity

load_dotenv()


def sync_contacts_from_conversations() -> list[dict]:
    """
    Recorre todas las conversaciones registradas en el sistema y garantiza que
    cada una tenga su correspondiente ficha de contacto guardada en la base de datos.
    """
    try:
        from db import database as db
        store = db.load_store()
        synced_contacts = []
        for phone_key, data in store.items():
            if not phone_key:
                continue
            norm_phone = normalize_phone_number(phone_key)
            name = data.get('name') or norm_phone
            aula_info = data.get('aula_info') or {}
            email = data.get('email') or aula_info.get('email') or aula_info.get('email_usuario')
            company = data.get('company') or aula_info.get('client') or aula_info.get('empresa_patrocinadora')
            aula_id = aula_info.get('space_id') or aula_info.get('aula_id')
            aula_nombre = aula_info.get('aula_nombre') or aula_info.get('client')

            c = upsert_contact_from_conversation(
                phone=norm_phone,
                name=name,
                email=email,
                company=company,
                aula_id=aula_id,
                aula_nombre=aula_nombre
            )
            if c:
                synced_contacts.append(c)
            else:
                synced_contacts.append({
                    "id": norm_phone,
                    "phone": norm_phone,
                    "name": name,
                    "email": email,
                    "company": company,
                    "aula_id": str(aula_id) if aula_id else None,
                    "aula_nombre": aula_nombre,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                })
        return synced_contacts
    except Exception as e:
        print(f"[CONTACT_STORE] sync_contacts_from_conversations error: {e}")
        return []


def list_contacts(query: str = None, include_deleted: bool = False, limit: int = 200) -> list[dict]:
    """Retorna la lista de contactos ordenados por última actualización."""
    try:
        # Sincronizar automáticamente cualquier conversación existente hacia la tabla de contactos
        sync_contacts_from_conversations()

        client = _get_client()
        req = client.table('contacts').select('*')
        if not include_deleted:
            req = req.is_('deleted_at', 'null')
        req = req.order('updated_at', desc=True).limit(limit)
        res = req.execute()
        contacts = res.data or []

        if not contacts:
            contacts = sync_contacts_from_conversations()

        if query:
            q = str(query).lower().strip()
            filtered = []
            for c in contacts:
                name_match = q in str(c.get('name', '')).lower()
                phone_match = q in str(c.get('phone', '')).lower()
                email_match = q in str(c.get('email', '')).lower()
                company_match = q in str(c.get('company', '')).lower()
                aula_match = q in str(c.get('aula_nombre', '')).lower()
                if name_match or phone_match or email_match or company_match or aula_match:
                    filtered.append(c)
            return filtered

        return contacts
    except Exception as e:
        print(f"[CONTACT_STORE] list_contacts error: {e}")
        return sync_contacts_from_conversations()


def get_contact_by_phone(phone: str) -> dict | None:
    """Busca un contacto por su número telefónico normalizado."""
    norm_phone = normalize_phone_number(phone)
    if not norm_phone:
        return None
    try:
        client = _get_client()
        res = client.table('contacts').select('*').eq('phone', norm_phone).is_('deleted_at', 'null').limit(1).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[CONTACT_STORE] get_contact_by_phone error: {e}")
        return None


def get_contact_by_id(contact_id) -> dict | None:
    """Busca un contacto por su ID numérico o por su teléfono."""
    try:
        client = _get_client()
        cid_str = str(contact_id).strip()
        if cid_str.isdigit():
            res = client.table('contacts').select('*').eq('id', int(cid_str)).is_('deleted_at', 'null').limit(1).execute()
        else:
            res = client.table('contacts').select('*').eq('phone', cid_str).is_('deleted_at', 'null').limit(1).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"[CONTACT_STORE] get_contact_by_id error: {e}")
        return None


def upsert_contact_from_conversation(
    phone: str,
    name: str = None,
    email: str = None,
    company: str = None,
    cargo: str = None,
    ciudad: str = None,
    aula_id: str = None,
    aula_nombre: str = None
) -> dict | None:
    """
    Crea o actualiza automáticamente una ficha de contacto cuando un usuario escribe
    o cuando la API de Aulas provee datos del estudiante.
    """
    norm_phone = normalize_phone_number(phone)
    if not norm_phone:
        return None

    try:
        client = _get_client()
        existing = get_contact_by_phone(norm_phone)

        now_iso = datetime.now(timezone.utc).isoformat()

        if existing:
            # Actualizar campos cuando son provistos
            updates = {'updated_at': 'now()', 'deleted_at': None}
            if name and name != norm_phone:
                updates['name'] = name.strip()

            if email:
                updates['email'] = email.strip()
            if company:
                updates['company'] = company.strip()
            if cargo:
                updates['cargo'] = cargo.strip()
            if ciudad:
                updates['ciudad'] = ciudad.strip()
            if aula_id:
                updates['aula_id'] = str(aula_id).strip()
            if aula_nombre:
                updates['aula_nombre'] = aula_nombre.strip()

            client.table('contacts').update(updates).eq('id', existing['id']).execute()
            return {**existing, **updates}
        else:
            # Crear nuevo contacto automático
            contact_name = name.strip() if (name and name != norm_phone) else norm_phone
            new_payload = {
                'phone': norm_phone,
                'name': contact_name,
                'email': email.strip() if email else None,
                'company': company.strip() if company else None,
                'cargo': cargo.strip() if cargo else None,
                'ciudad': ciudad.strip() if ciudad else None,
                'aula_id': str(aula_id).strip() if aula_id else None,
                'aula_nombre': aula_nombre.strip() if aula_nombre else None,
                'created_at': now_iso,
                'updated_at': now_iso,
                'deleted_at': None
            }
            res = client.table('contacts').insert(new_payload).execute()
            print(f"[CONTACT_STORE] Contacto creado automáticamente para {norm_phone} ({contact_name})")
            return res.data[0] if res.data else new_payload

    except Exception as e:
        print(f"[CONTACT_STORE] upsert_contact_from_conversation error: {e}")
        return None


def create_contact(
    phone: str,
    name: str,
    email: str = None,
    company: str = None,
    cargo: str = None,
    ciudad: str = None,
    aula_id: str = None,
    aula_nombre: str = None
) -> dict | None:
    """Crea un contacto manualmente desde la interfaz web."""
    norm_phone = normalize_phone_number(phone)
    if not norm_phone or not name:
        return None

    try:
        client = _get_client()
        payload = {
            'phone': norm_phone,
            'name': name.strip(),
            'email': email.strip() if email else None,
            'company': company.strip() if company else None,
            'cargo': cargo.strip() if cargo else None,
            'ciudad': ciudad.strip() if ciudad else None,
            'aula_id': str(aula_id).strip() if aula_id else None,
            'aula_nombre': aula_nombre.strip() if aula_nombre else None,
            'updated_at': 'now()',
            'deleted_at': None
        }
        res = client.table('contacts').upsert(payload, on_conflict='phone').execute()
        log_activity(None, 'CREATE_CONTACT', f"Contacto creado/actualizado: {norm_phone} ({name})")
        return res.data[0] if res.data else payload
    except Exception as e:
        print(f"[CONTACT_STORE] create_contact error: {e}")
        return None


def update_contact(contact_id, data: dict) -> bool:
    """Actualiza la información de un contacto existente por su ID o Teléfono."""
    if not contact_id or not data:
        return False

    updates = {}
    allowed_keys = ['name', 'email', 'company', 'cargo', 'ciudad', 'aula_id', 'aula_nombre', 'phone']
    for k in allowed_keys:
        if k in data:
            if k == 'phone':
                updates[k] = normalize_phone_number(data[k])
            else:
                updates[k] = str(data[k]).strip() if data[k] is not None else None

    if not updates:
        return False

    updates['updated_at'] = 'now()'

    try:
        client = _get_client()
        cid_str = str(contact_id).strip()
        if cid_str.isdigit():
            client.table('contacts').update(updates).eq('id', int(cid_str)).execute()
        else:
            client.table('contacts').update(updates).eq('phone', cid_str).execute()
        log_activity(None, 'UPDATE_CONTACT', f"Contacto {contact_id} actualizado.")
        return True
    except Exception as e:
        print(f"[CONTACT_STORE] update_contact error: {e}")
        return False


def delete_contact(contact_id) -> bool:
    """Realiza Soft Delete marcando deleted_at en el contacto por ID o Teléfono."""
    try:
        client = _get_client()
        cid_str = str(contact_id).strip()
        if cid_str.isdigit():
            client.table('contacts').update({'deleted_at': 'now()'}).eq('id', int(cid_str)).execute()
        else:
            client.table('contacts').update({'deleted_at': 'now()'}).eq('phone', cid_str).execute()
        log_activity(None, 'DELETE_CONTACT', f"Contacto ID {contact_id} marcado como eliminado.")
        return True
    except Exception as e:
        print(f"[CONTACT_STORE] delete_contact error: {e}")
        return False
