import streamlit as st
import google.generativeai as genai
import PyPDF2
import pandas as pd
import json

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="SENA Evaluador AI", page_icon="🤖", layout="wide")

# --- ESTILOS VISUALES SENA ---
ESTILO_CUMPLE = """
    <div style='background-color: #39A900; color: white; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px;'>
        <h1 style='margin:0;'>✅ CUMPLE EL PERFIL</h1>
        <p style='font-size: 18px;'>Candidato Idóneo según análisis AI</p>
    </div>
"""
ESTILO_NO_CUMPLE = """
    <div style='background-color: #FF671F; color: white; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px;'>
        <h1 style='margin:0;'>⚠️ REVISIÓN REQUERIDA</h1>
        <p style='font-size: 18px;'>La AI detectó inconsistencias con los requisitos</p>
    </div>
"""

# --- BARRA LATERAL PARA LA LLAVE (Seguridad) ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/8/83/Sena_Colombia_logo.svg/1200px-Sena_Colombia_logo.svg.png", width=150)
    st.header("Configuración AI")
    # Para compartir el link, lo ideal es usar st.secrets, pero por ahora lo pedimos aquí
    api_key = st.text_input("Ingresa tu Google API Key:", type="password")
    st.info("Esta llave conecta la App con los servidores de Google Gemini.")

# --- FUNCIONES ---

def extraer_texto_pdf(archivo):
    """Lee el PDF y lo convierte en texto plano."""
    pdf_reader = PyPDF2.PdfReader(archivo)
    texto = ""
    for pagina in pdf_reader.pages:
        txt = pagina.extract_text()
        if txt: texto += txt + "\n"
    return texto

def analizar_con_gemini(texto_cv, requisitos, fecha_grado):
    """
    Envía la HV y los requisitos a Gemini y pide una respuesta en formato JSON estricto.
    """
    if not api_key:
        return None
    
    # Configuramos el modelo
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash') # Modelo rápido y eficiente
    
    # EL PROMPT (LAS INSTRUCCIONES PARA LA IA)
    prompt = f"""
    Actúa como un analista experto de Talento Humano del SENA.
    Tu tarea es evaluar una hoja de vida frente a unos requisitos y extraer la experiencia laboral válida.
    
    CONTEXTO:
    1. La experiencia laboral solo es válida si ocurrió DESPUÉS de la fecha de grado: {fecha_grado}.
    2. Debes ignorar experiencias previas a esa fecha.
    
    REQUISITOS DEL CARGO:
    {requisitos}
    
    TEXTO DE LA HOJA DE VIDA:
    {texto_cv}
    
    INSTRUCCIONES DE SALIDA:
    Responde ÚNICAMENTE con un objeto JSON (sin markdown, sin explicaciones extra) con esta estructura:
    {{
        "veredicto": "CUMPLE" o "NO CUMPLE",
        "justificacion": "Breve explicación de por qué cumple o no",
        "experiencia_valida": [
            {{
                "empresa": "Nombre exacto de la empresa o institución",
                "cargo": "Cargo desempeñado",
                "fecha_inicio": "DD/MM/AAAA",
                "fecha_fin": "DD/MM/AAAA",
                "meses": (numero entero de meses calculados)
            }}
        ],
        "total_meses_experiencia": (suma total de meses validos)
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        # Limpiamos la respuesta por si la IA pone ```json al principio
        texto_limpio = response.text.replace("```json", "").replace("```", "").strip()
        datos = json.loads(texto_limpio)
        return datos
    except Exception as e:
        st.error(f"Error al conectar con Gemini: {e}")
        return None

# --- INTERFAZ PRINCIPAL ---

st.title("Validador Inteligente SENA (Powered by Gemini 🧠)")
st.markdown("Herramienta avanzada para análisis de idoneidad y extracción de datos.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Perfil y Candidato")
    nombre = st.text_input("Nombre del Aspirante")
    requisitos = st.text_area("Requisitos del Perfil", height=150, placeholder="Ej: Ingeniero de Sistemas con especialización, 24 meses de experiencia docente...")

with col2:
    st.subheader("2. Parámetros de Validación")
    fecha_grado = st.date_input("Fecha de Grado (Punto de corte)", value=None)
    archivo = st.file_uploader("Cargar HV (PDF)", type="pdf")

# BOTÓN DE ANÁLISIS
if st.button("🚀 INICIAR ANÁLISIS IA"):
    if not api_key:
        st.warning("⚠️ Por favor ingresa tu API Key en la barra lateral izquierda.")
    elif not archivo or not requisitos or not fecha_grado:
        st.warning("⚠️ Completa todos los campos.")
    else:
        with st.spinner("Gemini está leyendo el documento, validando fechas y empresas..."):
            
            # 1. Leer PDF
            texto_pdf = extraer_texto_pdf(archivo)
            
            # 2. Consultar a la IA
            resultado_ai = analizar_con_gemini(texto_pdf, requisitos, str(fecha_grado))
            
            if resultado_ai:
                st.markdown("---")
                
                # 3. Mostrar Veredicto Visual
                if resultado_ai["veredicto"] == "CUMPLE":
                    st.markdown(ESTILO_CUMPLE, unsafe_allow_html=True)
                else:
                    st.markdown(ESTILO_NO_CUMPLE, unsafe_allow_html=True)
                
                st.write(f"**Justificación de la IA:** {resultado_ai['justificacion']}")
                
                # 4. Tabla de Experiencia Detallada
                st.subheader("📊 Desglose de Experiencia Válida (Post-Grado)")
                experiencias = resultado_ai["experiencia_valida"]
                
                if experiencias:
                    df = pd.DataFrame(experiencias)
                    # Reordenar columnas para mejor lectura
                    df = df[["empresa", "cargo", "fecha_inicio", "fecha_fin", "meses"]]
                    st.table(df)
                    
                    st.metric("Total Experiencia Validada", f"{resultado_ai['total_meses_experiencia']} Meses")
                else:
                    st.info("No se encontró experiencia válida posterior a la fecha de grado.")