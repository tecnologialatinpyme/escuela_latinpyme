import json
import requests
from openai import OpenAI
from config.settings import app_config


class AiAssistantService:
    """
    Servicio de Asistente IA para WhatsApp.
    Orquesta:
    1. Buscar el aula de un usuario por número de teléfono (API externa)
    2. Obtener el prompt configurado para esa aula (BD)
    3. Generar una respuesta automática usando OpenAI
    """

    # ──────────────────────────────────────────────────────
    # 1. Buscar aula por teléfono
    # ──────────────────────────────────────────────────────
    def buscar_aula_por_telefono(self, telefono: str) -> dict:
        """
        Consulta la API externa de Aulas con el número de teléfono.
        El número se envía sin '+', con código de país (ej: 573002711932).

        Respuesta esperada de la API cuando encuentra usuario:
        {
            "userId": 901028, "id": 4, "space_id": 4,
            "client": "EduFundación Coomeva",
            "name": "Laura Camila", "lastname": "Diaz Arevalo",
            "body": "edufundacioncoomeva.com", "email": "..."
        }

        Retorna:
        {
            "encontrado": bool,
            "space_id": str | None,
            "aula_nombre": str,
            "nombre_usuario": str,
            "email": str
        }
        """
        # Limpiar número: quitar '+' y espacios
        telefono_limpio = telefono.replace('+', '').replace(' ', '').strip()

        api_url   = app_config.aulas_api_url
        api_token = app_config.aulas_api_token

        try:
            res = requests.get(
                api_url,
                params={'phone': telefono_limpio, 'token': api_token},
                timeout=8
            )
            data = res.json()
        except Exception as e:
            print(f"[AiAssistant] Error llamando API de Aulas: {e}")
            return self._usuario_no_encontrado()

        # La API retorna status 0 (no encontrado) o status 400 (inválido)
        # Cuando encuentra: devuelve userId directamente (sin campo "status")
        if 'userId' in data and data.get('userId'):
            nombre    = data.get('name', '')
            apellido  = data.get('lastname', '')
            nombre_completo = f"{nombre} {apellido}".strip() or 'Estudiante'
            space_id  = str(data.get('space_id', ''))
            client    = data.get('client', 'Aula General')
            email     = data.get('email', '')
            body_domain = data.get('body', '')

            return {
                'encontrado':    True,
                'space_id':      space_id,
                'aula_nombre':   client,
                'nombre_usuario': nombre_completo,
                'email':         email,
                'body':          body_domain,
                'dominio_aula':  body_domain,
                'raw':           data
            }
        else:
            return self._usuario_no_encontrado()

    def _usuario_no_encontrado(self) -> dict:
        return {
            'encontrado':    False,
            'space_id':      None,
            'aula_nombre':   'Aula General',
            'nombre_usuario': 'Estudiante',
            'email':         '',
            'body':          '',
            'dominio_aula':  ''
        }


    # ──────────────────────────────────────────────────────
    # 2. Obtener prompt del aula desde BD
    # ──────────────────────────────────────────────────────
    def obtener_prompt_aula(self, space_id: str) -> str | None:
        """
        Busca el prompt configurado para un space_id en la base de datos.
        Retorna None si no hay prompt configurado para ese aula.
        """
        if not space_id:
            return None
        try:
            from db.database import get_ai_prompt_by_aula
            prompt_data = get_ai_prompt_by_aula(space_id)
            if prompt_data and prompt_data.get('activo'):
                return prompt_data.get('prompt')
        except Exception as e:
            print(f"[AiAssistant] Error obteniendo prompt del aula: {e}")
        return None

    # ──────────────────────────────────────────────────────
    # 3. Construir historial de mensajes para OpenAI
    # ──────────────────────────────────────────────────────
    def _construir_historial(self, mensajes: list, limite: int = 10) -> list:
        """
        Convierte los últimos `limite` mensajes del store en formato OpenAI.
        direction: 'in' → role: 'user', 'out' → role: 'assistant'
        """
        historial = []
        ultimos = mensajes[-limite:] if len(mensajes) > limite else mensajes
        for m in ultimos:
            role = 'user' if m.get('direction') == 'in' else 'assistant'
            body = m.get('body', '').strip()
            if body:
                historial.append({'role': role, 'content': body})
        return historial

    # ──────────────────────────────────────────────────────
    # 4. Generar respuesta automática
    # ──────────────────────────────────────────────────────
    def generar_respuesta(self, telefono: str, mensajes: list, last_trigger: str = None) -> dict:
        """
        Genera una respuesta de IA para una conversación de WhatsApp.

        Parámetros:
        - telefono: Número del contacto (con o sin '+')
        - mensajes: Lista completa de mensajes de la conversación
        - last_trigger: Disparador activo en la conversación (opcional)

        Retorna:
        {
            "exito": bool,
            "respuesta": str,
            "disparador": str,
            "pausar_ia": bool,
            "aula_info": dict,
            "modo_simulacion": bool
        }
        """
        # 1. Buscar aula del usuario
        aula_info = self.buscar_aula_por_telefono(telefono)

        # 2. Cargar Prompt Maestro (General / Soporte) y Prompt de Aula / Sub-Agente
        prompt_maestro = app_config.ai_master_prompt
        prompt_aula    = None

        # A) Buscar por el disparador activo (ej: "taller_IA", "SoporteOdoo", "agente_taller_declaracion")
        if last_trigger and last_trigger != 'ninguno':
            prompt_aula = self.obtener_prompt_aula(last_trigger)

        # B) Buscar por el space_id del aula del participante (ej: "4", "115", "2")
        if not prompt_aula and aula_info['encontrado'] and aula_info['space_id']:
            prompt_aula = self.obtener_prompt_aula(aula_info['space_id'])

        # C) Fallback a prompt por defecto
        if not prompt_aula:
            prompt_aula = app_config.ai_default_prompt

        # Si el prompt del aula incluye la etiqueta {prompt_maestro}, la reemplaza allí.
        # De lo contrario, antepone el Prompt Maestro al del aula.
        if '{prompt_maestro}' in prompt_aula:
            prompt_sistema = prompt_aula.replace('{prompt_maestro}', prompt_maestro)
        elif '{prompt_general}' in prompt_aula:
            prompt_sistema = prompt_aula.replace('{prompt_general}', prompt_maestro)
        else:
            prompt_sistema = (
                f"{prompt_maestro}\n\n"
                f"=== INFORMACIÓN ESPECÍFICA DEL AULA / SUB-AGENTE: {aula_info.get('aula_nombre', 'LatinPyme')} ===\n"
                f"{prompt_aula}"
            )


        # 4. Personalizar el prompt con datos del usuario y del aula
        nombre_usuario = aula_info.get('nombre_usuario', 'Estudiante')
        aula_nombre    = aula_info.get('aula_nombre', 'LatinPyme')
        space_id       = str(aula_info.get('space_id', ''))
        dominio_aula   = aula_info.get('raw', {}).get('body', 'capacitacionaportesenlinea.com')
        email_usuario  = aula_info.get('email', '')

        replacements = {
            '{{Aula Virtual ID}}':          space_id,
            '{space_id}':                   space_id,
            '{aula_id}':                    space_id,

            '{{Dominio Aula Virtual}}':      dominio_aula,
            '{dominio_aula}':               dominio_aula,

            '{{Empresa Cliente LatinPyme}}': aula_nombre,
            '{aula}':                       aula_nombre,
            '{aula_nombre}':                aula_nombre,

            '{{Nombre Usuario}}':           nombre_usuario,
            '{nombre_usuario}':             nombre_usuario,

            '{email}':                      email_usuario
        }

        for key, val in replacements.items():
            prompt_sistema = prompt_sistema.replace(key, val)


        # 5. Construir historial de mensajes
        historial_openai = self._construir_historial(mensajes, limite=10)

        # 6. Si no hay mensajes, no hay nada que responder
        if not historial_openai:
            return {
                'exito': False,
                'respuesta': '',
                'aula_info': aula_info,
                'modo_simulacion': False,
                'error': 'Sin mensajes para procesar'
            }

        # 7. Asegurar que el último mensaje sea del usuario
        if historial_openai[-1]['role'] != 'user':
            return {
                'exito': False,
                'respuesta': '',
                'aula_info': aula_info,
                'modo_simulacion': False,
                'error': 'El último mensaje no es del usuario'
            }

        # Instuir a OpenAI para devolver respuesta y disparador en JSON
        instruction_json = (
            "\n\nFORMATO DE RESPUESTA REQUERIDO:\n"
            "Debes responder EXCLUSIVAMENTE en formato JSON estricto con la siguiente estructura:\n"
            "{\n"
            '  "respuesta": "Texto plano fluido sin markdown ni HTML de la respuesta de Isabella para WhatsApp",\n'
            '  "disparador": "Identificador exacto del disparador activado (ej: asesor_humano_soporte, SoporteOdoo, soluciones_patrocinador, ventas_cursos_abiertos, ventas_agentes_ia, codigo_aportes_en_linea, reclutamiento, encuesta_2026, agente_taller_declaracion, taller_IA, etc.) o \'ninguno\'",\n'
            '  "pausar_ia": true (solo si el contacto solicita hablar con un asesor o si se activa asesor_humano_soporte) o false\n'
            "}"
        )
        prompt_sistema += instruction_json

        # 8. Llamar a OpenAI
        api_key = app_config.openai_key
        if not api_key:
            # Modo simulación sin OpenAI Key
            return self._respuesta_simulada(aula_info, historial_openai)

        try:
            client = OpenAI(api_key=api_key)
            res = client.chat.completions.create(
                model=app_config.openai_model,
                messages=[
                    {'role': 'system', 'content': prompt_sistema},
                    *historial_openai
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=600,
                timeout=15
            )
            raw_content = res.choices[0].message.content.strip()
            data_json   = json.loads(raw_content)

            respuesta_texto = str(data_json.get("respuesta", raw_content)).strip()
            disparador      = str(data_json.get("disparador", "ninguno")).strip()
            pausar_ia       = bool(data_json.get("pausar_ia", False) or disparador == "asesor_humano_soporte")

            return {
                'exito': True,
                'respuesta': respuesta_texto,
                'disparador': disparador,
                'pausar_ia': pausar_ia,
                'aula_info': aula_info,
                'modo_simulacion': False
            }
        except Exception as e:
            print(f"[AiAssistant] Error en OpenAI completion: {e}")
            return self._respuesta_simulada(aula_info, historial_openai)


    # ──────────────────────────────────────────────────────
    # 5. Respuesta simulada (fallback sin OpenAI Key)
    # ──────────────────────────────────────────────────────
    def _respuesta_simulada(self, aula_info: dict, historial: list) -> dict:
        """Respuesta de fallback cuando no hay API Key de OpenAI configurada."""
        nombre = aula_info.get('nombre_usuario', 'Estudiante')
        aula   = aula_info.get('aula_nombre', 'LatinPyme')
        ultimo_msg = historial[-1]['content'] if historial else ''

        respuesta = (
            f"Hola {nombre}, gracias por escribirnos desde {aula}. "
            f"Recibimos tu mensaje: \"{ultimo_msg[:80]}...\". "
            f"Un asesor de LatinPyme te contactará en breve. 🎓"
        )
        return {
            'exito': True,
            'respuesta': respuesta,
            'aula_info': aula_info,
            'modo_simulacion': True
        }

    # ──────────────────────────────────────────────────────
    # 6. Verificar si IA está habilitada para una conversación
    # ──────────────────────────────────────────────────────
    def esta_habilitada_para_conversacion(self, phone: str) -> bool:
        """
        Verifica si la IA está habilitada para una conversación específica.
        Primero chequea el flag global, luego el estado individual.
        """
        if not app_config.ai_assistant_enabled:
            return False
        try:
            from db.database import get_ai_conversation_config
            config = get_ai_conversation_config(phone)
            # Si no hay registro, por defecto está habilitada
            if config is None:
                return True
            return config.get('ai_enabled', True)
        except Exception:
            return True
