import streamlit as st
import pandas as pd
import re
import time

# --- 1. CONFIGURACIÓN CORPORATIVA (Debe ser la primera línea) ---
st.set_page_config(page_title="OmniLogistics OS", page_icon="🔐", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    [data-testid="stToolbarActions"], .stAppDeployButton, footer { display: none !important; }
    .main { background-color: #0e1117; }
    .login-box { background-color: #1a1c23; padding: 40px; border-radius: 12px; border-left: 5px solid #d4af37; box-shadow: 0 8px 20px rgba(0,0,0,0.5); text-align: center; }
</style>
""", unsafe_allow_html=True)

# --- 2. BÓVEDA DE SEGURIDAD (SISTEMA DE LOGIN) ---
if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    _, col_login, _ = st.columns([1, 1.2, 1])
    with col_login:
        st.markdown("<br><br><br><br>", unsafe_allow_html=True)
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.markdown("<h1 style='color: white; font-family: \"Arial Black\";'>OMNILOGISTICS OS</h1>", unsafe_allow_html=True)
        st.caption("ACCESO TÁCTICO RESTRINGIDO")
        st.markdown("---")
        
        usuario = st.text_input("👤 Credencial de Operador:")
        clave = st.text_input("🔑 Código de Autorización:", type="password")
        
        if st.button("🔓 Iniciar Secuencia de Desbloqueo", type="primary", use_container_width=True):
            # Credenciales maestras (Puedes cambiarlas luego)
            if usuario.lower() == "comandante" and clave == "omega2026":
                st.success("✅ Acceso Concedido. Iniciando turbinas...")
                time.sleep(1)
                st.session_state['autenticado'] = True
                st.rerun()
            else:
                st.error("🚨 Credenciales denegadas. Intento registrado en bitácora.")
        st.markdown("</div>", unsafe_allow_html=True)
    
    # 🛑 MURO DE CONTENCIÓN: Si no está autenticado, el código muere aquí.
    st.stop()

# =====================================================================
# 🟢 ZONA SEGURA: EL CÓDIGO DE TU APP COMIENZA AQUÍ
# =====================================================================

# --- IMPORTACIÓN DE MÓDULOS AISLADOS ---
import modulos.m1_dashboard as m1
import modulos.m2_smart_split as m2
import modulos.m3_auditoria as m3
import modulos.m4_limpieza as m4

# --- MEMORIA CACHÉ ---
@st.cache_data(show_spinner=False)
def leer_archivo_cacheado(archivo):
    df = pd.read_csv(archivo) if archivo.name.endswith('.csv') else pd.read_excel(archivo)
    df['_Origen_Archivo'] = archivo.name
    return df

@st.cache_data(show_spinner=False)
def leer_url_cacheado(url_input):
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', url_input)
    if match:
        url_csv = f"https://docs.google.com/spreadsheets/d/{match.group(1)}/export?format=csv"
        df = pd.read_csv(url_csv)
        df['_Origen_Archivo'] = "Google_Sheets"
        return df
    return pd.DataFrame()

# --- MOTOR DE CARGA MULTI-ARCHIVO ---
def procesar_fuentes_datos(archivos_subidos, url_input):
    if archivos_subidos and len(archivos_subidos) > 0:
        lista_dfs = []
        for arch in archivos_subidos:
            try:
                lista_dfs.append((arch.name, leer_archivo_cacheado(arch)))
            except Exception: pass
        if lista_dfs: return lista_dfs, "Archivos Cliente"

    if url_input and url_input.strip() != "":
        df_url = leer_url_cacheado(url_input)
        if not df_url.empty:
            return [("Google_Sheets", df_url)], "Nube Externa"

    return [], "Sin Datos"

# --- BARRA LATERAL ---
with st.sidebar:
    st.markdown("## 🌐 OmniLogistics OS")
    st.caption("Arquitectura B2B de Alto Rendimiento")
    st.markdown("---")
    menu = st.radio("Módulos Operativos:", [
        "📊 1. Command Center (Dashboard)",
        "⚙️ 2. Motor de Costos (Smart Split)",
        "🛡️ 3. Auditoría en la Nube",
        "📥 4. Ingesta y Limpieza Financiera"
    ])
    st.markdown("---")
    st.markdown("**📥 Carga Multi-Archivo:**")
    archivos_cliente = st.file_uploader("Sube archivos (CSV/Excel):", type=['csv', 'xlsx'], accept_multiple_files=True)
    url_input = st.text_input("🔗 Conectar Nube Externa:", placeholder="Pegar enlace...")
    
    st.markdown("---")
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state['autenticado'] = False
        st.rerun()

fuentes, tipo_origen = procesar_fuentes_datos(archivos_cliente, url_input)

# --- SELECTOR MULTI-ARCHIVO ---
df_base = pd.DataFrame()
fuente_activa = "Ninguna"

if fuentes:
    if len(fuentes) > 1:
        st.sidebar.markdown("---")
        modo_multi = st.sidebar.radio("Procesamiento:", ["⚡ Consolidado", "🔍 Archivo Único"])
        if modo_multi == "⚡ Consolidado":
            df_base = pd.concat([item[1] for item in fuentes], ignore_index=True)
            fuente_activa = f"Consolidado Global ({len(fuentes)} archivos)"
        else:
            archivo_sel = st.sidebar.selectbox("Seleccionar reporte:", [item[0] for item in fuentes])
            df_base = next(item[1] for item in fuentes if item[0] == archivo_sel)
            fuente_activa = f"Archivo: {archivo_sel}"
    else:
        df_base = fuentes[0][1]
        fuente_activa = fuentes[0][0]

# --- ENRUTAMIENTO BLINDADO ---
if menu == "📊 1. Command Center (Dashboard)":
    m1.ejecutar(df_base, fuente_activa)
elif menu == "⚙️ 2. Motor de Costos (Smart Split)":
    m2.ejecutar(df_base)
elif menu == "🛡️ 3. Auditoría en la Nube":
    m3.ejecutar(df_base)
elif menu == "📥 4. Ingesta y Limpieza Financiera":
    m4.ejecutar(df_base)
