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
        elif "```" in respuesta: respuesta = respuesta.split("```")[1].split("```")[0].strip()
        return json.loads(respuesta)
    except Exception:
        return None

# ==============================================================================
# 2. MOTOR UNIVERSAL DE RECONSTRUCCIÓN DE TABLAS (Data Interpreter)
# ==============================================================================
@st.cache_data(show_spinner=False)
def reconstruir_tabla_empresarial(df_crudo):
    df = df_crudo.copy()
    
    # A. PURGA INICIAL DE BASURA TEXTUAL
    basura = ['None', 'none', 'nan', 'NaN', 'null', 'NULL', '#N/A', '-', '']
    df = df.replace(to_replace=basura, value=np.nan)
    df = df.replace(r'^\s+$', np.nan, regex=True)
    
    # B. ELIMINACIÓN DE VACÍOS ABSOLUTOS
    df = df.dropna(how='all', axis=0).dropna(how='all', axis=1).reset_index(drop=True)
    if df.empty: return df
    
    # C. CAZADOR DE ENCABEZADOS (Detecta dónde empiezan los datos reales)
    # Heurística: La primera columna clave rara vez es nula en los datos, pero suele serlo en los títulos.
    try:
        primera_col = df.columns[0]
        idx_inicio_datos = df[df[primera_col].notna()].index[0]
    except:
        idx_inicio_datos = 0
        
    # D. FUSIÓN DE CELDAS COMBINADAS Y SUBTÍTULOS (Reconstrucción)
    if 0 < idx_inicio_datos < 10: 
        df_headers = df.iloc[:idx_inicio_datos].copy()
        df_headers = df_headers.ffill(axis=1) # Rellena hacia la derecha las celdas combinadas de Excel
        
        nuevos_nombres = []
        for col_idx, col_name in enumerate(df.columns):
            partes = []
            if "Unnamed" not in str(col_name):
                partes.append(str(col_name).strip())
                
            for fila_idx in range(idx_inicio_datos):
                val = df_headers.iloc[fila_idx, col_idx]
                if pd.notna(val):
                    # Evitar que años en encabezados tengan .0 (Ej: 2025.0 -> 2025)
                    if isinstance(val, float) and val.is_integer():
                        val_str = str(int(val))
                    else:
                        val_str = str(val).strip()
                        
                    if val_str and (not partes or partes[-1] != val_str):
                        partes.append(val_str)
                        
            nuevo_nombre = " | ".join(partes) if partes else f"Columna {col_idx+1}"
            nuevos_nombres.append(nuevo_nombre)
            
        df.columns = nuevos_nombres
        df = df.drop(index=range(idx_inicio_datos)).reset_index(drop=True)
        
    # E. DESDUPLICACIÓN INTELIGENTE DE COLUMNAS
    s = pd.Series(df.columns)
    df.columns = s.where(~s.duplicated(), s + ' (' + s.groupby(s).cumcount().astype(str) + ')')
    
    # F. RESCATE MATEMÁTICO (Inferencia agresiva de tipos numéricos)
    for col in df.columns:
        if df[col].dtype == 'object':
            serie_str = df[col].astype(str)
            # Limpiar comas, signos de $ y espacios para forzar números
            serie_num = pd.to_numeric(serie_str.str.replace(r'[$\s,]', '', regex=True), errors='coerce')
            nulos_orig = df[col].isna().sum()
            # Si el 40% de los datos se salvaron como número, convertir toda la columna
            if len(df) > nulos_orig and serie_num.notna().sum() > ((len(df) - nulos_orig) * 0.4):
                df[col] = serie_num
                
    return df

# ==============================================================================
# 3. FORMATEADOR VISUAL COLOMBIANO
# ==============================================================================
def renderizador_colombiano(val):
    if pd.isna(val) or val == 'None' or val == 'nan':
        return "" # Celdas verdaderamente invisibles
    if isinstance(val, (int, float)):
        if pd.isna(val): return ""
        if val % 1 == 0:
            return f"{int(val):,}".replace(",", ".")
        else:
            parts = f"{val:,.2f}".split(".")
            return f"{parts[0].replace(',', '.')},{parts[1]}"
    return str(val)

# ==============================================================================
# 4. NÚCLEO DE LA APLICACIÓN BI
# ==============================================================================
def ejecutar(df_base, fuente_activa):
    try:
        # INYECCIÓN CSS EMPRESARIAL
        st.markdown("""
        <style>
            .title-bar { color: #0f172a; font-family: 'Inter', sans-serif; font-size: 26px; font-weight: 900; border-bottom: 2px solid #cbd5e1; padding-bottom: 12px; margin-bottom: 25px; text-transform: uppercase; }
            .ia-box { background: #f8fafc; border: 1px solid #e2e8f0; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 5px solid #6366f1;}
            .ia-box strong { color: #4f46e5; font-size: 14px; text-transform: uppercase; }
            button[data-baseweb="tab"] { font-size: 16px !important; font-weight: 700 !important; color: #64748b !important; }
            button[data-baseweb="tab"][aria-selected="true"] { color: #0f172a !important; border-bottom: 3px solid #3b82f6 !important; }
            .kpi-card { background: #ffffff; padding: 15px; border-radius: 8px; border: 1px solid #e2e8f0; border-left: 4px solid #10b981; box-shadow: 0 2px 4px rgba(0,0,0,0.02);}
            .kpi-title { font-size: 11px; color: #64748b; font-weight: 800; text-transform: uppercase;}
            .kpi-val { font-size: 22px; color: #0f172a; font-weight: 900; font-family: 'Consolas', monospace;}
        </style>
        """, unsafe_allow_html=True)

        if df_base.empty:
            st.info("💡 Bóveda de datos vacía. Inyecta un archivo en la barra lateral.")
            return

        # ---------------------------------------------------------
        # FASE 1: RECONSTRUCCIÓN (MAGIA B2B)
        # ---------------------------------------------------------
        with st.spinner("Reconstruyendo arquitectura de tabla..."):
            df_norm = reconstruir_tabla_empresarial(df_base)
            
        cols_num = df_norm.select_dtypes(include=[np.number]).columns.tolist()
        cols_cat = df_norm.select_dtypes(include=['object', 'category']).columns.tolist()

        diagnostico = generar_diagnostico_ia(df_norm.head(3).to_json(date_format='iso'), df_norm.describe().to_json(), list(df_norm.columns))
        titulo = diagnostico.get("titulo_contextual", "MOTOR B2B UNIVERSAL") if diagnostico else "MOTOR B2B UNIVERSAL"

        st.markdown(f"<div class='title-bar'>💠 {titulo}</div>", unsafe_allow_html=True)
        if diagnostico:
            st.markdown(f"<div class='ia-box'><strong>🤖 Análisis Estratégico (IA):</strong> <span style='color:#334155; font-size: 15px;'>{diagnostico.get('resumen_gerencial', '')}</span></div>", unsafe_allow_html=True)

        # ---------------------------------------------------------
        # FASE 2: PESTAÑAS EJECUTIVAS
        # ---------------------------------------------------------
        tab_tabla, tab_dash = st.tabs(["🗄️ BÓVEDA NORMALIZADA", "📊 VISUALIZACIÓN ANALÍTICA"])

        with tab_tabla:
            st.markdown("### 🎛️ Filtros bajo Demanda")
            st.caption("Selecciona solo las columnas que deseas filtrar para no saturar la pantalla.")
            
            # FILTROS COMPACTOS Y DINÁMICOS
            cols_filtro = st.multiselect("Agregar filtro:", df_norm.columns.tolist())
            df_filtrado = df_norm.copy()
            
            if cols_filtro:
                with st.container(border=True):
                    grid = st.columns(min(len(cols_filtro), 4))
                    for i, col in enumerate(cols_filtro):
                        with grid[i % 4]:
                            if col in cols_num:
                                min_v, max_v = float(df_norm[col].min()), float(df_norm[col].max())
                                if not pd.isna(min_v) and not pd.isna(max_v) and min_v != max_v:
                                    rango = st.slider(col, min_value=min_v, max_value=max_v, value=(min_v, max_v))
                                    df_filtrado = df_filtrado[df_filtrado[col].between(rango[0], rango[1])]
                            else:
                                ops = sorted([str(x) for x in df_norm[col].dropna().unique()])
                                sel = st.multiselect(col, ops, placeholder="Elegir...")
                                if sel:
                                    df_filtrado = df_filtrado[df_filtrado[col].astype(str).isin(sel)]

            # PAGINACIÓN (Evita el colapso de RAM y permite ocultar Nulls perfectamente)
            st.markdown("---")
            col_p1, col_p2, col_p3 = st.columns([1, 1, 2])
            with col_p1:
                regs_pagina = st.selectbox("Registros por página:", [25, 50, 100, 500])
            
            total_filas = len(df_filtrado)
            total_pags = max(1, (total_filas + regs_pagina - 1) // regs_pagina)
            
            with col_p2:
                pag_actual = st.number_input("Página:", min_value=1, max_value=total_pags, value=1)
                
            with col_p3:
                st.markdown(f"<div style='margin-top: 32px; font-weight: 800; color: #0f172a;'>Total de registros: {total_filas:,}</div>", unsafe_allow_html=True)

            # RENDERIZADO VISUAL PERFECTO
            inicio = (pag_actual - 1) * regs_pagina
            fin = inicio + regs_pagina
            df_mostrar = df_filtrado.iloc[inicio:fin]
            
            st.dataframe(
                df_mostrar.style.format(renderizador_colombiano),
                use_container_width=True,
                hide_index=True
            )

        with tab_dash:
            if not cols_num:
                st.warning("Se requieren métricas numéricas para generar analítica.")
            else:
                st.markdown("### 📈 Cuadro de Mando")
                
                # KPIs Dinámicos Automáticos
                kpis = st.columns(4)
                for i, col in enumerate(cols_num[:4]):
                    val = df_filtrado[col].sum()
                    formato = f"{val:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".") if isinstance(val, float) else f"{int(val):,}".replace(",", ".")
                    with kpis[i]:
                        st.markdown(f"<div class='kpi-card'><div class='kpi-title'>{col[:20]}</div><div class='kpi-val'>{formato}</div></div>", unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Gráficos Universales
                c_x, c_y = st.columns(2)
                eje_x = c_x.selectbox("Eje X (Categoría):", df_filtrado.columns.tolist())
                eje_y = c_y.selectbox("Eje Y (Métrica):", cols_num)
                
                if eje_x and eje_y:
                    df_graf = df_filtrado.groupby(eje_x)[eje_y].sum().reset_index().sort_values(eje_y, ascending=False).head(20)
                    fig = px.bar(df_graf, x=eje_x, y=eje_y, template="plotly_white")
                    fig.update_traces(marker_color='#3b82f6', marker_line_color='#1e293b', marker_line_width=1)
                    st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error("🚨 COLAPSO DEL SISTEMA DETECTADO")
        st.error(f"Falla crítica: {str(e)}")
        st.code(traceback.format_exc(), language="python")
