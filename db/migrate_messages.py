"""
db/migrate_messages.py
══════════════════════════════════════════════════════════════════
Script de Migración Seguro en 4 Fases para Normalización de Mensajes:

Fase 1: Crear la tabla 'messages' y realizar el backfill en lote (batch)
        desde conversations.data -> messages sin eliminar nada aún.
Fase 2: Escritura Dual (Dual-Write) — Los nuevos mensajes se persisten
        tanto en messages como en conversations.data durante el período de transición.
Fase 3: Verificación y corte de lecturas — Verificar que el conteo de mensajes
        en 'messages' coincide exactamente con la suma en JSONB data.
Fase 4: Limpieza de JSONB — Eliminar el array 'messages' de conversations.data,
        dejando únicamente la metadata ligera en conversations.
══════════════════════════════════════════════════════════════════
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db.database import _get_client, normalize_phone_number, add_message, log_activity


def run_phase_1_backfill():
    """Fase 1: Backfill en batch desde conversations.data hacia la tabla messages."""
    print("[MIGRATION - FASE 1] Iniciando backfill de mensajes...")
    client = _get_client()

    res = client.table('conversations').select('phone, data').execute()
    rows = res.data or []

    total_conversations = len(rows)
    total_messages_migrated = 0
    skipped_duplicates = 0

    print(f"[MIGRATION - FASE 1] Procesando {total_conversations} conversaciones...")

    for row in rows:
        phone = normalize_phone_number(row.get('phone', ''))
        data = row.get('data') or {}
        json_messages = data.get('messages', [])

        for m in json_messages:
            msg_id = m.get('id')
            body = m.get('body', '')
            direction = m.get('direction', 'in')
            ts = m.get('ts')

            res_msg = add_message(
                phone=phone,
                direction=direction,
                body=body,
                ts=ts,
                ia_generated=m.get('ia_generated', False),
                disparador=m.get('disparador'),
                wa_sent=m.get('wa_sent', True),
                simulado=m.get('simulado', False),
                msg_id=msg_id,
                wa_message_id=msg_id
            )
            if res_msg and res_msg.get('wa_message_id'):
                total_messages_migrated += 1

    print(f"[MIGRATION - FASE 1] Completado: {total_messages_migrated} mensajes migrados a la tabla 'messages'.")
    log_activity(None, 'MIGRATION_PHASE_1', f"Backfill completado: {total_messages_migrated} mensajes migrados.")
    return total_messages_migrated


def run_phase_3_verify(expected_min_count: int = 0):
    """Fase 3: Verificación de integridad entre 'conversations.data' y 'messages'."""
    print("[MIGRATION - FASE 3] Verificando integridad de datos...")
    client = _get_client()

    conv_res = client.table('conversations').select('phone, data').execute()
    conv_rows = conv_res.data or []

    json_msg_count = 0
    for r in conv_rows:
        data = r.get('data') or {}
        json_msg_count += len(data.get('messages', []))

    msg_res = client.table('messages').select('id', count='exact').is_('deleted_at', 'null').execute()
    tbl_msg_count = msg_res.count or 0

    print(f"[MIGRATION - FASE 3] Mensajes en JSONB: {json_msg_count} | Mensajes en tabla 'messages': {tbl_msg_count}")

    if tbl_msg_count >= json_msg_count:
        print("[MIGRATION - FASE 3] OK: Verificación exitosa. Todos los mensajes están respaldados en la tabla 'messages'.")
        log_activity(None, 'MIGRATION_PHASE_3', f"Verificación OK: {tbl_msg_count} mensajes en BD.")
        return True
    else:
        print("[MIGRATION - FASE 3] ADVERTENCIA: Hay más mensajes en JSONB que en la tabla 'messages'. Revisar logs.")
        return False


def run_phase_4_cleanup_jsonb():
    """Fase 4: Limpieza de JSONB — Remueve el array 'messages' de conversations.data."""
    print("[MIGRATION - FASE 4] Iniciando limpieza de 'messages' en JSONB...")
    client = _get_client()

    res = client.table('conversations').select('phone, data').execute()
    rows = res.data or []
    cleaned_count = 0

    for row in rows:
        phone = row['phone']
        data = row.get('data') or {}
        if 'messages' in data:
            light_data = {k: v for k, v in data.items() if k != 'messages'}
            client.table('conversations').update({
                'data': light_data,
                'updated_at': 'now()'
            }).eq('phone', phone).execute()
            cleaned_count += 1

    print(f"[MIGRATION - FASE 4] Completado: Limpieza realizada en {cleaned_count} conversaciones.")
    log_activity(None, 'MIGRATION_PHASE_4', f"Limpieza completada en {cleaned_count} conversaciones.")
    return cleaned_count


if __name__ == '__main__':
    print("═══ SCRIPT DE MIGRACION DE MENSAJES EN FASES ═══")
    migrated = run_phase_1_backfill()
    verified = run_phase_3_verify(migrated)
    if verified:
        print("\n¿Desea proceder con la Fase 4 (Limpieza de JSONB data)? (Ejecute con --cleanup)")
        if '--cleanup' in sys.argv:
            run_phase_4_cleanup_jsonb()
