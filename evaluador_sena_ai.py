import streamlit as st
import google.generativeai as genai
import PyPDF2
import pandas as pd
import json
import io
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Evaluador Masivo SENA", page_icon="⚖️", layout="wide")

# --- GESTIÓN DE API KEY (SECRETS) ---
# Intenta obtener la clave de los secretos de la nube, si no, la pide manual
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    api_key = st.sidebar.text_input("Ingresa tu Google API Key:", type="password")

# --- FUNCIONES DE SOPORTE ---

def extraer_texto_pdf(archivo):
    try:
        pdf_reader = PyPDF2.PdfReader(archivo)
        texto = ""
        for pagina in pdf_reader.pages:
            txt = pagina.extract_text()
            if txt: texto += txt + "\n"
        return texto
    except Exception as e:
        return f"Error leyendo PDF: {e}"

def consultar_gemini_avanzado(texto_cv, requisitos):
    """
    Analiza el CV buscando cumplimiento de alternativas y fechas históricas.
    """
    if not api_key: return None
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # PROMPT DE INGENIERÍA AVANZADA
    prompt = f"""
    Eres un experto evaluador de Talento Humano del SENA. Tu misión es validar si un candidato cumple con el perfil.
    
    PERFIL REQUERIDO (Analiza si cumple la Opción 1 O la Opción 2 si existen):
    {requisitos}
    
    INSTRUCCIONES CLAVE DE VALIDACIÓN:
    1. **Fechas Históricas:** Reconoce fechas antiguas (ej: 1989, 1995). Son totalmente válidas.
    2. **Punto de Corte:** Busca en el texto la fecha de GRADO o TÍTULO PROFESIONAL. La experiencia laboral solo cuenta DESPUÉS de esa fecha.
    3. **Alternativas:** Si el perfil permite "Alternativa A" (ej: Profesional + Especialización) o "Alternativa B" (ej: Profesional + 3 años exp), verifica si cumple CUALQUIERA de las dos.
    4. **Sumatoria:** Suma los tiempos de experiencia válida (post-grado) de todas las certificaciones encontradas.
    
    TEXTO DEL CANDIDATO:
    {texto_cv}
    
    FORMATO DE RESPUESTA (Solo JSON válido):
    {{
        "nombre_candidato": "Nombre detectado",
        "documento_id": "Cédula o ID detectado",
        "fecha_grado_detectada": "DD/MM/AAAA (o 'No encontrada')",
        "cumple_perfil": "SI" o "NO",
        "alternativa_aplicada": "Indica si aplicó Alternativa 1, 2, o Ninguna",
        "justificacion_breve": "Explica por qué cumple o falla",
        "meses_experiencia_validos": (Número entero, suma total post-grado),
        "empresas_detectadas": "Lista de empresas separadas por coma"
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except Exception as e:
        return {"nombre_candidato": "Error AI", "justificacion_breve": str(e)}

def generar_excel_descargable(dataframe, archivo_plantilla=None):
    """
    Genera un Excel. Si el usuario subió plantilla, anexa los datos.
    Si no, crea uno nuevo.
    """
    buffer = io.BytesIO()
    
    if archivo_plantilla is not None:
        # Lógica para cargar plantilla y anexar (Append)
        # Por simplicidad y robustez, cargamos la plantilla en pandas y concatenamos
        try:
            df_plantilla = pd.read_excel(archivo_plantilla)
            # Normalizamos nombres de columnas para evitar duplicados si son iguales
            df_final = pd.concat([df_plantilla, dataframe], ignore_index=True)
        except:
            # Si falla la lectura de la plantilla, usamos solo la data nueva
            df_final = dataframe
    else:
        df_final = dataframe

    # Guardar en buffer con motor XlsxWriter
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_final.to_excel(writer, index=False, sheet_name='Evaluacion_SENA')
        
        # Ajuste automático de ancho de columnas
        worksheet = writer.sheets['Evaluacion_SENA']
        for i, col in enumerate(df_final.columns):
            width = max(df_final[col].astype(str).map(len).max(), len(col)) + 2
            worksheet.set_column(i, i, width)
            
    buffer.seek(0)
    return buffer

# --- INTERFAZ GRÁFICA ---

st.title("Validador Masivo de Instructores SENA 🚀")
st.markdown("---")

# ZONA SUPERIOR: CONFIGURACIÓN Y PLANTILLA
col_config1, col_config2 = st.columns([1, 1])

with col_config1:
    st.subheader("1. Definición del Perfil")
    requisitos_input = st.text_area(
        "Copie aquí los Requisitos (Incluya Alternativa 1 y 2 si aplican)", 
        height=200,
        placeholder="Ejemplo:\nAlternativa 1: Título Profesional en Sistemas + Especialización.\nAlternativa 2: Título Profesional + 24 meses de experiencia..."
    )

with col_config2:
    st.subheader("2. Formato de Salida (Opcional)")
    st.info("Si tienes un formato Excel propio, cárgalo aquí y el sistema agregará los resultados al final.")
    plantilla_excel = st.file_uploader("Cargar Plantilla Excel (.xlsx)", type=["xlsx"])

st.markdown("---")

# ZONA CENTRAL: CARGA MASIVA
st.subheader("3. Carga de Hojas de Vida (Lote)")
uploaded_files = st.file_uploader(
    "Seleccione TODOS los archivos PDF a evaluar (Máx 200MB)", 
    type="pdf", 
    accept_multiple_files=True
)

# BOTÓN DE ACCIÓN
if st.button("🔍 EJECUTAR EVALUACIÓN MASIVA"):
    if not api_key:
        st.error("❌ Falta la API Key de Google.")
    elif not requisitos_input:
        st.warning("⚠️ Debes definir los requisitos del perfil.")
    elif not uploaded_files:
        st.warning("⚠️ No has cargado ningún PDF.")
    else:
        # BARRA DE PROGRESO
        progreso_bar = st.progress(0)
        status_text = st.empty()
        
        resultados_lista = []
        total_archivos = len(uploaded_files)
        
        # BUCLE DE PROCESAMIENTO
        for index, archivo_pdf in enumerate(uploaded_files):
            status_text.text(f"Analizando {index + 1}/{total_archivos}: {archivo_pdf.name}...")
            
            # 1. Extraer Texto
            texto = extraer_texto_pdf(archivo_pdf)
            
            # 2. Consultar a GEMINI
            datos_ai = consultar_gemini_avanzado(texto, requisitos_input)
            
            if datos_ai:
                # Agregamos el nombre del archivo para referencia
                datos_ai["nombre_archivo"] = archivo_pdf.name
                resultados_lista.append(datos_ai)
            
            # Actualizar barra
            progreso_bar.progress((index + 1) / total_archivos)
            
        status_text.text("✅ Análisis completado. Generando informe...")
        
        # CREACIÓN DEL DATAFRAME (TABLA)
        if resultados_lista:
            df_resultados = pd.DataFrame(resultados_lista)
            
            # Reordenamos columnas para que se vea profesional
            cols_orden = [
                "nombre_candidato", "documento_id", "cumple_perfil", 
                "meses_experiencia_validos", "fecha_grado_detectada", 
                "alternativa_aplicada", "justificacion_breve", "nombre_archivo"
            ]
            # Aseguramos que existan las columnas (por si la IA falló en alguna)
            df_resultados = df_resultados.reindex(columns=cols_orden)
            
            # MOSTRAR TABLA EN PANTALLA
            st.success("Proceso finalizado con éxito.")
            st.dataframe(df_resultados)
            
            # GENERAR EXCEL
            excel_data = generar_excel_descargable(df_resultados, plantilla_excel)
            
            st.download_button(
                label="📥 DESCARGAR INFORME DE EVALUACIÓN (EXCEL)",
                data=excel_data,
                file_name=f"Informe_Evaluacion_SENA_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("No se pudieron extraer datos de los archivos.")
