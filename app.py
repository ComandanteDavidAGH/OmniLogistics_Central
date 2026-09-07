import streamlit as st
import pandas as pd
import time
import re
import plotly.express as px

# --- CONFIGURACIÓN CORPORATIVA (Bloqueo de menú nativo) ---
st.set_page_config(
    page_title="OmniLogistics OS | Demo", 
    page_icon="🌐", 
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

st.markdown("""
<style>
    /* 🎯 CIRUGÍA DE PRECISIÓN: Neutralizar Gato y mantener Hamburguesa */
    [data-testid="stToolbarActions"], .stAppDeployButton, .viewerBadge_container, div[class^="viewerBadge"], footer { 
        display: none !important; 
    }
    #MainMenu { 
        visibility: visible !important; 
        display: block !important; 
    }
    header { 
        background-color: transparent !important; 
    }

    /* DISEÑO CORPORATIVO Y KPI */
    .main { background-color: #0e1117; }
    .titulo-principal { color: #ffffff; font-family: 'Arial Black', sans-serif; font-size: 26px; border-bottom: 3px solid #d4af37; padding-bottom: 10px; margin-bottom: 20px; text-transform: uppercase; }
    
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
    st.markdown("<div class='titulo-principal'>Auditoría de Calidad y Desviaciones</div>", unsafe_allow_html=True)
    if not df_base.empty:
        st.info("🔍 Escaneando la matriz en busca de ineficiencias ocultas, errores de tipeo y duplicados...")
        
        # 1. Búsqueda de Duplicados
        duplicados = df_base[df_base.duplicated(keep=False)]
        
        # 2. Análisis de Texto (Espacios, Casos Mixtos)
        cols_texto = df_base.select_dtypes(include=['object']).columns
        lista_espacios = []
        lista_casos = []
        
        for col in cols_texto:
            # Detectar espacios al inicio o final
            mask_espacios = df_base[col].astype(str).str.contains(r'^\s+|\s+$', regex=True, na=False)
            if mask_espacios.any():
                temp_df = df_base[mask_espacios].copy()
                temp_df['Problema_Detectado'] = f"Espacios fantasma en columna: {col}"
                lista_espacios.append(temp_df)
                
            # Detectar inconsistencias de mayúsculas/minúsculas (CamelCase o mixto)
            mask_casos = df_base[col].astype(str).apply(lambda x: not (str(x).isupper() or str(x).islower() or str(x).istitle()) if pd.notna(x) and str(x).strip() != "" else False)
            if mask_casos.any():
                temp_df2 = df_base[mask_casos].copy()
                temp_df2['Problema_Detectado'] = f"Formato inconsistente (Mayús/Minús) en: {col}"
                lista_casos.append(temp_df2)

        df_espacios = pd.concat(lista_espacios) if lista_espacios else pd.DataFrame()
        df_casos = pd.concat(lista_casos) if lista_casos else pd.DataFrame()

        t1, t2, t3 = st.tabs([f"👯 Duplicados Exactos ({len(duplicados)})", f"👻 Espacios Ocultos ({len(df_espacios)})", f"🔤 Formato Inconsistente ({len(df_casos)})"])
        
        with t1:
            if not duplicados.empty:
                st.error("Se encontraron registros exactamente iguales que inflan los costos.")
                st.dataframe(duplicados, use_container_width=True)
            else: st.success("Cero duplicados detectados.")
            
        with t2:
            if not df_espacios.empty:
                st.warning("Estos registros fallarán en cruces de bases de datos (Ej: 'BOGOTA ' vs 'BOGOTA').")
                st.dataframe(df_espacios, use_container_width=True)
            else: st.success("Sin espacios residuales.")
            
        with t3:
            if not df_casos.empty:
                st.warning("Nombres escritos sin estandarización. Afecta la agrupación de costos.")
                st.dataframe(df_casos, use_container_width=True)
            else: st.success("Textos estandarizados.")
    else:
        st.warning("Carga una base de datos primero.")

elif menu == "📥 4. Ingesta y Limpieza Financiera":
    st.markdown("<div class='titulo-principal'>Motor de Limpieza Automática</div>", unsafe_allow_html=True)
    if not df_base.empty:
        st.info("Este motor erradica los problemas encontrados en la auditoría con un solo clic, preparando la data para SAP.")
        if st.button("🚀 Ejecutar Limpieza Estructural (Sanitización)", type="primary"):
            with st.spinner("Destruyendo espacios, unificando formatos y purgando duplicados..."):
                time.sleep(1.5)
                df_limpio = df_base.copy()
                
                # 1. Eliminar duplicados
                filas_antes = len(df_limpio)
                df_limpio = df_limpio.drop_duplicates()
                duplicados_borrados = filas_antes - len(df_limpio)
                
                # 2. Limpieza de texto profunda
                cols_texto = df_limpio.select_dtypes(include=['object']).columns
                for col in cols_texto:
                    df_limpio[col] = df_limpio[col].astype(str).str.strip().str.upper()
                    # Eliminar dobles espacios intermedios
                    df_limpio[col] = df_limpio[col].apply(lambda x: re.sub(r'\s+', ' ', x))
                
                st.success(f"✅ Matriz Sanitizada. Se eliminaron {duplicados_borrados} duplicados y se estandarizaron {len(cols_texto)} columnas de texto.")
                st.dataframe(df_limpio, use_container_width=True, hide_index=True)
