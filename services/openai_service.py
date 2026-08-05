import json
import re
import unicodedata
from openai import OpenAI
from config.settings import app_config

class OpenAIService:
    """
    Servicio de integración con la API de OpenAI para analizar los perfiles
    de los candidatos en base al público objetivo de un curso.
    """

    def _get_client(self):
        """Inicializa el cliente de OpenAI de manera dinámica usando la clave actual."""
        api_key = app_config.openai_key
        if not api_key:
            return None
        try:
            return OpenAI(api_key=api_key)
        except Exception as e:
            print(f"Error al inicializar el cliente OpenAI: {e}")
            return None

    def analizar_perfil(self, nombre_curso: str, audiencia_curso: str, nombre_completo: str, cargo: str, profesion: str) -> dict:
        """
        Evalúa mediante GPT-4o-mini si un perfil califica como candidato ideal.
        Retorna un diccionario con las llaves:
        - es_candidato: bool
        - razon: str
        - mensaje: str (personalizado para WhatsApp)
        """
        client = self._get_client()
        
        # Si no hay cliente u OpenAI API Key, se activa el fallback local de simulación
        if not client:
            return self._evaluar_perfil_local_simulado(nombre_curso, audiencia_curso, nombre_completo, cargo, profesion)

        prompt = f"""
        Evalúa si la siguiente persona es un candidato ideal para el curso: '{nombre_curso}'.
        Público objetivo del curso: '{audiencia_curso}'.
        
        Datos del Candidato:
        - Nombre: {nombre_completo}
        - Cargo actual: {cargo}
        - Profesión: {profesion}

        Debes responder EXCLUSIVAMENTE en formato JSON estricto con las siguientes claves:
        {{
            "es_candidato": true/false (booleano, según si el cargo/profesión se alinea con la audiencia o curso),
            "razon": "Breve explicación en español del análisis (máximo 150 caracteres)",
            "mensaje": "Mensaje personalizado y persuasivo de WhatsApp de máximo 200 caracteres, dirigido a la persona saludándola por su nombre y explicándole por qué su cargo es ideal para este taller."
        }}
        """

        try:
            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un asistente de admisiones experto en capacitación corporativa y redacción persuasiva."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                timeout=10
            )
            data_ia = json.loads(res.choices[0].message.content)
            
            # Sanitizar y asegurar tipos correctos
            return {
                "es_candidato": bool(data_ia.get("es_candidato", False)),
                "razon": str(data_ia.get("razon", "Evaluado con éxito.")),
                "mensaje": str(data_ia.get("mensaje", ""))
            }
        except Exception as e:
            print(f"Error en consulta a OpenAI: {e}. Activando modo local de respaldo.")
            return self._evaluar_perfil_local_simulado(nombre_curso, audiencia_curso, nombre_completo, cargo, profesion)

    def _evaluar_perfil_local_simulado(self, nombre_curso: str, audiencia_curso: str, nombre_completo: str, cargo: str, profesion: str) -> dict:
        """
        Algoritmo de respaldo insensible a acentos que simula la evaluación
        comparando palabras clave del cargo/profesión con la audiencia objetivo.
        """
        def normalizar(t: str) -> str:
            if not isinstance(t, str):
                return ""
            norm = unicodedata.normalize('NFD', t)
            return ''.join(c for c in norm if unicodedata.category(c) != 'Mn').lower().strip()

        cargo_n = normalizar(cargo)
        profesion_n = normalizar(profesion)
        audiencia_n = normalizar(audiencia_curso)
        
        texto_comparar = f"{cargo_n} {profesion_n}"
        palabras_clave = [p for p in re.split(r'[,;\s]+', audiencia_n) if len(p) >= 3]
        
        # Si no hay palabras clave en la audiencia, buscar palabras clave en el nombre del curso
        if not palabras_clave:
            curso_n = normalizar(nombre_curso)
            palabras_clave = [p for p in re.split(r'[,;\s]+', curso_n) if len(p) >= 4]

        coincide = any(kw in texto_comparar for kw in palabras_clave)

        primer_nombre = nombre_completo.split()[0] if nombre_completo else "candidato"

        if coincide:
            return {
                "es_candidato": True,
                "razon": f"(Offline) El cargo '{cargo}' o profesión '{profesion}' coincide con los criterios de interés.",
                "mensaje": f"Hola {primer_nombre}, por tu rol como {cargo} creemos que el curso de {nombre_curso} potenciará tus habilidades."
            }
        else:
            return {
                "es_candidato": False,
                "razon": f"(Offline) El rol '{cargo}' no presenta coincidencias directas con la audiencia objetivo.",
                "mensaje": ""
            }
