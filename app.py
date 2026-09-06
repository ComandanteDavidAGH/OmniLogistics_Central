import streamlit as st
import pandas as pd
import time
import re
import plotly.express as px

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

# --- MOTOR DE CARGA DINÁMICA DE DATOS ---
def cargar_base_datos(archivo_subido, url_input):
    if archivo_subido is not None:
        try:
            df = pd.read_csv(archivo_subido) if archivo_subido.name.endswith('.csv') else pd.read_excel(archivo_subido)
            return df, f"Archivo Cliente ({archivo_subido.name})"
        except Exception as e:
            st.sidebar.error(f"Error al leer el archivo: {e}")

    if url_input and url_input.strip() != "":
        try:
            match = re.search(r'/d/([a-zA-Z0-9-_]+)', url_input)
            if match:
                url_csv = f"https://docs.google.com/spreadsheets/d/{match.group(1)}/export?format=csv"
                return pd.read_csv(url_csv), "Bóveda Nube (Google Sheets)"
        except Exception:
            pass

    try:
        return pd.read_csv("datos_logistica_demo.csv"), "Demo Central (Fletes y Rutas)"
    except Exception:
        return None, "Sin Fuente de Datos"

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
    st.markdown("**📥 Ingesta de Datos (Drag & Drop):**")
    archivo_cliente = st.file_uploader("Arrastra tu Excel/CSV aquí:", type=['csv', 'xlsx'])
    url_input = st.text_input("🔗 Conectar Nube Externa:", placeholder="Pegar enlace...")

df_base, fuente = cargar_base_datos(archivo_cliente, url_input)

# --- MÓDULO 1: COMMAND CENTER ---
if menu == "📊 1. Command Center (Dashboard)":
    st.markdown("<div class='titulo-principal'>Centro de Mando Operativo</div>", unsafe_allow_html=True)

    if df_base is not None and not df_base.empty:
        st.success(f"✅ Enlace seguro establecido. Origen: **{fuente}**")
        
        # Inteligencia para encontrar columnas financieras y de estado (Agnóstico)
        col_costo = [c for c in df_base.columns if any(palabra in c.lower() for palabra in ['costo', 'valor', 'monto', 'precio'])]
        col_estatus = [c for c in df_base.columns if any(palabra in c.lower() for palabra in ['estatus', 'estado', 'salud', 'condicion'])]
        col_categoria = [c for c in df_base.columns if any(palabra in c.lower() for palabra in ['transp', 'proveedor', 'categoria', 'bodega', 'origen'])]

        # Cálculos de KPI
        total_filas = len(df_base)
        costo_total = df_base[col_costo[0]].sum() if col_costo else 0
        
        if col_estatus:
            df_base[col_estatus[0]] = df_base[col_estatus[0]].astype(str)
            novedades = len(df_base[df_base[col_estatus[0]].str.lower().str.contains('retras|novedad|pendiente|quiebre|sobre')])
        else:
            novedades = 0
            
        pct_novedad = (novedades / total_filas * 100) if total_filas > 0 else 0

        # Tarjetas de KPI Corporativas (Formato COP)
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='kpi-card'><div class='kpi-title'>Volumen de Registros</div><p class='kpi-value'>{total_filas:,}</p></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='kpi-card' style='border-left-color: #28a745;'><div class='kpi-title'>Capital Comprometido (COP)</div><p class='kpi-value' style='font-size:24px;'>$ {costo_total:,.0f}</p></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='kpi-card' style='border-left-color: #dc3545;'><div class='kpi-title'>Alertas / Novedades</div><p class='kpi-value'>{novedades:,}</p></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='kpi-card' style='border-left-color: #17a2b8;'><div class='kpi-title'>Índice de Fricción</div><p class='kpi-value'>{pct_novedad:.1f}%</p></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Gráficos Interactivos con Plotly
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("### 📊 Distribución de Capital por Entidad")
            if col_categoria and col_costo:
                df_agrupado = df_base.groupby(col_categoria[0])[col_costo[0]].sum().reset_index()
                fig1 = px.bar(df_agrupado, x=col_categoria[0], y=col_costo[0], text_auto='.2s', 
                              color=col_costo[0], color_continuous_scale='Blues')
                fig1.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.info("Faltan columnas de categoría o costo para graficar.")

        with col_b:
            st.markdown("### 🎯 Semáforo Operativo (Estatus)")
            if col_estatus:
                fig2 = px.pie(df_base, names=col_estatus[0], hole=0.4, color_discrete_sequence=px.colors.qualitative.Set1)
                fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Falta columna de Estatus.")

        st.markdown("### 🗄️ Bóveda de Datos (Detalle)")
        st.dataframe(df_base, use_container_width=True, hide_index=True)
    else:
        st.error("🚨 Sin datos disponibles. Sube un archivo en la barra lateral.")

# --- MÓDULO 2, 3 Y 4 SE MANTIENEN IGUAL ---
elif menu == "⚙️ 2. Motor de Costos (Smart Split)":
    st.markdown("<div class='titulo-principal'>Motor de Prorrateo Dinámico</div>", unsafe_allow_html=True)
    st.info("Sube una base de datos para activar simulaciones de overhead y costos ocultos.")

elif menu == "🛡️ 3. Auditoría en la Nube":
    st.markdown("<div class='titulo-principal'>Auditoría de Ineficiencias</div>", unsafe_allow_html=True)
    st.info("Módulo de escaneo activo. El sistema busca desviaciones estándar en los registros de entrega e inventario.")

elif menu == "📥 4. Ingesta y Limpieza Financiera":
    st.markdown("<div class='titulo-principal'>Motor de Limpieza Automática</div>", unsafe_allow_html=True)
    st.write("Sube una sábana de Excel desordenada y presiona el botón para sanitizar textos y estructurar valores.")
