import streamlit as st
import pandas as pd
import time
import re

# --- CONFIGURACIÓN CORPORATIVA ---
st.set_page_config(page_title="OmniLogistics OS | Demo", page_icon="🌐", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .titulo-principal { color: #ffffff; font-family: 'Arial Black', sans-serif; font-size: 28px; border-bottom: 3px solid #d4af37; padding-bottom: 10px; margin-bottom: 20px; text-transform: uppercase; }
    .kpi-card { background-color: #1a1c23; border-left: 5px solid #d4af37; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .kpi-title { color: #a0aec0; font-size: 12px; text-transform: uppercase; font-weight: bold; margin-bottom: 5px; }
    .kpi-value { color: #ffffff; font-size: 28px; font-weight: 900; margin: 0; }
</style>
""", unsafe_allow_html=True)

# --- MOTOR DE EXTRACCIÓN DE DATOS ---
@st.cache_data(ttl=60)
def cargar_base_datos(url):
    # Si el usuario proporciona una URL de Google Sheets
    if url and url.strip() != "":
        try:
            match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
            if match:
                doc_id = match.group(1)
                url_csv = f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv"
                df = pd.read_csv(url_csv)
                return df, "Google Sheets"
        except Exception:
            pass

    # Fallback automático al archivo demo con 1,500 registros
    try:
        df = pd.read_csv("datos_logistica_demo.csv")
        return df, "Demo Central (1,500 Registros)"
    except Exception:
        return None, "Error"

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
    url_input = st.text_input("🔗 Conectar Google Sheet (Opcional):", placeholder="Pega URL o deja en blanco...")

# Carga de la base de datos
df_base, fuente = cargar_base_datos(url_input)

# --- MÓDULO 1: COMMAND CENTER ---
if menu == "📊 1. Command Center (Dashboard)":
    st.markdown("<div class='titulo-principal'>Centro de Mando Logístico</div>", unsafe_allow_html=True)

    if df_base is not None and not df_base.empty:
        st.success(f"✅ Sistema sincronizado correctamente. Fuente de datos: **{fuente}**")
        
        # Validación de columnas para el archivo de 1,500 datos
        total_despachos = len(df_base)
        
        if 'Costo_Real' in df_base.columns:
            costo_total = df_base['Costo_Real'].sum()
        else:
            costo_total = 0

        if 'Estatus' in df_base.columns:
            retrasados = len(df_base[df_base['Estatus'] == 'Retrasado'])
        else:
            retrasados = 0

        pct_retraso = (retrasados / total_despachos * 100) if total_despachos > 0 else 0

        # Tarjetas de KPI
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='kpi-card'><div class='kpi-title'>Total Despachos</div><p class='kpi-value'>{total_despachos:,}</p></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='kpi-card' style='border-left-color: #28a745;'><div class='kpi-title'>Costo Operativo Real</div><p class='kpi-value'>${costo_total:,.0f}</p></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='kpi-card' style='border-left-color: #dc3545;'><div class='kpi-title'>Novedades / Retrasos</div><p class='kpi-value'>{retrasados}</p></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='kpi-card' style='border-left-color: #17a2b8;'><div class='kpi-title'>% Tasa de Ineficiencia</div><p class='kpi-value'>{pct_retraso:.1f}%</p></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Gráficos dinámicos
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("### 🚚 Operaciones por Transportista")
            if 'Transportista' in df_base.columns:
                st.bar_chart(df_base['Transportista'].value_counts())
            else:
                st.info("Columna 'Transportista' no disponible en esta vista.")

        with col_b:
            st.markdown("### 📍 Distribución por Estatus")
            if 'Estatus' in df_base.columns:
                st.bar_chart(df_base['Estatus'].value_counts())
            else:
                st.info("Columna 'Estatus' no disponible en esta vista.")

        st.markdown("### 📦 Detalle de Operaciones en Registro")
        st.dataframe(df_base, use_container_width=True, hide_index=True)
    else:
        st.error("🚨 Error al cargar la base de datos. Asegúrate de que 'datos_logistica_demo.csv' esté subido en la raíz de tu repositorio de GitHub.")

# --- MÓDULO 2: MOTOR DE COSTOS ---
elif menu == "⚙️ 2. Motor de Costos (Smart Split)":
    st.markdown("<div class='titulo-principal'>Motor de Prorrateo Dinámico</div>", unsafe_allow_html=True)
    
    if df_base is not None and not df_base.empty and 'Costo_Proyectado' in df_base.columns and 'Costo_Real' in df_base.columns:
        st.write("Análisis de variación presupuestal y ajuste de carga operativa.")
        
        df_split = df_base.copy()
        df_split['Variacion'] = df_split['Costo_Real'] - df_split['Costo_Proyectado']
        
        overhead = st.slider("⚙️ Ajuste de Carga Administrativa (Overhead %):", min_value=0, max_value=50, value=15, step=1)
        df_split['Costo_Ajustado'] = df_split['Costo_Real'] * (1 + (overhead / 100))
        
        columnas_mostrar = ['ID_Despacho', 'Origen', 'Destino', 'Transportista', 'Costo_Proyectado', 'Costo_Real', 'Variacion', 'Costo_Ajustado']
        df_mostrar = df_split[[c for c in columnas_mostrar if c in df_split.columns]]
        
        st.dataframe(df_mostrar.style.format({
            'Costo_Proyectado': '${:,.0f}',
            'Costo_Real': '${:,.0f}',
            'Variacion': '${:,.0f}',
            'Costo_Ajustado': '${:,.0f}'
        }), use_container_width=True, hide_index=True)
    else:
        st.warning("Se requiere la base de datos de demo para calcular el prorrateo de costos.")

# --- MÓDULO 3: AUDITORÍA ---
elif menu == "🛡️ 3. Auditoría en la Nube":
    st.markdown("<div class='titulo-principal'>Auditoría de Ineficiencias</div>", unsafe_allow_html=True)
    if df_base is not None and 'Dias_Retraso' in df_base.columns:
        df_anomalias = df_base[df_base['Dias_Retraso'] > 0]
        st.warning(f"⚠️ Se detectaron {len(df_anomalias)} despachos con sobrecostos o retrasos en la operación.")
        st.dataframe(df_anomalias, use_container_width=True, hide_index=True)
    else:
        st.info("Sin registros de auditoría pendientes.")

# --- MÓDULO 4: INGESTA Y LIMPIEZA ---
elif menu == "📥 4. Ingesta y Limpieza Financiera":
    st.markdown("<div class='titulo-principal'>Motor de Limpieza Financiera</div>", unsafe_allow_html=True)
    st.write("Demostración interactiva de procesamiento de sábanas crudas de Excel.")
    
    if st.button("🚀 Simular Limpieza de Datos Crudos"):
        with st.spinner("Procesando estructura..."):
            time.sleep(1)
            st.success("✅ 1,500 Registros validados, limpios y normalizados en 0.8 segundos.")
