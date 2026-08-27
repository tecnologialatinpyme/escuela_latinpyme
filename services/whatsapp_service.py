import time
import json
import requests
from config.settings import app_config

class WhatsAppService:
    """
    Servicio de integración con la API oficial de WhatsApp Cloud de Meta.
    Soporta envíos reales de plantillas y de texto plano, consulta de plantillas,
    y un modo simulación cuando no hay credenciales configuradas.
    """

    def _get_api_headers(self) -> dict:
        """Devuelve los cabezales necesarios para consultar a Meta."""
        token = app_config.meta_wa_token
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

    def enviar_mensaje_plantilla(self, telefono: str, plantilla_nombre: str, parametros: list) -> dict:
        """
        Envía un mensaje de WhatsApp basado en una plantilla aprobada por Meta.
        
        Parámetros:
        - telefono: Número de destino en formato E.164 (ej: +573144187269).
        - plantilla_nombre: Nombre de la plantilla en Meta (ej: plantilla_curso_latinpyme).
        - parametros: Lista de strings con los valores para reemplazar {{1}}, {{2}}, etc.
        """
        # Limpiar el '+' si la API de Meta no lo requiere (Meta WhatsApp Cloud API prefiere números limpios sin el '+')
        telefono_limpio = telefono.replace("+", "").strip()
        
        token = app_config.meta_wa_token
        phone_id = app_config.meta_wa_phone_id
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": telefono_limpio,
            "type": "template",
            "template": {
                "name": plantilla_nombre,
                "language": {
                    "code": "es"
                }
            }
        }
        
        # Mapear parámetros si existen
        if parametros:
            payload["template"]["components"] = [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": str(p)} for p in parametros]
                }
            ]

        # Si falta token o ID de teléfono, entramos en Modo Simulación
        if not token or not phone_id:
            return self._simular_envio(telefono, plantilla_nombre, parametros)

        url = f"https://graph.facebook.com/v20.0/{phone_id}/messages"
        
        try:
            body_bytes = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            res = requests.post(url, data=body_bytes, headers=headers, timeout=10)
            data = json.loads(res.content.decode('utf-8'))
            if res.status_code in [200, 201]:
                return {
                    "exito": True,
                    "message_id": data.get("messages", [{}])[0].get("id", "wamid.simulado"),
                    "respuesta_meta": data
                }
            else:
                return {
                    "exito": False,
                    "error": data.get("error", {}).get("message", "Error desconocido de Meta API"),
                    "respuesta_meta": data
                }
        except Exception as e:
            return {
                "exito": False,
                "error": f"Excepción de red al conectar con Meta: {str(e)}"
            }

    def enviar_mensaje_texto(self, telefono: str, texto: str) -> dict:
        """
        Envía un mensaje de texto libre por WhatsApp. 
        Nota: Esto requiere que la ventana de 24 horas del cliente esté abierta (conversación activa).
        """
        telefono_limpio = telefono.replace("+", "").strip()
        token = app_config.meta_wa_token
        phone_id = app_config.meta_wa_phone_id

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": telefono_limpio,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": texto
            }
        }

        if not token or not phone_id:
            return self._simular_envio_texto(telefono, texto)

        url = f"https://graph.facebook.com/v20.0/{phone_id}/messages"

        try:
            body_bytes = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            res = requests.post(url, data=body_bytes, headers=headers, timeout=10)
            data = json.loads(res.content.decode('utf-8'))
            if res.status_code in [200, 201]:
                return {
                    "exito": True,
                    "message_id": data.get("messages", [{}])[0].get("id", "wamid.simulado"),
                    "respuesta_meta": data
                }
            else:
                return {
                    "exito": False,
                    "error": data.get("error", {}).get("message", "Error de Meta al enviar texto"),
                    "respuesta_meta": data
                }
        except Exception as e:
            return {
                "exito": False,
                "error": f"Excepción de red: {str(e)}"
            }

    _dynamic_templates = []

    def obtener_plantillas(self) -> list:
        """
        Recupera las plantillas de mensaje aprobadas para la cuenta de WhatsApp Business.
        Si no hay cuenta configurada, devuelve plantillas simuladas para pruebas.
        """
        business_id = app_config.meta_wa_business_id
        token = app_config.meta_wa_token
        
        # Plantillas de simulación por defecto
        plantillas_simuladas = [
            {
                "name": "plantilla_curso_latinpyme",
                "language": "es",
                "category": "UTILITY",
                "components": [
                    {
                        "type": "BODY",
                        "text": "Hola {{1}}, vimos tu desempeño y perfil. Por eso creemos que el taller de: {{2}} es ideal para ti."
                    }
                ],
                "status": "APPROVED"
            },
            {
                "name": "bienvenida_latinpyme",
                "language": "es",
                "category": "UTILITY",
                "components": [
                    {
                        "type": "BODY",
                        "text": "Hola {{1}}, bienvenido a la Escuela de Negocios LatinPyme. ¡Estamos felices de tenerte!"
                    }
                ],
                "status": "APPROVED"
            },
            {
                "name": "recordatorio_evento",
                "language": "es",
                "category": "UTILITY",
                "components": [
                    {
                        "type": "BODY",
                        "text": "Estimado(a) {{1}}, te recordamos que tu evento inicia el {{2}} a las {{3}}. ¡Te esperamos!"
                    }
                ],
                "status": "APPROVED"
            }
        ]

        # Incluir plantillas creadas localmente / en sesión
        todas_simuladas = plantillas_simuladas + self._dynamic_templates

        if not business_id or not token:
            return todas_simuladas

        url = f"https://graph.facebook.com/v20.0/{business_id}/message_templates"
        
        try:
            res = requests.get(url, headers=self._get_api_headers(), timeout=10)
            if res.status_code == 200:
                data = res.json()
                templates = data.get("data", [])
                if not templates:
                    return todas_simuladas
                
                # Combinar plantillas de Meta con las creadas localmente no sincronizadas aún
                nombres_meta = {t["name"] for t in templates}
                for dt in self._dynamic_templates:
                    if dt["name"] not in nombres_meta:
                        templates.append(dt)
                return templates
            else:
                print(f"Error al obtener plantillas de Meta ({res.status_code}): {res.text}")
                return todas_simuladas
        except Exception as e:
            print(f"Excepción obteniendo plantillas de Meta: {e}")
            return todas_simuladas

    def crear_plantilla(self, nombre: str, categoria: str, texto_body: str, idioma: str = "es") -> dict:
        """
        Envía una nueva plantilla de mensaje a Meta para su revisión y aprobación.
        
        Categorías válidas de Meta:
        - UTILITY: Notificaciones transaccionales, actualizaciones de cursos, recordatorios.
        - MARKETING: Ofertas, promociones, lanzamientos.
        - AUTHENTICATION: Códigos de verificación.
        """
        import re
        nombre_limpio = nombre.lower().strip().replace(" ", "_").replace("-", "_")
        nombre_limpio = re.sub(r'[^a-z0-9_]', '', nombre_limpio)
        
        if not nombre_limpio:
            return {"exito": False, "error": "El nombre de la plantilla debe contener caracteres válidos (a-z, 0-9, _)."}

        business_id = app_config.meta_wa_business_id
        token = app_config.meta_wa_token
        
        new_template_obj = {
            "name": nombre_limpio,
            "category": categoria.upper(),
            "language": idioma,
            "components": [
                {
                    "type": "BODY",
                    "text": texto_body
                }
            ],
            "status": "PENDING"
        }

        if not business_id or not token:
            # En modo simulación la agregamos a la lista dinámica
            self._dynamic_templates.append(new_template_obj)
            return {
                "exito": True,
                "simulado": True,
                "template": new_template_obj,
                "mensaje": f"Plantilla '{nombre_limpio}' enviada a revisión de Meta. Estado inicial: 🟡 PENDING (En revisión)."
            }
            
        url = f"https://graph.facebook.com/v20.0/{business_id}/message_templates"
        payload = {
            "name": nombre_limpio,
            "category": categoria.upper(),
            "language": idioma,
            "components": [
                {
                    "type": "BODY",
                    "text": texto_body
                }
            ]
        }

        try:
            body_bytes = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            res = requests.post(url, data=body_bytes, headers=headers, timeout=10)
            data = res.json()
            
            if res.status_code in [200, 201]:
                status = data.get("status", "PENDING")
                new_template_obj["status"] = status
                new_template_obj["id"] = data.get("id")
                self._dynamic_templates.append(new_template_obj)
                return {
                    "exito": True,
                    "id": data.get("id"),
                    "status": status,
                    "template": new_template_obj,
                    "mensaje": "Plantilla enviada exitosamente a Meta Graph API. Estado inicial: 🟡 PENDING (En revisión por Meta)."
                }
            else:
                error_msg = data.get("error", {}).get("message", "Error de Meta al crear la plantilla")
                return {
                    "exito": False,
                    "error": error_msg,
                    "respuesta_meta": data
                }
        except Exception as e:
            return {
                "exito": False,
                "error": f"Excepción de red conectando con Meta: {str(e)}"
            }

    def _simular_envio(self, telefono: str, plantilla_nombre: str, parametros: list) -> dict:
        """Simula una llamada exitosa para pruebas de flujo offline."""
        time.sleep(0.15)  # Breve retardo realista
        return {
            "exito": True,
            "simulado": True,
            "message_id": f"wamid.HBgM{int(time.time()*1000)}simulado",
            "detalles": f"Enviado simulado de la plantilla '{plantilla_nombre}' a {telefono} con parámetros: {parametros}"
        }

    def _simular_envio_texto(self, telefono: str, texto: str) -> dict:
        """Simula envío de texto plano."""
        time.sleep(0.1)
        return {
            "exito": True,
            "simulado": True,
            "message_id": f"wamid.HBgM{int(time.time()*1000)}simulado_text",
            "detalles": f"Mensaje simulado enviado a {telefono}: '{texto}'"
        }

    def download_media(self, media_id: str, save_dir: str = 'static/uploads/media') -> dict:
        """
        Descarga un archivo multimedia (imagen, audio, documento, video) desde los servidores de Meta Cloud API
        utilizando su media_id y lo guarda localmente en el servidor.
        """
        token = app_config.meta_wa_token
        if not token or not media_id:
            return {"exito": False, "error": "Falta token de Meta o media_id"}

        try:
            import os
            import uuid
            os.makedirs(save_dir, exist_ok=True)

            headers = {"Authorization": f"Bearer {token}"}
            # 1. Obtener la URL de descarga temporal desde Meta Graph API
            meta_url = f"https://graph.facebook.com/v20.0/{media_id}"
            res = requests.get(meta_url, headers=headers, timeout=10)
            if res.status_code != 200:
                return {"exito": False, "error": f"Error obteniendo URL de media de Meta (status {res.status_code})"}

            data = res.json()
            download_url = data.get("url")
            mime_type = data.get("mime_type", "")

            if not download_url:
                return {"exito": False, "error": "Meta no devolvió la URL de descarga"}

            # 2. Descargar los bytes binarios del archivo
            file_res = requests.get(download_url, headers=headers, timeout=20)
            if file_res.status_code != 200:
                return {"exito": False, "error": f"Error descargando binario de media (status {file_res.status_code})"}

            ext_map = {
                'audio/ogg': '.ogg',
                'audio/opus': '.ogg',
                'audio/mpeg': '.mp3',
                'audio/mp4': '.m4a',
                'image/jpeg': '.jpg',
                'image/png': '.png',
                'image/webp': '.webp',
                'application/pdf': '.pdf',
                'video/mp4': '.mp4'
            }
            ext = ext_map.get(mime_type.split(';')[0].strip(), '.bin')
            filename = f"wa_{int(time.time())}_{uuid.uuid4().hex[:6]}{ext}"
            file_path = os.path.join(save_dir, filename)

            with open(file_path, "wb") as f:
                f.write(file_res.content)

            media_url = f"/static/uploads/media/{filename}"
            print(f"[META-MEDIA] Descargado exitosamente {media_id} -> {file_path}")

            return {
                "exito": True,
                "local_path": file_path,
                "media_url": media_url,
                "mime_type": mime_type,
                "filename": filename
            }
        except Exception as e:
            print(f"[META-MEDIA] Excepción descargando media {media_id}: {e}")
            return {"exito": False, "error": str(e)}

    def enviar_mensaje_media(self, telefono: str, media_type: str, media_url: str, caption: str = None, filename: str = None) -> dict:
        """
        Envía un archivo multimedia (imagen, audio, documento) por WhatsApp Cloud API.
        """
        telefono_limpio = telefono.replace("+", "").strip()
        token = app_config.meta_wa_token
        phone_id = app_config.meta_wa_phone_id

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": telefono_limpio,
            "type": media_type
        }

        if media_type == "image":
            payload["image"] = {"link": media_url}
            if caption:
                payload["image"]["caption"] = caption
        elif media_type == "document":
            payload["document"] = {"link": media_url}
            if caption:
                payload["document"]["caption"] = caption
            if filename:
                payload["document"]["filename"] = filename
        elif media_type in ["audio", "voice"]:
            payload["audio"] = {"link": media_url}

        if not token or not phone_id:
            time.sleep(0.1)
            return {
                "exito": True,
                "simulado": True,
                "message_id": f"wamid.HBgM{int(time.time()*1000)}simulado_media",
                "detalles": f"Envío simulado de {media_type} a {telefono}"
            }

        url = f"https://graph.facebook.com/v20.0/{phone_id}/messages"
        try:
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8"
            }
            res = requests.post(url, json=payload, headers=headers, timeout=15)
            data = res.json()
            if res.status_code in [200, 201]:
                return {
                    "exito": True,
                    "message_id": data.get("messages", [{}])[0].get("id", "wamid.simulado"),
                    "respuesta_meta": data
                }
            else:
                return {
                    "exito": False,
                    "error": data.get("error", {}).get("message", "Error de Meta al enviar multimedia"),
                    "respuesta_meta": data
                }
        except Exception as e:
            return {"exito": False, "error": f"Excepción de red: {str(e)}"}
