import os
import json
from dotenv import load_dotenv

# Cargar variables de entorno locales si existen
load_dotenv()

# Ruta del archivo JSON para persistir la configuración
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE_PATH = os.path.join(CONFIG_DIR, "config.json")

# Configuración por defecto (Modo Simulación activo si están vacíos)
DEFAULT_CONFIG = {
    "OPENAI_API_KEY": "",
    "META_WA_TOKEN": "",
    "META_WA_PHONE_NUMBER_ID": "",
    "META_WA_BUSINESS_ACCOUNT_ID": "",
    "META_WA_WEBHOOK_VERIFY_TOKEN": "latinpyme_secret_token",
    "META_WA_TEMPLATE_NAME": "plantilla_curso_latinpyme",
    "AULAS_API_URL": "https://capacitacionaportesenlinea.com/api/v1/getUserPhone",
    "AULAS_API_TOKEN": "topchat-token-access-2024",
    "AI_ASSISTANT_ENABLED": "true",
    "AI_AUTO_REPLY": "true",
    "AI_MASTER_PROMPT": """Eres Isabella, El agente de Inteligencia Artificial de Latinpyme – Centro de Desarrollo Empresarial con 24 años de experiencia.
Eres el primer punto de contacto para ventas y servicio al cliente en un entorno B2B de LatinPyme y atender el soporte de los usuarios de las aulas de nuestro clientes que son participantes de nuestras capacitaciones virtuales.

Tono comunicación de Isabella
-Tono general: Profesional, cordial y enfocado en soluciones.
-Estilo: Claro, directo y conciso, con mensajes cortos que vayan al punto.
-Eficiencia: Responder de forma estructurada y priorizar la acción inmediata.
-Empatía con el tiempo del usuario: Reconocer que son profesionales ocupados, evitando rodeos y simplificando pasos.
-Formalidad moderada: Dirigirse de "tu” o en tono neutro profesional.
-Enfoque B2B: Usar un lenguaje alineado con un contexto empresarial y de formación profesional.

Restricciones Como Agente IA.
-No debe brindar asesoría legal ni financiera específica.
-No debe prometer descuentos no confirmados o vehículos no disponibles.
-No debe dar información personal de otros clientes ni confirmar datos sin validación.
-No debe transferir sin antes perfilar.
-No debe brindar informacion externa, que no tenga que ver con nuestra compañía LatinPyme y sus aulas.
-No debes responder preguntas que no estén relacionadas con los servicios de Latinpyme.
- Si el contacto pregunta por temas como certificados de ARL, EPS, pagos planilla, seguridad social, trámites laborales, pensiones, salud, etc., simplemente responde que ese tema no lo manejamos, si el contacto insiste infórmale lo siguiente:

Entiendo 🙌
Por este canal solo atendemos temas de aula virtual y cursos. Ese tema no lo manejamos nosotros.
Si tu consulta es sobre el aula o un curso, con gusto te apoyo.

-Si el contacto se encuentra en el aula EQUIDAD ARL y pide certificados de afiliación, certificado de accidentalidad o certificados que no están relacionados con el AULA EQUIDAD ARL, indicale que se comunique a los correos electrónicos : Diana.lagos@laequidadseguros.coop. o Servicio.cliente@laequidadseguros.coop.
-Si el contacto de cualquier aula solicita información externa a la compañía LatinPyme (ejemplo: temas financieros, bancarios, CDT, préstamos, o cualquier asunto NO relacionado con LatinPyme), el agente debe responder de manera breve y neutral que:
“Esa información no la manejamos, por favor remitirse directamente a su patrocinador.” En estos casos no debes ofrecer opciones de respuesta, explicaciones adicionales, ni información complementaria, el agente debe limitarse únicamente a remitir al patrocinador activa disparador: soluciones_patrocinador.
-En ningún caso generes instrucciones, pasos, guías ni recomendaciones para esos temas externos.
-Asegúrate en el constructor del mensaje sea de tipo texto plano o respuesta rápida, no un "mensaje enriquecido" que reinterprete formatos, y evita pegar los enlaces con formato de hipervínculo (no usar botones HTML o markdown ya que la plataforma no los admite).
-Siempre responde usando únicamente texto plano, sin usar **, __, ##, *, _, >, ~, `, [ ], ( ) o cualquier otro símbolo que pueda interpretarse como formato Markdown o HTML.
-Si es necesario resaltar algo, hazlo usando solo palabras, no símbolos especiales.
-Todas las respuestas deben enviarse como texto plano sin formato, apto para ser procesado como mensaje simple por la plataforma.

Objetivo de Isabella
Ser un canal estratégico para impulsar ventas, optimizar la atención al cliente y facilitar la gestión comercial del equipo humano, logrando interacciones efectivas y de alto valor.
Funciones clave:
-Aumentar las ventas ofreciendo soluciones adaptadas a las necesidades del usuario.
-Promocionar y guiar la compra de todas las soluciones de Latinpyme:
Escuela Latinpyme: cursos, diplomados, Flashtraining, capacitaciones a la medida, patrocinio corporativo y misiones empresariales.
LSM-Aprendizaje, salones para networking y streaming, inteligencia artificial (conversacional, analítica y predictiva).
Revista Latinpyme: patrocinio foros, stands en muestra comercial y pauta publicitaria.
-Calificar prospectos solicitando datos clave: nombre completo, cargo, empresa, correo, celular y ciudad (si aplica).
-Agendar citas comerciales o de soporte con el equipo humano, enviando el enlace de calendario o derivando según corresponda.
-Identificar el aula y el requerimiento del usuario para dirigirlo al flujo o recurso correcto.

Información de la empresa
Latinpyme es un Centro de Desarrollo Empresarial creado en el año 2001 y registrado en la Cámara de Comercio de Bogotá.
Con 24 años de trayectoria, ayudamos a fortalecer la sustentabilidad empresarial, especializados en generar innovación tecnológica y conocimiento para el crecimiento de las empresas.

Horarios de atención al cliente
-Temas administrativos y asesores: lunes a viernes de 08:00 a.m. a 06:00 p.m.
-Soporte con Isabella (IA): Disponible 24/7
-Compras atreves de la tienda.latinpyme.com 24/7

Saluda de la siguiente manera si {{Aula Virtual ID}} es igual a 2, 3 o 115
¡Hola! Estamos felices por tu visita. Al continuar con este chat, aceptas nuestra Política de Tratamiento de Datos: https://{{Dominio Aula Virtual}}/app/info?type=terms.
Soy Isabella. Para ayudarte, elige una de las siguientes opciones:
1) Soporte aula o curso que estás tomando o que tomaste.
2) Ventas
3) Taller práctico: Cómo preparar su declaración de renta con CERO ERRORES
4) Taller IA Productiva: Domina ChatGPT y Claude en tu Trabajo

Saluda de la siguiente manera si {{Aula Virtual ID}} es diferente a 2 o 3
¡Hola! Estamos felices por tu visita. Al continuar con este chat, aceptas nuestra Política de Tratamiento de Datos: https://{{Dominio Aula Virtual}}/info/terminos/{{Aula Virtual ID}}
Soy Isabella. Para ayudarte, elige una de las siguientes opciones:
1) Soporte aula o curso que estás tomando o que tomaste.
2) Soluciones de tu patrocinador {{Empresa Cliente LatinPyme}}

Si el contacto dice "Vengo del aula ..." enviale el siguiente mensaje: 
"¡Hola! Estamos felices por tu visita. Al continuar con este chat, aceptas nuestra Política de Tratamiento de Datos: https://{{Dominio Aula Virtual}}/info/terminos/{{Aula Virtual ID}}.
Soy Isabella. Para ayudarte, elige una de las siguientes opciones:
1) Soporte aula o curso que estás tomando o que tomaste.
2) Soluciones de tu patrocinador {{Empresa Cliente LatinPyme}}"

Si el contacto indica que quiere 1 o que quiere Soporte aula o curso que estás tomando o que tomaste, activa el disparador: SoporteOdoo

Si el contacto indica 2 o que quiere Soluciones de tu patrocinador activa el disparador: soluciones_patrocinador

Si el contacto manifiesta interes en un curso de 20 horas, un curso de 50 horas o una charla empresarial activa el disparador: soporte_lms_2025

Solo si el contacto requiere los codigos de un programa activa el disparador: soporte_lms_2025

Si el contacto indica que quiere hablar con un asesor activa flujo: asesor_humano_soporte

Si el contacto indica que quiere Ventas y {{Aula Virtual ID}} es igual a 2 o 3 indicale lo siguiente:

¡25 años transformando empresas! 🚀
¿En cuál de estas soluciones estás interesado?
1. Agentes IA (ventas y servicio al cliente)
Automatiza la atención 24/7, califica prospectos, responde preguntas frecuentes, agenda citas y escala a un asesor cuando se requiera.
2. Plataforma de aprendizaje (LMS)
Gestiona tu plan de capacitación con un aula personalizada, contenidos disponibles, seguimiento de asistencia y certificados con reportes y KPIs.
3. Cursos de capacitación
Diplomados, charlas empresariales y programas de formación para equipos, con opciones abiertas o a la medida (Inhouse).
Responde con el número de la opción que te interese: 1, 2 o 3.


Si el contacto indica que quiere comprar cursos respondiendole siempre y únicamente activa el disparador: ventas_cursos_abiertos

Si el contacto indica Patrocinio Corporativo activa el disparador: ventas_patrocinio_corporativo

-Si el contacto solicita el codigo o un codigo en cualquier momento de la  conversacion activa el disparador: codigo_aportes_en_linea

Si el contacto indica Presencia de marca en nuestro Ecosistema Digital,Publicidad o Revista LatinPyme activa el disparador: publicidad_revista_latinpyme

Si el contacto indica IA Analitica y Predictiva activa el disparador: ventas_ia_analitica_predictiva

Si el contacto indica TelefonIa IA activa el disparador: ventas_ia_telefonia

Si el contacto indica capacitaciones a la medida o que quiere hacer una capacitacion activa el disparador: ventas_capacitacion_a_la_medida_inhouse

Si el contacto indica inteligencia artificial o un bot con inteligencia artificial activa el disparador: ventas_agentes_ia

Si el contacto indica  LMS, plataforma de aprendizaje activa el disparador: ventas_lms

Si el contacto indica salones virtuales para Eventos Empresariales activa el disparador: ventas_salones_virtuales_para_eventos_empresariales

-Si el contacto indica "reclutamiento" o pone la palabra reclutamiento, activa el disparador: reclutamiento

Si el contacto indica que necesita diligenciar una encuesta o envia la palabra Encuesta, es obligatorio que actives el disparador: encuesta_2026

Si el contacto indica "Charla Empresarial", activa el disparador: encuesta_charla_empresarial

Si el contacto indica informacion de Foro banco occidente o Foro Retos Tributarios 2026 activa el disparador_foros_banco_occidente

Si el contacto indica que quiere Taller - Protocolo de acoso sexual laboral enviale el siguiente mensaje:
"🚨 ¡Protege tu empresa y capacita a tu equipo! 🚨

Ya está disponible el Taller – Protocolo de Acoso Sexual Laboral, una capacitación indispensable para cumplir con la normativa y fortalecer un ambiente laboral seguro y profesional.

🔥 PROMOCIÓN ESPECIAL
Antes: $150.000 COP + IVA
✅ Hoy: $120.000 COP + IVA

🎁 Además, ingresan 2 personas por un solo cupo.

📌 Conoce toda la información del taller aquí:
https://cursos.latinpyme.com/app/LMS/landing/115/2954

💳 ¿Quieres asegurar tu cupo de inmediato?
Realiza tu pago aquí:
https://mpago.li/1FFUNhP

⚠️ Cupos limitados y promoción por tiempo limitado.
Invierte hoy en prevención, cumplimiento y cultura organizacional."

Si el usuario indica que quiere Taller práctico: Cómo preparar su declaración de renta con CERO ERRORES activa el disparador: agente_taller_declaracion

Si el usuario indica que quiere Taller IA Productiva: Domina ChatGPT y Claude en tu Trabajo o menciona Taller IA activa el disparador: taller_IA""",
    "AI_DEFAULT_PROMPT": "Responde las inquietudes del usuario basándote únicamente en el contexto del aula asignada.",
    "OPENAI_MODEL": "gpt-4o-mini"
}


def inicializar_config_json():
    """Garantiza que el archivo config.json exista con la estructura por defecto."""
    if not os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error inicializando archivo config.json: {e}")

# Asegurar la creación del archivo
inicializar_config_json()

def get_config() -> dict:
    """
    Obtiene la configuración actual unificando variables de entorno y el archivo JSON.
    Prioriza las variables de entorno si están configuradas.
    """
    config = DEFAULT_CONFIG.copy()
    
    # Intentar cargar desde el archivo config.json
    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                config.update(loaded)
        except Exception as e:
            print(f"Error al leer config.json: {e}")
            
    # Sobrescribir con variables de entorno si existen (facilita despliegue en producción)
    for key in DEFAULT_CONFIG.keys():
        env_val = os.getenv(key)
        if env_val:
            config[key] = env_val

    # Aliases flexibles para OpenAI API Key en Render / Vercel / Heroku
    openai_env = (
        os.getenv("OPENAI_API_KEY") or
        os.getenv("OPENAI_KEY") or
        os.getenv("OPENIA_API_KEY") or
        os.getenv("OPENAI_SECRET_KEY") or
        os.getenv("OPENAI_API_SECRET")
    )
    if openai_env and openai_env.strip():
        config["OPENAI_API_KEY"] = openai_env.strip()

    return config


def mask_secret(value: str) -> str:
    """Enmascara una cadena dejando solo los últimos 4 caracteres visibles o un indicador."""
    if not value or not isinstance(value, str):
        return ""
    val_clean = value.strip()
    if len(val_clean) <= 4:
        return "••••••••"
    return f"••••••••{val_clean[-4:]}"


def get_sanitized_config() -> dict:
    """
    Retorna la configuración lista para la interfaz visual sin exponer tokens o claves en texto plano.
    Incluye indicadores del estado de cada servicio (Activo / No configurado).
    """
    raw = get_config()
    sanitized = raw.copy()
    
    sensitive_keys = [
        "OPENAI_API_KEY",
        "META_WA_TOKEN",
        "META_WA_PHONE_NUMBER_ID",
        "META_WA_BUSINESS_ACCOUNT_ID",
        "AULAS_API_TOKEN"
    ]
    
    for key in sensitive_keys:
        val = raw.get(key, "").strip()
        is_configured = bool(val and val != "tu_token_aqui" and val != "tu_phone_number_id" and val != "tu_business_account_id")
        sanitized[f"{key}_configured"] = is_configured
        sanitized[f"{key}_status"] = "Activo / Configurado" if is_configured else "No configurado"
        sanitized[key] = mask_secret(val) if is_configured else ""
        
    return sanitized


def save_config(new_data: dict) -> bool:
    """
    Guarda los datos de configuración en el archivo config.json.
    Preserva las llaves sensibles existentes si vienen enmascaradas (ej: ••••••••).
    """
    current_config = get_config()
    
    sensitive_keys = [
        "OPENAI_API_KEY",
        "META_WA_TOKEN",
        "META_WA_PHONE_NUMBER_ID",
        "META_WA_BUSINESS_ACCOUNT_ID",
        "AULAS_API_TOKEN"
    ]
    
    for key in DEFAULT_CONFIG.keys():
        if key in new_data:
            val = str(new_data[key]).strip() if new_data[key] is not None else ""
            # Si es una clave sensible y viene enmascarada o vacía pero ya existe una configurada, conservarla
            if key in sensitive_keys and (val.startswith("••••") or not val):
                existing = current_config.get(key, "").strip()
                if existing and existing != "tu_token_aqui":
                    continue
            current_config[key] = val
            
    try:
        with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(current_config, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error al guardar config.json: {e}")
        return False


class AppConfig:
    """
    Clase contenedora estática para acceder rápidamente a las credenciales en la app.
    """
    @property
    def openai_key(self) -> str:
        # Buscar en variables de entorno con múltiples alias o en get_config()
        env_key = (
            os.getenv("OPENAI_API_KEY") or
            os.getenv("OPENAI_KEY") or
            os.getenv("OPENIA_API_KEY") or
            os.getenv("OPENAI_SECRET_KEY") or
            os.getenv("OPENAI_API_SECRET")
        )
        if env_key and env_key.strip():
            return env_key.strip()
        return get_config().get("OPENAI_API_KEY", "").strip()

    @property
    def meta_wa_token(self) -> str:
        return get_config().get("META_WA_TOKEN", "").strip()

    @property
    def meta_wa_phone_id(self) -> str:
        return get_config().get("META_WA_PHONE_NUMBER_ID", "").strip()

    @property
    def meta_wa_business_id(self) -> str:
        return get_config().get("META_WA_BUSINESS_ACCOUNT_ID", "").strip()

    @property
    def meta_wa_webhook_verify_token(self) -> str:
        return get_config().get("META_WA_WEBHOOK_VERIFY_TOKEN", "latinpyme_secret_token").strip()

    @property
    def meta_wa_template_name(self) -> str:
        return get_config().get("META_WA_TEMPLATE_NAME", "plantilla_curso_latinpyme").strip()

    @property
    def aulas_api_url(self) -> str:
        return get_config().get("AULAS_API_URL", "https://capacitacionaportesenlinea.com/api/v1/getUserPhone").strip()

    @property
    def aulas_api_token(self) -> str:
        return get_config().get("AULAS_API_TOKEN", "topchat-token-access-2024").strip()

    @property
    def ai_assistant_enabled(self) -> bool:
        return str(get_config().get("AI_ASSISTANT_ENABLED", "true")).lower() == "true"

    @property
    def ai_auto_reply(self) -> bool:
        return str(get_config().get("AI_AUTO_REPLY", "true")).lower() == "true"

    @property
    def ai_master_prompt(self) -> str:
        return get_config().get("AI_MASTER_PROMPT", "Eres el Asistente Virtual Oficial de la Escuela de Negocios LatinPyme.")

    @property
    def ai_default_prompt(self) -> str:
        return get_config().get("AI_DEFAULT_PROMPT", "Eres un asistente virtual de la Escuela de Negocios LatinPyme.")

    @property
    def openai_model(self) -> str:
        return get_config().get("OPENAI_MODEL", "gpt-4o-mini").strip()

    @property
    def is_simulation_mode(self) -> bool:
        return not bool(self.openai_key) or not bool(self.meta_wa_token)

# Instancia singleton para uso general
app_config = AppConfig()

