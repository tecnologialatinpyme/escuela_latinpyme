"""Script para reparar routes/conversations.py"""
import re

with open('routes/conversations.py', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# La línea corrupta empieza con 'value = change.get' y tiene \n literales
# La reemplazamos con el bloque correcto
STATUS_BLOCK = """                value = change.get('value', {})

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
                for msg in value.get('messages', []):"""

# Encontrar y reemplazar la línea corrupta (que contiene \\n literales)
lines = content.split('\n')
new_lines = []
replaced = False
for i, line in enumerate(lines):
    if '\\n' in line and "value = change.get('value'" in line and not replaced:
        # Reemplazar con el bloque correcto
        new_lines.append(STATUS_BLOCK)
        replaced = True
        print(f"Línea {i+1} reemplazada correctamente")
    else:
        new_lines.append(line)

new_content = '\n'.join(new_lines)

# Verificar sintaxis
import ast
try:
    ast.parse(new_content)
    print("SINTAXIS OK - guardando archivo")
    with open('routes/conversations.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Archivo guardado.")
except SyntaxError as e:
    print(f"SINTAXIS ERROR: {e}")
    print("No se guardó el archivo.")
