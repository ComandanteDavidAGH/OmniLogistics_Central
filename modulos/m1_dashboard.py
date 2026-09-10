import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
import json
import traceback

# ==============================================================================
# 1. MOTOR DE INTELIGENCIA (SAFE-MODE)
# ==============================================================================
@st.cache_data(show_spinner=False)
def generar_diagnostico_ia(df_sample_json, df_stats_json, columns_list):
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
        if not api_key: return None
        genai.configure(api_key=api_key)
        
        prompt = f"""
        Eres un motor analítico universal B2B. Analiza esta estructura de datos:
        Columnas: {columns_list}
        Muestra: {df_sample_json}
        Resumen: {df_stats_json}
        Responde ÚNICAMENTE en JSON con: "titulo_contextual", "resumen_gerencial", "cuellos_de_botella" (lista).
        """
        model = genai.GenerativeModel('gemini-3.6-flash', generation_config={"response_mime_type": "application/json"})
        respuesta = model.generate_content(prompt).text.strip()
        if "```json" in respuesta: respuesta = respuesta.split("```json")[1].split("```")[0].strip()
        return json.loads(respuesta)
    except Exception:
        return None  # Falla silenciosa y segura

# ==============================================================================
# 2. MOTOR DE INGESTA Y NORMALIZACIÓN PROFUNDA
# ==============================================================================
@st.cache_data(show_spinner=False)
def normalizar_datos(df_crudo):
    df = df_crudo.copy()
    
    # A. REPARACIÓN DE ENCABEZADOS (Celdas Combinadas y Duplicados)
    nuevas_cols = []
    col_anterior = "Variable"
    conteo_unnamed = 1
    vistos = {}
    
    for c in df.columns:
        c_str = str(c).strip()
        
        # Reparar Unnamed
        if "Unnamed:" in c_str:
            c_str = f"{col_anterior} (Sub-{conteo_unnamed})"
            conteo_unnamed += 1
        else:
            col_anterior = c_str
            conteo_unnamed = 1
            
        # Reparar Duplicados (Streamlit colapsa con columnas del mismo nombre)
        if c_str in vistos:
            vistos[c_str] += 1
            c_str = f"{c_str} ({vistos[c_str]})"
        else:
            vistos[c_str] = 0
            
        nuevas_cols.append(c_str)
    df.columns = nuevas_cols

    # B. LIMPIEZA DE BASURA TEXTUAL A NULOS REALES
    # Preservamos el 0. Destruimos los falsos vacíos.
    basura = ['None', 'nan', 'NaN', 'null', 'NULL', '#N/A', '-', '']
    df = df.replace(basura, np.nan)
    # Reemplazo de espacios en blanco usando regex
    df = df.replace(r'^\s+$', np.nan, regex=True)

    # C. INFERENCIA DE TIPOS (Rescate de Datos)
    for col in df.columns:
        # Si la columna es un objeto (texto)
        if df[col].dtype == 'object':
            serie_limpia = df[col].astype(str).str.strip()
            
            # 1. ¿Es una fecha?
            try:
                # Si tiene más de 4 caracteres y parece fecha
                if serie_limpia.str.match(r'^\d{2,4}[-/]\d{2}[-/]\d{2,4}$').any():
                    df[col] = pd.to_datetime(df[col], errors='ignore')
                    continue
            except: pass
            
            # 2. ¿Es un número atrapado en formato moneda o porcentaje?
            serie_num = serie_limpia.str.replace(r'[$\s]', '', regex=True).str.replace('%', '')
            # Manejo de comas y puntos (si hay coma y punto, asumimos formato US o LATAM)
            # Para universalidad agresiva, usamos pandas to_numeric con coerce
            serie_test = pd.to_numeric(serie_num.str.replace(',', ''), errors='coerce')
            
            # Si más del 50% de los datos no nulos se pudieron convertir a número, ES número
            no_nulos_orig = df[col].notna().sum()
            if no_nulos_orig > 0 and (serie_test.notna().sum() / no_nulos_orig) > 0.5:
                df[col] = serie_test
                
    return df

# ==============================================================================
# 3. CONSTRUCTOR VISUAL DE COLUMNAS (Formato sin destruir el valor)
# ==============================================================================
def construir_configuracion_columnas(df):
    config = {}
    for col in df.columns:
        dtype = df[col].dtype
        if pd.api.types.is_float_dtype(dtype):
            config[col] = st.column_config.NumberColumn(col, format="%.2f")
        elif pd.api.types.is_integer_dtype(dtype):
            config[col] = st.column_config.NumberColumn(col, format="%d")
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            config[col] = st.column_config.DateColumn(col, format="YYYY-MM-DD")
        else:
            config[col] = st.column_config.TextColumn(col)
    return config

# ==============================================================================
# 4. NÚCLEO DE RENDERIZADO
# ==============================================================================
def ejecutar(df_base, fuente_activa):
    try:
        # CSS EMPRESARIAL (Alta Densidad, Limpio, Sin bordes excesivos)
        st.markdown("""
        <style>
            .title-bar { color: #1e293b; font-family: 'Inter', sans-serif; font-size: 24px; font-weight: 800; border-bottom: 2px solid #e2e8f0; padding-bottom: 10px; margin-bottom: 20px; }
            .metric-card { background: #ffffff; border-left: 4px solid #3b82f6; padding: 15px; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; }
            .metric-title { color: #64748b; font-size: 11px; text-transform: uppercase; font-weight: 700; margin-bottom: 4px; letter-spacing: 0.5px;}
            .metric-value { color: #0f172a; font-size: 22px; font-weight: 800; margin: 0; }
            .ia-box { background: #f8fafc; border: 1px solid #e2e8f0; padding: 15px 20px; border-radius: 6px; margin-bottom: 20px; border-left: 4px solid #8b5cf6;}
            .ia-box strong { color: #4f46e5; font-size: 13px; text-transform: uppercase; }
            button[data-baseweb="tab"] { font-size: 14px !important; font-weight: 600 !important; }
        </style>
        """, unsafe_allow_html=True)

        if df_base.empty:
            st.info("💡 Bóveda vacía. Carga un dataset para iniciar la arquitectura de datos.")
            return

        # ---------------------------------------------------------
        # FASE 1: PROCESAMIENTO INVISIBLE
        # ---------------------------------------------------------
        df_norm = normalizar_datos(df_base)
        
        cols_num = df_norm.select_dtypes(include=[np.number]).columns.tolist()
        cols_cat = df_norm.select_dtypes(include=['object', 'category']).columns.tolist()
        cols_date = df_norm.select_dtypes(include=['datetime64']).columns.tolist()
        
        # Inteligencia Artificial en hilo separado (Cacheado)
        diagnostico = generar_diagnostico_ia(df_norm.head(3).to_json(date_format='iso'), df_norm.describe().to_json(), list(df_norm.columns))
        titulo = diagnostico.get("titulo_contextual", "ANÁLISIS DE DATOS UNIVERSAL") if diagnostico else "ANÁLISIS DE DATOS"

        # ---------------------------------------------------------
        # FASE 2: ENCABEZADO Y KPI GLOBALES
        # ---------------------------------------------------------
        st.markdown(f"<div class='title-bar'>💠 {titulo}</div>", unsafe_allow_html=True)

        if diagnostico:
            st.markdown(f"<div class='ia-box'><strong>🤖 Análisis IA:</strong> <span style='color:#334155;'>{diagnostico.get('resumen_gerencial', '')}</span></div>", unsafe_allow_html=True)

        # KPIs Automáticos (Detecta las primeras 4 columnas sumables)
        kpi_cols = st.columns(4)
        
        # KPI 1: Volumen
        with kpi_cols[0]:
            st.markdown(f"<div class='metric-card' style='border-color: #64748b;'><div class='metric-title'>Registros Totales</div><div class='metric-value'>{len(df_norm):,}</div></div>", unsafe_allow_html=True)
        
        # KPIs Numéricos 2, 3 y 4
        for i, col in enumerate(cols_num[:3]):
            val = df_norm[col].sum()
            formato = f"{val:,.2f}" if isinstance(val, float) else f"{val:,}"
            with kpi_cols[i+1]:
                st.markdown(f"<div class='metric-card'><div class='metric-title'>Suma de {col[:15]}</div><div class='metric-value'>{formato}</div></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # ---------------------------------------------------------
        # FASE 3: PANEL DE CONTROL Y TABS
        # ---------------------------------------------------------
        tab_datos, tab_dash = st.tabs(["🗄️ EXPLORADOR DE DATOS", "📊 DASHBOARD INTELIGENTE"])

        with tab_datos:
            # FILTROS DINÁMICOS ON-DEMAND (Cero saturación visual)
            st.markdown("**🔍 Filtros Inteligentes (Bajo Demanda)**")
            
            # El usuario elige qué quiere filtrar, en lugar de vomitar todos los filtros
            cols_para_filtrar = st.multiselect("Agregar filtro por columna:", df_norm.columns, placeholder="Selecciona columnas para segmentar...")
            
            df_filtrado = df_norm.copy()
            
            if cols_para_filtrar:
                # Contenedor gris sutil para los filtros activos
                with st.container(border=True):
                    filas_filtros = st.columns(len(cols_para_filtrar))
                    for i, col in enumerate(cols_para_filtrar):
                        with filas_filtros[i]:
                            # Si es numérico o fecha, slider. Si es texto, multiselect.
                            if col in cols_num:
                                min_v, max_v = float(df_norm[col].min()), float(df_norm[col].max())
                                if pd.isna(min_v) or pd.isna(max_v): continue
                                rango = st.slider(col, min_value=min_v, max_value=max_v, value=(min_v, max_v))
                                df_filtrado = df_filtrado[df_filtrado[col].between(rango[0], rango[1])]
                            else:
                                opciones = df_norm[col].dropna().unique()
                                seleccion = st.multiselect(col, sorted(opciones), placeholder="Seleccionar...")
                                if seleccion:
                                    df_filtrado = df_filtrado[df_filtrado[col].isin(seleccion)]

            # PANEL DE SALUD Y EXPORTACIÓN
            salud_pct = 100 - (df_filtrado.isna().sum().sum() / max(df_filtrado.size, 1)) * 100
            
            c_info, c_down = st.columns([4, 1])
            c_info.caption(f"Mostrando **{len(df_filtrado):,}** registros. | Salud de datos: **{salud_pct:.1f}%** completos.")
            with c_down:
                csv = df_filtrado.to_csv(index=False).encode('utf-8')
                st.download_button("📥 Exportar CSV", data=csv, file_name="exportacion_limpia.csv", mime="text/csv", use_container_width=True)

            # RENDERIZADOR UNIVERSAL WEBGL
            # Utilizamos st.dataframe nativo + column_config. 
            # Esto soporta 100.000 filas sin lag, ordena matemáticamente y deja nulos invisibles.
            config_columnas = construir_configuracion_columnas(df_filtrado)
            st.dataframe(
                df_filtrado,
                column_config=config_columnas,
                use_container_width=True,
                hide_index=True,
                height=500
            )

        with tab_dash:
            if not cols_num:
                st.warning("Se requieren columnas numéricas para generar analítica visual.")
            else:
                st.markdown("**📈 Analítica Automatizada**")
                
                # Selector de ejes compacto
                c_x, c_y = st.columns(2)
                
                # Inteligencia del Eje X: Priorizar fechas si existen, luego categorías.
                opciones_x = cols_date + cols_cat + cols_num
                
                eje_x = c_x.selectbox("Dimensión (Eje X):", opciones_x, index=0 if opciones_x else None)
                eje_y = c_y.selectbox("Métrica (Eje Y):", cols_num, index=0 if cols_num else None)

                if eje_x and eje_y:
                    # Agrupar datos (Top 30 para no saturar gráficos de barras)
                    df_graf = df_filtrado.groupby(eje_x)[eje_y].sum().reset_index()
                    
                    # Decisión automática de gráfico
                    if eje_x in cols_date:
                        # Gráfico temporal
                        df_graf = df_graf.sort_values(eje_x)
                        fig = px.line(df_graf, x=eje_x, y=eje_y, template="plotly_white", markers=True)
                        fig.update_traces(line_color='#10b981', line_width=3)
                    else:
                        # Gráfico categórico (Top 30)
                        df_graf = df_graf.sort_values(eje_y, ascending=False).head(30)
                        fig = px.bar(df_graf, x=eje_x, y=eje_y, template="plotly_white")
                        fig.update_traces(marker_color='#3b82f6')

                    fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), font=dict(family="Inter"))
                    st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error("🚨 COLAPSO DEL SISTEMA DETECTADO")
        st.error(f"Falla: {e}")
        st.code(traceback.format_exc(), language="python")
