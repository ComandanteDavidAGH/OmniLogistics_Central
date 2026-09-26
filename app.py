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
# Las credenciales se leen de st.secrets si existen (recomendado para producción /
# clientes reales). Si no hay secrets.toml configurado, se usa un valor de respaldo
# SOLO para pruebas locales. Antes de entregar la app a un cliente, configura
# APP_USER y APP_PASS en .streamlit/secrets.toml.
try:
    USUARIO_VALIDO = st.secrets["APP_USER"]
    CLAVE_VALIDA = st.secrets["APP_PASS"]
except Exception:
    USUARIO_VALIDO = "comandante"
    CLAVE_VALIDA = "omega2026"

if 'autenticado' not in st.session_state:
    st.session_state['autenticado'] = False

if not st.session_state['autenticado']:
    _, col_login, _ = st.columns([1, 1.2, 1])
    with col_login:
        st.markdown("<br><br><br><br>", unsafe_allow_html=True)
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.markdown("<h1 style='color: white; font-family: \"Arial Black\";'>OMNILOGISTICS OS</h1>", unsafe_allow_html=True)
        st.caption("ACCESO RESTRINGIDO")
        st.markdown("---")

        usuario = st.text_input("👤 Usuario:")
        clave = st.text_input("🔑 Contraseña:", type="password")

        if st.button("🔓 Ingresar", type="primary", use_container_width=True):
            if usuario.lower() == USUARIO_VALIDO.lower() and clave == CLAVE_VALIDA:
                st.success("✅ Acceso concedido...")
                time.sleep(0.6)
                st.session_state['autenticado'] = True
                st.rerun()
            else:
                st.error("🚨 Credenciales incorrectas.")
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
            except Exception as e:
                st.sidebar.error(f"⚠️ No se pudo leer '{arch.name}': {e}")
        if lista_dfs:
            return lista_dfs, "Archivos Cliente"

    if url_input and url_input.strip() != "":
        try:
            df_url = leer_url_cacheado(url_input)
            if not df_url.empty:
                return [("Google_Sheets", df_url)], "Nube Externa"
        except Exception as e:
            st.sidebar.error(f"⚠️ No se pudo leer el enlace: {e}")

    return [], "Sin Datos"

# --- BARRA LATERAL ---
with st.sidebar:
    st.markdown("## 🌐 OmniLogistics OS")
    st.caption("Limpieza, orden e inteligencia para tu negocio")
    st.markdown("---")
    menu = st.radio("Módulos:", [
        "📊 1. Dashboard (Centro de Mando)",
        "⚙️ 2. Motor de Fórmulas y Ajustes %",
        "🛡️ 3. Auditoría de Calidad de Datos",
        "📥 4. Limpieza y Exportación"
    ])
    st.markdown("---")
    st.markdown("**📥 Carga de Datos:**")
    archivos_cliente = st.file_uploader("Sube tus archivos (CSV/Excel):", type=['csv', 'xlsx'], accept_multiple_files=True)
    url_input = st.text_input("🔗 O pega un enlace de Google Sheets:", placeholder="Pegar enlace...")

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
            archivo_sel = st.sidebar.selectbox("Seleccionar archivo:", [item[0] for item in fuentes])
            df_base = next(item[1] for item in fuentes if item[0] == archivo_sel)
            fuente_activa = f"Archivo: {archivo_sel}"
    else:
        df_base = fuentes[0][1]
        fuente_activa = fuentes[0][0]

# --- ENRUTAMIENTO ---
if menu == "📊 1. Dashboard (Centro de Mando)":
    m1.ejecutar(df_base, fuente_activa)
elif menu == "⚙️ 2. Motor de Fórmulas y Ajustes %":
    m2.ejecutar(df_base)
elif menu == "🛡️ 3. Auditoría de Calidad de Datos":
    m3.ejecutar(df_base)
elif menu == "📥 4. Limpieza y Exportación":
    m4.ejecutar(df_base)
