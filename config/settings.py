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
    "AI_DEFAULT_PROMPT": "Eres un asistente virtual amable y profesional de la Escuela de Negocios LatinPyme. Responde de manera concisa y cordial las preguntas del estudiante. Si no conoces la respuesta, indícale que un asesor le contactará pronto.",
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
            
    return config

def save_config(new_data: dict) -> bool:
    """
    Guarda los datos de configuración en el archivo config.json.
    """
    current_config = get_config()
    # Solo actualizar las llaves que corresponden a nuestra configuración estándar
    for key in DEFAULT_CONFIG.keys():
        if key in new_data:
            current_config[key] = new_data[key]
            
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
        return get_config().get("OPENAI_API_KEY", "")

    @property
    def meta_wa_token(self) -> str:
        return get_config().get("META_WA_TOKEN", "")

    @property
    def meta_wa_phone_id(self) -> str:
        return get_config().get("META_WA_PHONE_NUMBER_ID", "")

    @property
    def meta_wa_business_id(self) -> str:
        return get_config().get("META_WA_BUSINESS_ACCOUNT_ID", "")

    @property
    def meta_wa_webhook_verify_token(self) -> str:
        return get_config().get("META_WA_WEBHOOK_VERIFY_TOKEN", "latinpyme_secret_token")

    @property
    def meta_wa_template_name(self) -> str:
        return get_config().get("META_WA_TEMPLATE_NAME", "plantilla_curso_latinpyme")

    @property
    def aulas_api_url(self) -> str:
        return get_config().get("AULAS_API_URL", "https://capacitacionaportesenlinea.com/api/v1/getUserPhone")

    @property
    def aulas_api_token(self) -> str:
        return get_config().get("AULAS_API_TOKEN", "topchat-token-access-2024")

    @property
    def ai_assistant_enabled(self) -> bool:
        return get_config().get("AI_ASSISTANT_ENABLED", "true").lower() == "true"

    @property
    def ai_auto_reply(self) -> bool:
        return get_config().get("AI_AUTO_REPLY", "true").lower() == "true"

    @property
    def ai_default_prompt(self) -> str:
        return get_config().get("AI_DEFAULT_PROMPT", "Eres un asistente virtual de la Escuela de Negocios LatinPyme.")

    @property
    def openai_model(self) -> str:
        return get_config().get("OPENAI_MODEL", "gpt-4o-mini")

    @property
    def is_simulation_mode(self) -> bool:
        config = get_config()
        # Si falta la API Key de OpenAI o el token de Meta, activamos simulación parcial o total
        return not config.get("OPENAI_API_KEY") or not config.get("META_WA_TOKEN")

# Instancia singleton para uso general
app_config = AppConfig()
