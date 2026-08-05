import os
import io
from flask import Blueprint, render_template, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
import pandas as pd
from services import ExcelService, OpenAIService

datacenter_bp = Blueprint('datacenter', __name__)

excel_service = ExcelService()
openai_service = OpenAIService()

@datacenter_bp.route('/')
def index():
    """Renderiza la interfaz del Data Center."""
    return render_template('datacenter.html')

@datacenter_bp.route('/analizar', methods=['POST'])
def analizar():
    """
    Recibe el archivo Excel/CSV y los parámetros del curso.
    Detecta automáticamente las columnas y ejecuta la evaluación de perfil por IA.
    """
    archivo = request.files.get('file')
    nombre_curso = request.form.get('nombre_curso', '').strip()
    audiencia_curso = request.form.get('audiencia_curso', '').strip()

    if not archivo:
        return jsonify({'error': 'No se cargó ningún archivo.'}), 400

    if not nombre_curso or not audiencia_curso:
        return jsonify({'error': 'Debe ingresar el nombre del curso y el perfil de la audiencia.'}), 400

    # Crear carpeta de subidas si no existe
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    os.makedirs(upload_folder, exist_ok=True)

    filename = secure_filename(archivo.filename)
    filepath = os.path.join(upload_folder, filename)
    archivo.save(filepath)

    try:
        # Procesar Excel / CSV usando el servicio especializado
        registros = excel_service.procesar_archivo(filepath)
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({'error': f"Error al procesar el archivo: {str(e)}"}), 400

    # Borrar archivo temporal después de cargado en memoria
    if os.path.exists(filepath):
        os.remove(filepath)

    analizados = []
    
    # Evaluar cada registro usando el servicio de OpenAI / simulación
    for reg in registros:
        nombre_completo = reg["nombre"]
        cargo = reg["cargo"]
        profesion = reg["profesion"]
        
        # Consultar servicio de evaluación por IA
        resultado_ia = openai_service.analizar_perfil(
            nombre_curso=nombre_curso,
            audiencia_curso=audiencia_curso,
            nombre_completo=nombre_completo,
            cargo=cargo,
            profesion=profesion
        )

        reg.update({
            "es_candidato": resultado_ia.get("es_candidato", False),
            "razon": resultado_ia.get("razon", "Sin evaluar"),
            "mensaje": resultado_ia.get("mensaje", "")
        })
        analizados.append(reg)

    return jsonify({
        "exito": True,
        "total_registros": len(analizados),
        "data": analizados
    })

@datacenter_bp.route('/exportar', methods=['POST'])
def exportar():
    """
    Recibe la lista de registros evaluados como JSON y genera un Excel para descargar.
    """
    datos = request.get_json()
    if not datos or 'registros' not in datos:
        return jsonify({'error': 'No hay datos para exportar.'}), 400

    registros = datos['registros']
    df = pd.DataFrame(registros)

    # Renombrar columnas para la descarga
    column_mapping = {
        "id_registro": "ID",
        "nombre": "Nombre Completo",
        "correo": "Correo Electrónico",
        "cargo": "Cargo",
        "profesion": "Profesión",
        "empresa": "Empresa",
        "telefono": "Teléfono Móvil",
        "documento": "Documento Identidad",
        "es_candidato": "Candidato Calificado",
        "razon": "Razón del Análisis",
        "mensaje": "Mensaje Personalizado WA"
    }
    
    # Filtrar solo columnas existentes en el mapeo
    df_export = df[[col for col in column_mapping.keys() if col in df.columns]].rename(columns=column_mapping)
    
    # Reemplazar booleanos por textos legibles
    if "Candidato Calificado" in df_export.columns:
        df_export["Candidato Calificado"] = df_export["Candidato Calificado"].map({True: "Aprobado", False: "Descartado"})

    # Crear buffer en memoria para enviar el archivo
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Candidatos_Perfilados')
    output.seek(0)

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="candidatos_perfilados_latinpyme.xlsx"
    )
