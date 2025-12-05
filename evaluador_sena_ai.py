import streamlit as st
import google.generativeai as genai
import PyPDF2
import pandas as pd
import json
import io
from datetime import datetime
import openpyxl
from openpyxl.styles import Alignment, Border, Side

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestor de Idoneidad SENA 2026", page_icon="🇨🇴", layout="wide")

# --- GESTIÓN DE SEGURIDAD (API KEY) ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except:
    with st.sidebar:
        st.warning("Configuración Local detectada")
        api_key = st.text_input("Tu Google API Key:", type="password")

# --- FUNCIONES CENTRALES ---

def extraer_texto_pdf(archivo):
    """Extrae el texto crudo del PDF para que la IA lo lea."""
    try:
        pdf_reader = PyPDF2.PdfReader(archivo)
        texto = ""
        for pagina in pdf_reader.pages:
            txt = pagina.extract_text()
            if txt: texto += txt + "\n"
        return texto
    except Exception as e:
        return "Error lectura PDF"

def consultar_cerebro_ia(texto_cv, requisitos):
    """
    El núcleo inteligente. Evalúa alternativas, fechas antiguas y genera veredicto.
    """
    if not api_key: return None
    
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    Actúa como Coordinador de Talento Humano del SENA. Tu tarea es diligenciar el formato de idoneidad.
    
    REGLAS DE NEGOCIO CRÍTICAS:
    1. **Fecha de Grado:** Es el punto de partida. Solo cuenta la experiencia POSTERIOR a esta fecha.
    2. **Fechas Históricas:** Acepta fechas antiguas (ej: 1989, 1995, 2005). El sistema anterior fallaba con esto, tú debes sumarlas correctamente.
    3. **Alternativas:** El perfil puede tener "Alternativa 1" (ej: Título + Esp) o "Alternativa 2" (ej: Título + Exp). Si cumple CUALQUIERA, el veredicto es "CUMPLE".
    4. **Sumatoria:** Suma los meses de experiencia válida de todas las certificaciones detectadas post-grado.
    
    PERFIL REQUERIDO:
    {requisitos}
    
    HOJA DE VIDA DEL CANDIDATO:
    {texto_cv}
    
    SALIDA JSON OBLIGATORIA (Sin markdown):
    {{
        "nombre": "Nombre completo normalizado",
        "cedula": "Número de documento sin puntos",
        "fecha_grado": "DD/MM/AAAA",
        "veredicto": "CUMPLE" o "NO CUMPLE",
        "meses_exp": (Número entero de meses válidos),
        "alternativa": "Indica 'Alternativa 1', 'Alternativa 2' o 'N/A'",
        "empresas": "Lista resumida de empresas válidas",
        "observacion": "Breve justificación técnica del concepto (Máx 20 palabras)"
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        clean_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_json)
    except Exception as e:
        # En caso de error, devolvemos un diccionario con claves mínimas para evitar error
        return {
            "nombre": "Error de Lectura", 
            "cedula": "0", 
            "fecha_grado": "-", 
            "veredicto": "NO CUMPLE", 
            "meses_exp": 0, 
            "alternativa": "Error", 
            "empresas": "-", 
            "observacion": f"Error AI: {str(e)}"
        }

def llenar_plantilla_excel(dataframe, archivo_plantilla):
    """
    Toma la plantilla 2026_IDONEIDAD.xltx y vacía los datos en las celdas.
    """
    wb = openpyxl.load_workbook(archivo_plantilla)
    ws = wb.active 
    
    # Buscamos fila vacía
    start_row = ws.max_row + 1
    # Ajuste por si el max_row es engañoso (ej: plantilla con encabezados hasta fila 7)
    if start_row < 8: start_row = 8 
    
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    
    for index, row in dataframe.iterrows():
        # Usamos .get() o convertimos a string para evitar caídas si es None
        # Convertimos todo a string (str) excepto los números para evitar errores de escritura
        
        ws.cell(row=start_row, column=1, value=str(row['nombre'])).border = thin_border
        ws.cell(row=start_row, column=2, value=str(row['cedula'])).border = thin_border
        ws.cell(row=start_row, column=3, value=str(row['fecha_grado'])).border = thin_border
        ws.cell(row=start_row, column=4, value=row['meses_exp']).border = thin_border # Dejar como número
        ws.cell(row=start_row, column=5, value=str(row['empresas'])).border = thin_border
        ws.cell(row=start_row, column=6, value=str(row['alternativa'])).border = thin_border
        
        celda_concepto = ws.cell(row=start_row, column=7, value=str(row['veredicto']))
        celda_concepto.border = thin_border
        celda_concepto.alignment = Alignment(horizontal='center')
        
        ws.cell(row=start_row, column=8, value=str(row['observacion'])).border = thin_border
        
        start_row += 1

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

# --- INTERFAZ GRÁFICA ---

st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/Sena_Colombia_logo.svg/1200px-Sena_Colombia_logo.svg.png", width=120)
st.title("Sistema Experto de Evaluación - Idoneidad 2026")
st.markdown("Plataforma AI para validación de perfiles, cálculo de experiencia histórica y generación de informes.")

col_izq, col_der = st.columns([1, 1])

with col_izq:
    st.subheader("1. Configuración del Perfil (Norma)")
    st.info("Pegue aquí los requisitos completos, incluyendo Alternativa 1 y 2.")
    requisitos_txt = st.text_area("Requisitos:", height=200, placeholder="Ej: Título Profesional + 24 meses... O Alternativa 2...")

with col_der:
    st.subheader("2. Plantilla Institucional")
    st.info("Cargue el archivo '2026_IDONEIDAD.xltx' o '.xlsx'")
    archivo_plantilla = st.file_uploader("Formato Excel Base", type=["xlsx", "xltx"])

st.markdown("---")
st.subheader("3. Lote de Hojas de Vida")
archivos_pdf = st.file_uploader("Seleccione las HVs a evaluar (PDF)", type="pdf", accept_multiple_files=True)

# --- BOTÓN PRINCIPAL ---

if st.button("🚀 EJECUTAR EVALUACIÓN Y LLENAR FORMATO"):
    if not api_key or not requisitos_txt or not archivos_pdf:
        st.error("⚠️ Faltan datos: Asegúrese de tener API Key, Requisitos y Archivos cargados.")
    else:
        resultados = []
        barra = st.progress(0)
        status = st.empty()
        total = len(archivos_pdf)
        
        for i, pdf in enumerate(archivos_pdf):
            status.text(f"Analizando candidato {i+1}/{total}: {pdf.name}...")
            
            texto = extraer_texto_pdf(pdf)
            datos = consultar_cerebro_ia(texto, requisitos_txt)
            
            if datos:
                datos['archivo_origen'] = pdf.name
                resultados.append(datos)
            
            barra.progress((i + 1) / total)
            
        status.success("✅ Análisis finalizado. Consolidando archivo Excel...")
        
        # --- BLOQUE DE SEGURIDAD (CORRECCIÓN DEL ERROR KEYERROR) ---
        if resultados:
            df = pd.DataFrame(resultados)
            
            # 1. Definimos las columnas OBLIGATORIAS que espera el Excel
            columnas_obligatorias = [
                "nombre", "cedula", "fecha_grado", "meses_exp", 
                "empresas", "alternativa", "veredicto", "observacion"
            ]
            
            # 2. "Reindexamos": Si falta alguna columna, Pandas la crea y la llena con "-"
            # Esto evita el KeyError si la IA olvidó devolver la "cedula"
            df = df.reindex(columns=columnas_obligatorias).fillna("-")
            
            # 3. Aseguramos que 'meses_exp' sea numérico (poniendo 0 si hay texto raro)
            df['meses_exp'] = pd.to_numeric(df['meses_exp'], errors='coerce').fillna(0)

            # --- FIN BLOQUE DE SEGURIDAD ---
            
            st.write("### Vista Previa de Resultados")
            st.dataframe(df)
            
            if archivo_plantilla:
                excel_final = llenar_plantilla_excel(df, archivo_plantilla)
                nombre_archivo = "2026_IDONEIDAD_DILIGENCIADO.xlsx"
            else:
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False)
                output.seek(0)
                excel_final = output
                nombre_archivo = "Reporte_General_Idoneidad.xlsx"
            
            st.download_button(
                label="📥 DESCARGAR ARCHIVO CONSOLIDADO",
                data=excel_final,
                file_name=nombre_archivo,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        else:
            st.error("No se pudo extraer información de los documentos.")
