import os
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import google.generativeai as genai
from pypdf import PdfReader

app = Flask(__name__, static_folder='.') # Ajuste para servir index.html si es necesario
CORS(app)

# CONFIGURACIÓN API KEY
# En entornos Google, lo ideal es usar Secret Manager o Variables de Entorno.
# Si no la encuentra en el sistema, usa la que pongas aquí por defecto.
API_KEY = os.environ.get("GOOGLE_API_KEY", "TU_API_KEY_AQUI")
genai.configure(api_key=API_KEY)

# --- SISTEMA EXPERTO SENA CIES ---
sena_instruction = """
Eres el Auditor de Contratación del SENA (Regional Huila).
Tu misión es validar rigurosamente si un candidato cumple con los requisitos para ser Instructor.

INSTRUCCIONES DE VALIDACIÓN:
1.  Analiza DETALLADAMENTE los "REQUISITOS DEL PERFIL" proporcionados.
2.  Revisa UNO A UNO los "DOCUMENTOS APORTADOS" (Soportes).
3.  Para cada requisito, busca la evidencia correspondiente en los soportes.
4.  Determina si el candidato "CUMPLE" o "NO CUMPLE" con cada requisito específico.
5.  Justifica tu decisión citando el documento y la página (si es posible) donde se encuentra la evidencia.
6.  Si un requisito no tiene soporte, marca "NO CUMPLE" y explica que falta la evidencia.

FORMATO DE SALIDA (Markdown):
-   Resumen del Perfil: Breve descripción del cargo.
-   Tabla de Cumplimiento:
    | Requisito | Estado (CUMPLE / NO CUMPLE) | Justificación / Evidencia |
    | :--- | :---: | :--- |
    | ... | ... | ... |
-   Conclusión Final: Párrafo indicando si el candidato es APTO o NO APTO para contratación, basado en si cumple TODOS los requisitos críticos.
"""

model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    generation_config={"temperature": 0.2},
    system_instruction=sena_instruction
)

def extraer_texto_pdf(file_storage):
    try:
        reader = PdfReader(file_storage)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except: return "[Error leyendo PDF]"

# RUTA PARA SERVIR EL FRONTEND (Importante para despliegue unificado)
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/validar-contratacion', methods=['POST'])
def validar_contratacion():
    try:
        # Recolección de datos
        nombre = request.form.get('nombre')
        id_aspirante = request.form.get('identificacion')
        requisitos_texto = request.form.get('requisitos')
        requisitos_pdf = request.files.get('requisitos_pdf') # Nuevo: PDF de requisitos
        archivos = request.files.getlist('soportes')

        if not archivos:
            return jsonify({"error": "Debes subir los archivos soporte (PDFs)."}), 400

        # Procesar Requisitos (Texto o PDF)
        texto_requisitos = ""
        if requisitos_pdf:
            texto_requisitos += f"--- REQUISITOS (Desde PDF: {requisitos_pdf.filename}) ---\n"
            texto_requisitos += extraer_texto_pdf(requisitos_pdf) + "\n"
        
        if requisitos_texto:
             texto_requisitos += f"\n--- REQUISITOS (Texto Adicional) ---\n{requisitos_texto}\n"

        if not texto_requisitos.strip():
             return jsonify({"error": "Debes proporcionar los requisitos (Texto o PDF)."}), 400

        # Procesamiento PDF Soportes
        texto_evidencia = ""
        for arch in archivos:
            texto_evidencia += f"\n--- SOPORTE: {arch.filename} ---\n{extraer_texto_pdf(arch)}\n"

        # Prompt
        prompt = f"""
        CANDIDATO: {nombre} (ID: {id_aspirante})
        
        === PERFIL REQUERIDO Y REQUISITOS ===
        {texto_requisitos}
        
        === DOCUMENTOS APORTADOS (EVIDENCIA) ===
        {texto_evidencia}
        """

        response = model.generate_content(prompt)
        return jsonify({"analisis": response.text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Google Cloud inyecta el puerto en la variable de entorno PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)