import pandas as pd
import io
import re

import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import os

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="SENA CIES - Validador de Instructores",
    page_icon="✅",
    layout="wide"
)

# --- SIDEBAR / CONFIGURACIÓN ---
with st.sidebar:
    # Logo Oficial SENA (Sin filtros)
    st.image("https://www.sena.edu.co/Style%20Library/alayout/images/logoSena.png", width=150)
    st.header("Configuración")
    
    # Dark Mode Toggle
    dark_mode = st.toggle("🌙 Modo Oscuro", value=False)
    
    # API Key Management
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        api_key = st.text_input("Ingresa tu Google API Key", type="password")
    
    if api_key:
        genai.configure(api_key=api_key)
        st.success("API Key configurada")
    else:
        st.warning("Necesitas una API Key para continuar.")

# --- ESTILOS CSS DINÁMICOS ---
if dark_mode:
    # Variables Modo Oscuro
    bg_color = "#0e1117"
    text_color = "#fafafa"
    card_bg = "#262730"
    input_bg = "#1e1e1e"
    border_color = "#444"
    header_text = "#ffffff"
else:
    # Variables Modo Claro (Original)
    bg_color = "#f4f7f6"
    text_color = "#333"
    card_bg = "white"
    input_bg = "white"
    border_color = "#ddd"
    header_text = "#00324d"

st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600;700&display=swap');

        :root {{
            /* COLORES INSTITUCIONALES SENA */
            --sena-green: #39A900;       /* Principal */
            --sena-dark-blue: #00324D;   /* Principal */
            --sena-light-blue: #82DEF0;  /* Principal */
            --sena-yellow: #FFCE40;      /* Secundario */
            --sena-dark-grey: #385C57;   /* Secundario */
            
            /* Variables de Tema */
            --bg-color: {bg_color};
            --text-color: {text_color};
            --card-bg: {card_bg};
            --input-bg: {input_bg};
            --border-color: {border_color};
            --header-text: {header_text};
        }}

        /* Override Streamlit Defaults */
        .stApp {{
            background-color: var(--bg-color);
            font-family: 'Segoe UI', sans-serif;
            color: var(--text-color);
        }}
        
        /* Ocultar elementos nativos de Streamlit que no queremos */
        #MainMenu {{visibility: hidden;}}
        footer {{visibility: hidden;}}
        header {{visibility: hidden;}}

        /* Encabezado Personalizado */
        .main-header {{
            background-color: var(--sena-green);
            padding: 1.5rem;
            text-align: center;
            color: white;
            border-bottom: 5px solid var(--sena-dark-blue);
            margin-bottom: 2rem;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            border-radius: 0 0 10px 10px;
        }}
        .main-header h1 {{ 
            color: white; 
            margin: 0; 
            font-size: 1.8rem; 
            font-family: 'Segoe UI', sans-serif;
            font-weight: 700;
        }}
        .main-header h2 {{ 
            color: white; 
            margin: 0.5rem 0 0; 
            font-size: 1.2rem; 
            font-weight: 400; 
            opacity: 0.9; 
            font-family: 'Segoe UI', sans-serif;
        }}

        /* Paneles (Contenedores de Streamlit) */
        div[data-testid="stVerticalBlock"] > div {{
            background-color: var(--card-bg);
            padding: 1rem;
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        }}
        
        /* Headers de los paneles */
        h3 {{
            color: var(--header-text) !important;
            font-weight: 700 !important;
            font-size: 1.2rem !important;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 1rem;
            margin-bottom: 1.5rem;
            font-family: 'Segoe UI', sans-serif !important;
        }}

        /* Inputs y TextAreas */
        .stTextInput input, .stTextArea textarea {{
            background-color: var(--input-bg);
            color: var(--text-color);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 12px;
            transition: border-color 0.3s;
        }}
        .stTextInput input:focus, .stTextArea textarea:focus {{
            border-color: var(--sena-green) !important;
            box-shadow: none !important;
        }}
        
        /* Labels de inputs */
        .stTextInput label, .stTextArea label, .stFileUploader label {{
            color: var(--text-color) !important;
        }}

        /* Botón Principal */
        .stButton button {{
            background-color: var(--sena-dark-blue) !important;
            color: white !important;
            border: none !important;
            padding: 15px 25px !important;
            font-size: 1rem !important;
            font-weight: bold !important;
            border-radius: 8px !important;
            cursor: pointer !important;
            width: 100% !important;
            transition: background 0.3s, transform 0.1s !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important;
        }}
        .stButton button:hover {{
            background-color: #004d73 !important;
            transform: translateY(-1px) !important;
        }}
        .stButton button:active {{
            transform: translateY(1px) !important;
        }}

        /* Resultados */
        .result-container {{
            background-color: var(--card-bg);
            padding: 2.5rem;
            margin-top: 1rem;
            border-radius: 12px;
            border-top: 6px solid var(--sena-yellow); /* Usando Amarillo Secundario */
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
            color: var(--text-color);
        }}
        
        /* Markdown en Resultados */
        .result-container h1, .result-container h2, .result-container h3 {{
            color: var(--header-text);
            margin-top: 1.5rem;
            border-bottom: none;
        }}
        
        /* Tablas en Resultados */
        .result-container table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            font-size: 0.95rem;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 0 0 1px var(--border-color);
            color: var(--text-color);
        }}
        .result-container th {{
            background-color: var(--input-bg);
            color: var(--header-text);
            font-weight: 700;
            text-transform: uppercase;
            font-size: 0.85rem;
            padding: 12px 15px;
            text-align: left;
            border-bottom: 2px solid var(--border-color);
        }}
        .result-container td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}
    </style>
""", unsafe_allow_html=True)

# --- LÓGICA DE NEGOCIO ---
def extraer_texto_pdf(uploaded_file):
    try:
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"[Error leyendo PDF: {str(e)}]"

import json
import openpyxl
from openpyxl.styles import Alignment

# ... (previous code)

# --- LÓGICA DE NEGOCIO ---
def extraer_texto_pdf(uploaded_file):
    try:
        reader = PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"[Error leyendo PDF: {str(e)}]"

def fill_excel_template(data_json, template_path="2026_IDONEIDAD.xlsx"):
    try:
        if not os.path.exists(template_path):
            return None, f"El archivo plantilla '{template_path}' no se encuentra en el servidor."

        wb = openpyxl.load_workbook(template_path)
        ws = wb.active
        
        # 1. Datos Personales
        if 'nombre' in data_json:
            ws['G10'] = data_json['nombre']
        if 'cedula' in data_json:
            ws['F11'] = data_json['cedula']
            
        # 2. Idoneidad y Formación
        if 'idoneidad_texto' in data_json:
            ws['D14'] = data_json['idoneidad_texto']
            ws['D14'].alignment = Alignment(wrap_text=True, vertical='top')
            
        if 'formacion_texto' in data_json:
            ws['I15'] = data_json['formacion_texto']
            ws['I15'].alignment = Alignment(wrap_text=True, vertical='top')
            
        # 3. Tabla de Experiencia
        if 'experiencia_lista' in data_json:
            start_row = 24
            for i, exp in enumerate(data_json['experiencia_lista']):
                current_row = start_row + i
                ws[f'D{current_row}'] = exp.get('empresa', '')
                ws[f'E{current_row}'] = exp.get('fecha_inicio', '')
                ws[f'F{current_row}'] = exp.get('fecha_fin', '')
                
        output = io.BytesIO()
        wb.save(output)
        return output.getvalue(), None
    except Exception as e:
        return None, str(e)

# --- INTERFAZ PRINCIPAL ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("📋 1. Requisitos del Perfil")
    
    tab_pdf, tab_text = st.tabs(["Subir PDF", "Pegar Texto"])
    
    with tab_pdf:
        requisitos_pdf = st.file_uploader("Cargar PDF del Perfil", type=["pdf"], key="req_pdf")
    
    with tab_text:
        requisitos_text = st.text_area("Pegar requisitos manualmente", height=200, placeholder="Copie y pegue aquí los requisitos...")

with col2:
    st.subheader("👤 2. Datos del Candidato")
    nombre = st.text_input("Nombre Completo", placeholder="Ej: Juan Pérez")
    identificacion = st.text_input("Identificación (ID)", placeholder="Ej: 123456789")
    
    st.subheader("📂 Soportes (Evidencias)")
    soportes = st.file_uploader("Cargar Hojas de Vida y Soportes", type=["pdf"], accept_multiple_files=True, key="soportes")

# --- BOTÓN DE ACCIÓN ---
if st.button("EVALUAR CANDIDATO", type="primary"):
    if not api_key:
        st.error("❌ Por favor configura tu API Key en el menú lateral.")
    elif not (requisitos_pdf or requisitos_text):
        st.error("❌ Debes proporcionar los requisitos (PDF o Texto).")
    elif not soportes:
        st.error("❌ Debes subir al menos un soporte PDF.")
    else:
        with st.spinner("⏳ Analizando documentos con IA... Por favor espera."):
            try:
                # 1. Procesar Requisitos
                texto_requisitos = ""
                if requisitos_pdf:
                    texto_requisitos += f"--- REQUISITOS (Desde PDF: {requisitos_pdf.name}) ---\n"
                    texto_requisitos += extraer_texto_pdf(requisitos_pdf) + "\n"
                if requisitos_text:
                    texto_requisitos += f"\n--- REQUISITOS (Texto Adicional) ---\n{requisitos_text}\n"

                # 2. Procesar Soportes
                texto_evidencia = ""
                for arch in soportes:
                    texto_evidencia += f"\n--- SOPORTE: {arch.name} ---\n{extraer_texto_pdf(arch)}\n"

                # 3. Construir Prompt JSON
                sena_instruction = """
                Eres el Auditor de Contratación del SENA.
                Tu tarea PRINCIPAL es determinar si el candidato CUMPLE o NO CUMPLE.
                
                CRITERIO DE EVALUACIÓN:
                - Para dictaminar "CUMPLE", el candidato debe cumplir con EL 100% de los requisitos de Formación y Experiencia.
                - Si falta UN SOLO requisito (ej: falta tiempo de experiencia, título no afín), el dictamen es "NO CUMPLE".

                SALIDA ESPERADA (JSON ÚNICAMENTE):
                {
                    "nombre": "Nombre del candidato",
                    "cedula": "ID del candidato",
                    "concepto_final": "CUMPLE o NO CUMPLE",
                    "idoneidad_texto": "Justificación detallada del concepto final.",
                    "formacion_texto": "Lista detallada de títulos académicos encontrados.",
                    "experiencia_lista": [
                        {
                            "empresa": "Nombre Empresa", 
                            "fecha_inicio": "DD/MM/AAAA", 
                            "fecha_fin": "DD/MM/AAAA",
                            "meses": "Número de meses (entero)",
                            "dias": "Número de días (entero)",
                            "validada": "Si o No (Basado en si cumple con la experiencia relacionada requerida)"
                        }
                    ],
                    "analisis_detallado_markdown": "Tabla Markdown detallada de cumplimiento."
                }
                """

                prompt = f"""
                CANDIDATO: {nombre} (ID: {identificacion})
                
                === PERFIL REQUERIDO ===
                {texto_requisitos}
                
                === DOCUMENTOS ===
                {texto_evidencia}
                """

                # 4. Llamar a Gemini (Modelo Disponible: Gemini 2.0 Flash)
                model = genai.GenerativeModel(
                    model_name="gemini-2.0-flash",
                    generation_config={"temperature": 0.1, "response_mime_type": "application/json"},
                    system_instruction=sena_instruction
                )
                
                response = model.generate_content(prompt)
                
                # Parsear JSON
                data_json = json.loads(response.text)
                
                # 5. Mostrar Resultados (Markdown)
                st.markdown("<div class='result-container'>", unsafe_allow_html=True)
                
                # --- DICTAMEN FINAL VISUAL ---
                concepto = data_json.get('concepto_final', 'NO CUMPLE').upper()
                if "CUMPLE" in concepto and "NO" not in concepto:
                    st.markdown("""
                        <div style='background-color: #39a900; color: white; padding: 20px; border-radius: 10px; text-align: center; font-size: 24px; font-weight: bold; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
                            ✅ EL CANDIDATO CUMPLE CON EL PERFIL
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown("""
                        <div style='background-color: #fc7323; color: white; padding: 20px; border-radius: 10px; text-align: center; font-size: 24px; font-weight: bold; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
                            ⚠️ EL CANDIDATO NO CUMPLE CON EL PERFIL
                        </div>
                    """, unsafe_allow_html=True)

                st.markdown("### 📊 Informe de Auditoría")
                
                if 'analisis_detallado_markdown' in data_json:
                    st.markdown(data_json['analisis_detallado_markdown'])
                else:
                    st.markdown(data_json.get('idoneidad_texto', 'Sin análisis.'))
                
                # --- NUEVO: TABLA DE EXPERIENCIA PREVIA ---
                st.markdown("### 🗓️ Detalle de Experiencia Laboral")
                if 'experiencia_lista' in data_json and data_json['experiencia_lista']:
                    # Crear DataFrame para mostrar
                    df_exp = pd.DataFrame(data_json['experiencia_lista'])
                    
                    # Renombrar columnas para que coincidan con lo solicitado
                    column_mapping = {
                        'empresa': 'NOMBRE EMPRESA',
                        'fecha_inicio': 'FECHA INICIO',
                        'fecha_fin': 'FECHA FINAL',
                        'meses': 'MESES',
                        'dias': 'DÍAS',
                        'validada': 'VALIDADA (Si/No)'
                    }
                    
                    # Asegurar que existan las columnas aunque vengan vacías
                    for col in column_mapping.keys():
                        if col not in df_exp.columns:
                            df_exp[col] = ""
                            
                    df_display = df_exp[list(column_mapping.keys())].rename(columns=column_mapping)
                    st.table(df_display)
                else:
                    st.info("No se detectó experiencia laboral estructurada.")

                # 6. Exportar a Excel (Plantilla)
                excel_data, error_msg = fill_excel_template(data_json)
                
                if excel_data:
                    st.download_button(
                        label="📥 Generar y Descargar Archivo Excel",
                        data=excel_data,
                        file_name=f"IDONEIDAD_{nombre.replace(' ', '_')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                else:
                    st.error(f"No se pudo generar el archivo Excel. Error: {error_msg}")
                
                st.markdown("</div>", unsafe_allow_html=True)

            except Exception as e:
                st.error(f"Ocurrió un error durante el análisis: {str(e)}")
