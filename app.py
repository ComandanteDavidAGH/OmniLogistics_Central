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
    .titulo-principal { color: #ffffff; font-family: 'Arial Black', sans-serif; font-size: 26px; border-bottom: 3px solid #d4af37; padding-bottom: 10px; margin-bottom: 20px; text-transform: uppercase; }
    
    /* CSS RESTRUCTURADO PARA TARJETAS KPI IMPECABLES */
    .kpi-container {
        display: flex;
        flex-direction: column;
        justify-content: center;
        background-color: #1a1c23; 
        border-left: 5px solid #d4af37; 
        padding: 15px 18px; 
        border-radius: 8px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        min-height: 95px;
    }
    .kpi-title { 
        color: #a0aec0; 
        font-size: 11px; 
        text-transform: uppercase; 
        font-weight: 700; 
        letter-spacing: 0.5px;
        margin-bottom: 6px; 
    }
    .kpi-value-single { 
        color: #ffffff; 
        font-size: 21px; 
        font-weight: 900; 
        margin: 0; 
        white-space: nowrap; 
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .kpi-currency {
        font-size: 12px;
        color: #a0aec0;
        font-weight: 600;
        margin-left: 4px;
    }
</style>
""", unsafe_allow_html=True)

# --- MOTOR DE CARGA MULTI-ARCHIVO ---
def procesar_fuentes_datos(archivos_subidos, url_input):
    # 1. Prioridad: Carga Multi-Archivo del Cliente
    if archivos_subidos and len(archivos_subidos) > 0:
        lista_dfs = []
        for arch in archivos_subidos:
            try:
                df_temp = pd.read_csv(arch) if arch.name.endswith('.csv') else pd.read_excel(arch)
                df_temp['_Origen_Archivo'] = arch.name
                lista_dfs.append((arch.name, df_temp))
            except Exception:
                pass
        
        if lista_dfs:
            return lista_dfs, "Archivos Cliente"

    # 2. Prioridad: Google Sheets
    if url_input and url_input.strip() != "":
        try:
            match = re.search(r'/d/([a-zA-Z0-9-_]+)', url_input)
            if match:
                url_csv = f"https://docs.google.com/spreadsheets/d/{match.group(1)}/export?format=csv"
                df = pd.read_csv(url_csv)
                df['_Origen_Archivo'] = "Google_Sheets"
                return [("Google_Sheets", df)], "Nube Externa"
        except Exception:
            pass

    # 3. Prioridad: Demo Base Local
    try:
        df = pd.read_csv("datos_logistica_demo.csv")
        df['_Origen_Archivo'] = "datos_logistica_demo.csv"
        return [("datos_logistica_demo.csv", df)], "Demo Central"
    except Exception:
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
    st.markdown("**📥 Carga Multi-Archivo (Drag & Drop):**")
    archivos_cliente = st.file_uploader("Sube uno o varios archivos (CSV/Excel):", type=['csv', 'xlsx'], accept_multiple_files=True)
    url_input = st.text_input("🔗 Conectar Nube Externa:", placeholder="Pegar enlace...")

fuentes, tipo_origen = procesar_fuentes_datos(archivos_cliente, url_input)

# --- SELECTOR / CONSOLIDADOR MULTI-ARCHIVO ---
df_base = pd.DataFrame()
modo_multi = "Único"

if fuentes:
    if len(fuentes) > 1:
        st.sidebar.markdown("---")
        st.sidebar.markdown("**🗂️ Gestión Multi-Archivo:**")
        modo_multi = st.sidebar.radio("Modalidad de Procesamiento:", ["⚡ Consolidado (Todos los archivos)", "🔍 Seleccionar Archivo Único"])
        
        if modo_multi == "⚡ Consolidado (Todos los archivos)":
            df_base = pd.concat([item[1] for item in fuentes], ignore_index=True)
            fuente_activa = f"Consolidado Global ({len(fuentes)} archivos procesados simultáneamente)"
        else:
            opciones_archivos = [item[0] for item in fuentes]
            archivo_sel = st.sidebar.selectbox("Seleccionar reporte:", opciones_archivos)
            df_base = next(item[1] for item in fuentes if item[0] == archivo_sel)
            fuente_activa = f"Archivo: {archivo_sel}"
    else:
        df_base = fuentes[0][1]
        fuente_activa = fuentes[0][0]

# --- MÓDULO 1: COMMAND CENTER ---
if menu == "📊 1. Command Center (Dashboard)":
    st.markdown("<div class='titulo-principal'>Centro de Mando Operativo</div>", unsafe_allow_html=True)

    if not df_base.empty:
        st.success(f"✅ Sincronización exitosa. Origen de datos: **{fuente_activa}**")
        
        # Detección inteligente de columnas
        col_costo = [c for c in df_base.columns if any(p in c.lower() for p in ['costo', 'valor', 'monto', 'precio'])]
        col_estatus = [c for c in df_base.columns if any(p in c.lower() for p in ['estatus', 'estado', 'salud', 'condicion'])]
        col_categoria = [c for c in df_base.columns if any(p in c.lower() for p in ['transp', 'proveedor', 'categoria', 'bodega', 'origen'])]

        total_filas = len(df_base)
        costo_total = df_base[col_costo[0]].sum() if col_costo else 0
        
        if col_estatus:
            df_base[col_estatus[0]] = df_base[col_estatus[0]].astype(str)
            novedades = len(df_base[df_base[col_estatus[0]].str.lower().str.contains('retras|novedad|pendiente|quiebre|sobre')])
        else:
            novedades = 0
            
        pct_novedad = (novedades / total_filas * 100) if total_filas > 0 else 0

        # TARJETAS DE KPI CORREGIDAS (Alineación perfecta)
        c1, c2, c3, c4 = st.columns(4)
        
        c1.markdown(f"""
            <div class='kpi-container'>
                <div class='kpi-title'>Volumen de Registros</div>
                <p class='kpi-value-single'>{total_filas:,}</p>
            </div>
        """, unsafe_allow_html=True)
        
        c2.markdown(f"""
            <div class='kpi-container' style='border-left-color: #28a745;'>
                <div class='kpi-title'>Capital Comprometido</div>
                <p class='kpi-value-single'>${costo_total:,.0f}<span class='kpi-currency'>COP</span></p>
            </div>
        """, unsafe_allow_html=True)
        
        c3.markdown(f"""
            <div class='kpi-container' style='border-left-color: #dc3545;'>
                <div class='kpi-title'>Novedades / Alertas</div>
                <p class='kpi-value-single'>{novedades:,}</p>
            </div>
        """, unsafe_allow_html=True)
        
        c4.markdown(f"""
            <div class='kpi-container' style='border-left-color: #17a2b8;'>
                <div class='kpi-title'>Índice de Fricción</div>
                <p class='kpi-value-single'>{pct_novedad:.1f}%</p>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # Gráficos Interactivos Plotly
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.markdown("### 📊 Distribución Financiera")
            if col_categoria and col_costo:
                df_agrupado = df_base.groupby(col_categoria[0])[col_costo[0]].sum().reset_index()
                fig1 = px.bar(df_agrupado, x=col_categoria[0], y=col_costo[0], text_auto='.2s', 
                              color=col_costo[0], color_continuous_scale='Blues')
                fig1.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.info("Estructura de datos lista para visualización.")

        with col_b:
            st.markdown("### 🎯 Semáforo Operativo")
            if col_estatus:
                fig2 = px.pie(df_base, names=col_estatus[0], hole=0.4, color_discrete_sequence=px.colors.qualitative.Set1)
                fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Visualización de estatus disponible.")

        st.markdown("### 🗄️ Bóveda de Datos Conciliada")
        st.dataframe(df_base, use_container_width=True, hide_index=True)
    else:
        st.error("🚨 Sin datos disponibles. Sube tus archivos en la barra lateral.")

elif menu == "⚙️ 2. Motor de Costos (Smart Split)":
    st.markdown("<div class='titulo-principal'>Motor de Prorrateo Dinámico</div>", unsafe_allow_html=True)
    if not df_base.empty:
        overhead = st.slider("⚙️ Ajuste de Carga Administrativa (Overhead %):", min_value=0, max_value=50, value=15, step=1)
        df_split = df_base.copy()
        col_num = df_split.select_dtypes(include=['float64', 'int64']).columns
        if len(col_num) > 0:
            for col in col_num:
                df_split[f"{col}_Ajustado"] = df_split[col] * (1 + (overhead / 100))
            st.dataframe(df_split, use_container_width=True, hide_index=True)
            st.success(f"✅ Prorrateo recalculado sobre base activa con factor overhead del {overhead}%.")

elif menu == "🛡️ 3. Auditoría en la Nube":
    st.markdown("<div class='titulo-principal'>Auditoría de Ineficiencias</div>", unsafe_allow_html=True)
    st.info("Sistema de escaneo de desviaciones activado.")

elif menu == "📥 4. Ingesta y Limpieza Financiera":
    st.markdown("<div class='titulo-principal'>Motor de Limpieza Automática</div>", unsafe_allow_html=True)
    if not df_base.empty:
        if st.button("🚀 Ejecutar Limpieza y Sanitización"):
            with st.spinner("Procesando..."):
                time.sleep(1)
                df_limpio = df_base.copy()
                for col in df_limpio.select_dtypes(include=['object']).columns:
                    df_limpio[col] = df_limpio[col].astype(str).str.strip().str.upper()
                st.success(f"✅ {len(df_limpio):,} filas sanitizadas y consolidadas.")
                st.dataframe(df_limpio, use_container_width=True, hide_index=True)
