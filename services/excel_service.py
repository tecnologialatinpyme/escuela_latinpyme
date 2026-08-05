import os
import re
import pandas as pd
import unicodedata

class ExcelService:
    """
    Servicio de importación y procesamiento de archivos Excel/CSV.
    Detecta automáticamente columnas con nombres variables y normaliza los registros.
    """

    # Mapeo de términos para detección inteligente de columnas
    MAPEO_DICCIONARIO = {
        "nombre": ["nombre", "nombres", "name", "names", "primer nombre", "given name"],
        "apellidos": ["apellido", "apellidos", "last name", "lastname", "surname", "primer apellido"],
        "cargo": ["cargo", "puesto", "rol", "ocupacion", "job title", "title", "position"],
        "profesion": ["profesion", "profesión", "carrera", "area", "career", "profession"],
        "empresa": ["empresa", "compania", "compañía", "razon social", "company", "organization", "workplace"],
        "correo": ["correo", "email", "e-mail", "contacto", "correo electronico", "mail"],
        "celular": ["celular", "telefono", "teléfono", "movil", "móvil", "phone", "whatsapp", "cel", "tel", "mobile", "celular_contacto"],
        "documento": ["documento", "identificacion", "cedula", "nit", "cc", "id", "dni", "doc", "identification", "nro_documento"]
    }

    def _normalizar_header(self, header: str) -> str:
        """Limpia caracteres especiales, tildes y espacios del encabezado."""
        if not isinstance(header, str):
            return ""
        norm = unicodedata.normalize('NFD', header)
        sin_tildes = ''.join(c for c in norm if unicodedata.category(c) != 'Mn')
        return sin_tildes.lower().strip()

    def detectar_columnas(self, df_columns: list) -> dict:
        """
        Analiza las columnas del DataFrame de Excel y las asocia con los campos conocidos.
        Retorna un diccionario { campo_conocido: nombre_columna_excel }.
        """
        mapeo_detectado = {}
        columnas_disponibles = list(df_columns)

        for campo, palabras_clave in self.MAPEO_DICCIONARIO.items():
            for col in columnas_disponibles:
                col_norm = self._normalizar_header(col)
                # Coincidencia exacta o si alguna palabra clave está contenida de forma relevante
                if col_norm in palabras_clave or any(col_norm == kw for kw in palabras_clave):
                    mapeo_detectado[campo] = col
                    columnas_disponibles.remove(col)
                    break
            else:
                # Intento de coincidencia parcial si no hubo exacta
                for col in columnas_disponibles:
                    col_norm = self._normalizar_header(col)
                    if any(kw in col_norm for kw in palabras_clave if len(kw) > 3):
                        mapeo_detectado[campo] = col
                        columnas_disponibles.remove(col)
                        break

        return mapeo_detectado

    def formatear_telefono(self, celular_raw) -> str:
        """
        Limpia y normaliza el teléfono al formato E.164 (ej: +573144187269).
        Si no tiene código de país pero parece número de Colombia (inicia con 3 y tiene 10 dígitos),
        agrega automáticamente +57.
        """
        if pd.isna(celular_raw) or not celular_raw:
            return ""
            
        # Eliminar todo excepto dígitos y el signo + inicial
        limpio = re.sub(r'[^\d+]', '', str(celular_raw))
        
        # Eliminar el signo "+" intermedio si hay más de uno
        if limpio.startswith('+'):
            limpio = '+' + limpio.replace('+', '')
        
        # Si el número solo tiene dígitos y no inicia con "+", agregar prefijo
        # Caso típico de Colombia: 10 dígitos que inician con 3 (ej. 3144187269)
        if re.match(r'^3\d{9}$', limpio):
            limpio = '+57' + limpio
        elif limpio and not limpio.startswith('+'):
            limpio = '+' + limpio
            
        return limpio

    def procesar_archivo(self, filepath: str) -> list:
        """
        Lee el archivo Excel o CSV, detecta las columnas clave,
        extrae los datos normalizados y retorna una lista de diccionarios.
        """
        _, ext = os.path.splitext(filepath)
        ext = ext.lower()

        try:
            if ext == '.csv':
                # Intentar primero UTF-8, luego ISO-8859-1
                try:
                    df = pd.read_csv(filepath, encoding='utf-8')
                except UnicodeDecodeError:
                    df = pd.read_csv(filepath, encoding='iso-8859-1')
            elif ext in ['.xlsx', '.xls']:
                df = pd.read_excel(filepath)
            else:
                raise ValueError("Formato de archivo no soportado. Debe ser .xlsx, .xls o .csv")
        except Exception as e:
            raise Exception(f"Error al leer el archivo de datos: {str(e)}")

        # Detectar columnas automáticamente
        mapeo = self.detectar_columnas(df.columns)
        
        registros = []
        for idx, fila in df.iterrows():
            # Obtener datos usando el mapeo detectado (con fallback a campos genéricos)
            nombre = str(fila.get(mapeo.get("nombre"), "")).strip() if mapeo.get("nombre") else ""
            apellidos = str(fila.get(mapeo.get("apellidos"), "")).strip() if mapeo.get("apellidos") else ""
            
            # Formar nombre completo
            nombre_completo = f"{nombre} {apellidos}".strip()
            # Si no hay nombre pero hay apellidos (o viceversa) o simplemente está vacío
            if not nombre_completo:
                nombre_completo = "Sin Nombre"

            registro = {
                "id_registro": idx + 1,
                "nombre": nombre_completo,
                "correo": str(fila.get(mapeo.get("correo"), "")).strip() if mapeo.get("correo") else "Sin Correo",
                "cargo": str(fila.get(mapeo.get("cargo"), "")).strip() if mapeo.get("cargo") else "Sin Cargo",
                "profesion": str(fila.get(mapeo.get("profesion"), "")).strip() if mapeo.get("profesion") else "Sin Profesión",
                "empresa": str(fila.get(mapeo.get("empresa"), "")).strip() if mapeo.get("empresa") else "Sin Empresa",
                "telefono": self.formatear_telefono(fila.get(mapeo.get("celular"))),
                "documento": str(fila.get(mapeo.get("documento"), "")).strip() if mapeo.get("documento") else "Sin Documento"
            }
            registros.append(registro)

        return registros
