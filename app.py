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

# --- MOTOR DE CARGA DINÁMICA DE DATOS ---
def cargar_base_datos(archivo_subido, url_input):
    # 1. Prioridad: Archivo subido directamente por el usuario (CSV o Excel)
    if archivo_subido is not None:
        try:
            if archivo_subido.name.endswith('.csv'):
                df = pd.read_csv(archivo_subido)
            else:
                df = pd.read_excel(archivo_subido)
            return df, f"Archivo Cargado ({archivo_subido.name})"
        except Exception as e:
            st.sidebar.error(f"Error al leer el archivo: {e}")

    # 2. Prioridad: URL de Google Sheets
    if url_input and url_input.strip() != "":
        try:
            match = re.search(r'/d/([a-zA-Z0-9-_]+)', url_input)
            if match:
                doc_id = match.group(1)
                url_csv = f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv"
                df = pd.read_csv(url_csv)
                return df, "Google Sheets Conectado"
        except Exception:
            pass

    # 3. Prioridad: Carga por defecto del archivo demo local
    try:
        df = pd.read_csv("datos_logistica_demo.csv")
        return df, "Demo Central (1,500 Registros)"
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
    
    st.markdown("**📥 Cargar Datos de Cliente:**")
    archivo_cliente = st.file_uploader("Sube tu CSV o Excel aquí:", type=['csv', 'xlsx'])
    url_input = st.text_input("🔗 O conecta Google Sheet:", placeholder="Pega URL aquí...")

# Cargar los datos dinámicamente según la selección del usuario
df_base, fuente = cargar_base_datos(archivo_cliente, url_input)

# --- MÓDULO 1: COMMAND CENTER ---
if menu == "📊 1. Command Center (Dashboard)":
    st.markdown("<div class='titulo-principal'>Centro de Mando Logístico</div>", unsafe_allow_html=True)

    if df_base is not None and not df_base.empty:
        st.success(f"✅ Fuente de datos activa: **{fuente}**")
        
        total_despachos = len(df_base)
        
        # Identificación flexible de columnas numéricas / operativas
        col_costo = [c for c in df_base.columns if 'costo' in c.lower() or 'valor' in c.lower() or 'monto' in c.lower()]
        costo_total = df_base[col_costo[0]].sum() if col_costo else 0

        col_estatus = [c for c in df_base.columns if 'estatus' in c.lower() or 'estado' in c.lower()]
        retrasados = len(df_base[df_base[col_estatus[0]].astype(str).str.lower().str.contains('retras|novedad|pendiente')]) if col_estatus else 0
        pct_retraso = (retrasados / total_despachos * 100) if total_despachos > 0 else 0

        # Tarjetas de KPI
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f"<div class='kpi-card'><div class='kpi-title'>Total Registros</div><p class='kpi-value'>{total_despachos:,}</p></div>", unsafe_allow_html=True)
        c2.markdown(f"<div class='kpi-card' style='border-left-color: #28a745;'><div class='kpi-title'>Costo / Valor Total</div><p class='kpi-value'>${costo_total:,.0f}</p></div>", unsafe_allow_html=True)
        c3.markdown(f"<div class='kpi-card' style='border-left-color: #dc3545;'><div class='kpi-title'>Incidencias / Retrasos</div><p class='kpi-value'>{retrasados}</p></div>", unsafe_allow_html=True)
        c4.markdown(f"<div class='kpi-card' style='border-left-color: #17a2b8;'><div class='kpi-title'>% Ineficiencia</div><p class='kpi-value'>{pct_retraso:.1f}%</p></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Gráficos dinámicos
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("### 🚚 Agrupación por Proveedor / Transportista")
            col_transp = [c for c in df_base.columns if 'transp' in c.lower() or 'proveedor' in c.lower()]
            if col_transp:
                st.bar_chart(df_base[col_transp[0]].value_counts())
            else:
                st.info("Sube un archivo con columna de 'Transportista' o 'Proveedor' para ver el gráfico.")

        with col_b:
            st.markdown("### 📍 Estado de las Operaciones")
            if col_estatus:
                st.bar_chart(df_base[col_estatus[0]].value_counts())
            else:
                st.info("Sube un archivo con columna de 'Estatus' o 'Estado' para ver el gráfico.")

        st.markdown("### 📦 Vista Previa de la Bóveda de Datos")
        st.dataframe(df_base, use_container_width=True, hide_index=True)
    else:
        st.error("🚨 Sin datos disponibles. Sube un archivo en la barra lateral.")

# --- MÓDULO 2: MOTOR DE COSTOS ---
elif menu == "⚙️ 2. Motor de Costos (Smart Split)":
    st.markdown("<div class='titulo-principal'>Motor de Prorrateo Dinámico</div>", unsafe_allow_html=True)
    
    if df_base is not None and not df_base.empty:
        st.write("Ajuste de carga operativa y simulación de overhead presupuestal.")
        
        overhead = st.slider("⚙️ Ajuste de Carga Administrativa (Overhead %):", min_value=0, max_value=50, value=15, step=1)
        
        df_split = df_base.copy()
        col_num = df_split.select_dtypes(include=['float64', 'int64']).columns
        
        if len(col_num) > 0:
            for col in col_num:
                df_split[f"{col}_Ajustado"] = df_split[col] * (1 + (overhead / 100))
            st.dataframe(df_split, use_container_width=True, hide_index=True)
            st.success(f"✅ Re-cálculo financiero completado con un overhead del {overhead}%.")
        else:
            st.warning("El archivo no contiene columnas numéricas para calcular prorrateos.")
    else:
        st.warning("Carga un archivo de datos para activar el motor de costos.")

# --- MÓDULO 3: AUDITORÍA ---
elif menu == "🛡️ 3. Auditoría en la Nube":
    st.markdown("<div class='titulo-principal'>Auditoría de Ineficiencias</div>", unsafe_allow_html=True)
    if df_base is not None and not df_base.empty:
        col_retraso = [c for c in df_base.columns if 'retras' in c.lower() or 'dias' in c.lower()]
        if col_retraso:
            df_anomalias = df_base[df_base[col_retraso[0]] > 0]
            st.warning(f"⚠️ Se detectaron {len(df_anomalias)} registros con demoras o novedades.")
            st.dataframe(df_anomalias, use_container_width=True, hide_index=True)
        else:
            st.info("Buscando anomalías... No se detectaron columnas de retraso explícitas en el archivo cargado.")
    else:
        st.info("Sin registros para auditar.")

# --- MÓDULO 4: INGESTA Y LIMPIEZA ---
elif menu == "📥 4. Ingesta y Limpieza Financiera":
    st.markdown("<div class='titulo-principal'>Motor de Limpieza Automática</div>", unsafe_allow_html=True)
    st.write("Procesa sábanas de datos crudas, elimina espacios en blanco y normaliza valores financieros al instante.")

    if df_base is not None and not df_base.empty:
        if st.button("🚀 Ejecutar Limpieza y Normalización en Vivo"):
            with st.spinner("Procesando y sanitizando datos..."):
                time.sleep(1)
                
                df_limpio = df_base.copy()
                # Limpieza de textos en todas las columnas tipo string
                for col in df_limpio.select_dtypes(include=['object']).columns:
                    df_limpio[col] = df_limpio[col].astype(str).str.strip().str.upper()
                
                st.success(f"✅ ¡Proceso completado! Se limpiaron y estandarizaron {len(df_limpio):,} filas exitosamente.")
                st.markdown("### ✨ Datos Sanitizados y Listos para Exportar")
                st.dataframe(df_limpio, use_container_width=True, hide_index=True)
