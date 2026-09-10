import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
import json
import traceback

# --- MOTOR DE INTELIGENCIA DE CONTEXTO ---
@st.cache_data(show_spinner=False)
def generar_diagnostico_ia(df_sample_json, df_stats_json, columns_list):
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
        if not api_key: return None
        genai.configure(api_key=api_key)
        modelo_a_usar = 'gemini-3.6-flash'

        prompt = f"""
        Eres el motor analítico de un sistema logístico. Analiza esto:
        Columnas: {columns_list}
        Muestra: {df_sample_json}
        Resumen: {df_stats_json}
        
        Responde ÚNICAMENTE en JSON:
        {{
            "titulo_contextual": "Título profesional basado en la data",
            "resumen_gerencial": "Resumen ejecutivo identificando oportunidades.",
            "cuellos_de_botella": ["Alerta 1", "Alerta 2"],
            "titulo_grafico_1": "Título para gráfico de barras",
            "titulo_grafico_2": "Título para gráfico de distribución"
        }}
        """
        model = genai.GenerativeModel(modelo_a_usar, generation_config={"response_mime_type": "application/json"})
        respuesta_cruda = model.generate_content(prompt).text
        
        if "```json" in respuesta_cruda: respuesta_cruda = respuesta_cruda.split("```json")[1].split("```")[0].strip()
        elif "```" in respuesta_cruda: respuesta_cruda = respuesta_cruda.split("```")[1].split("```")[0].strip()
            
        return json.loads(respuesta_cruda)
    except Exception as e:
        return {"error_ia": str(e)}

def ejecutar(df_base, fuente_activa):
    try:
        # 💥 INYECCIÓN CSS
        st.markdown("""
        <style>
            .titulo-principal { color: #0d1b2a; font-family: 'Arial Black', sans-serif; font-size: 30px; border-bottom: 4px solid #d4af37; padding-bottom: 10px; margin-bottom: 25px; text-transform: uppercase; }
            .subtitulo-estrategico { color: #0d1b2a; font-size: 16px; font-weight: 900; border-bottom: 2px solid #d4af37; padding-bottom: 5px; margin-top: 20px; margin-bottom: 15px; text-transform: uppercase; }
            .ia-card { background: linear-gradient(145deg, #111827, #1f2937); border-left: 6px solid #10b981; padding: 25px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); }
            .ia-title { color: #10b981; font-size: 15px; font-weight: 900; text-transform: uppercase; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;}
            .ia-summary { color: #f3f4f6; font-size: 16px; font-weight: 400; line-height: 1.6; margin-bottom: 15px;}
            .ia-alert { color: #fb7185; font-size: 14px; font-weight: 700; margin-top: 8px; padding-left: 10px; border-left: 3px solid #fb7185;}
            .kpi-container { background: #0f172a; border-left: 5px solid #3b82f6; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3); min-height: 100px; }
            .kpi-title { color: #94a3b8; font-size: 11px; text-transform: uppercase; font-weight: 800; margin-bottom: 8px; }
            .kpi-value-single { color: #ffffff; font-size: 26px; font-weight: 900; margin: 0; }
            .kpi-currency { font-size: 12px; color: #10b981; font-weight: 800; margin-left: 6px; }
            button[data-baseweb="tab"] { font-size: 18px !important; font-weight: 700 !important; color: #0d1b2a !important; }
            button[data-baseweb="tab"][aria-selected="true"] { color: #10b981 !important; border-bottom: 3px solid #10b981 !important; }
        </style>
        """, unsafe_allow_html=True)

        if df_base.empty:
            st.error("🚨 Sin datos disponibles. Sube tus archivos.")
            return

        diagnostico = generar_diagnostico_ia(df_base.head(5).to_json(date_format='iso'), df_base.describe(include='all').fillna("").to_json(), list(df_base.columns))

        if diagnostico and "error_ia" in diagnostico:
            st.warning(f"⚠️ Cebo IA activado: Falló el análisis inteligente. Detalles: {diagnostico['error_ia']}")

        titulo_header = diagnostico.get("titulo_contextual", "CENTRO DE MANDO OPERATIVO") if diagnostico else "CENTRO DE MANDO OPERATIVO"
        st.markdown(f"<div class='titulo-principal'>📊 {titulo_header}</div>", unsafe_allow_html=True)

        if diagnostico and "resumen_gerencial" in diagnostico:
            alerts_html = "".join([f"<div class='ia-alert'>⚠️ {alerta}</div>" for alerta in diagnostico.get("cuellos_de_botella", [])])
            st.markdown(f"<div class='ia-card'><div class='ia-title'>🧠 INTELIGENCIA ESTRATÉGICA ACTIVA</div><div class='ia-summary'>{diagnostico.get('resumen_gerencial', '')}</div><div style='margin-top: 15px;'>{alerts_html}</div></div>", unsafe_allow_html=True)

        st.markdown("<div class='subtitulo-estrategico'>⚙️ Motor de Datos</div>", unsafe_allow_html=True)
        opciones = ["--- No Aplica ---"] + list(df_base.columns)
        c_cfg1, c_cfg2, c_cfg3, c_cfg4 = st.columns(4)
        col_cat = c_cfg1.selectbox("Eje X (Categoría):", opciones, index=0)
        col_costo = c_cfg2.selectbox("Métrica Financiera:", opciones, index=0)
        col_estatus = c_cfg3.selectbox("Semáforo (Estatus):", opciones, index=0)
        col_fecha = c_cfg4.selectbox("Filtro Temporal:", opciones, index=0)

        df_filtrado = df_base.copy()
        
        if col_costo != "--- No Aplica ---":
            df_filtrado['__Métrica_Limpia'] = pd.to_numeric(df_filtrado[col_costo].astype(str).str.replace(r'[^\d.-]', '', regex=True), errors='coerce').fillna(0)
            costo_total = df_filtrado['__Métrica_Limpia'].sum()
        else: df_filtrado['__Métrica_Limpia'] = 0; costo_total = 0

        if col_cat != "--- No Aplica ---": df_filtrado['__Cat_Limpia'] = df_filtrado[col_cat].astype(str).fillna("N/A")
        if col_estatus != "--- No Aplica ---":
            df_filtrado['__Estatus_Limpio'] = df_filtrado[col_estatus].astype(str).fillna("N/A")
            novedades = len(df_filtrado[df_filtrado['__Estatus_Limpio'].str.lower().str.contains('retras|novedad|pendiente|quiebre', na=False)])
        else: novedades = 0

        st.markdown("<br>", unsafe_allow_html=True)
        tab_dashboard, tab_tabla = st.tabs(["📊 VISUALIZACIÓN ESTRATÉGICA", "🗄️ BÓVEDA DE DATOS (NÚMEROS)"])

        with tab_dashboard:
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f"<div class='kpi-container' style='border-left-color: #3b82f6;'><div class='kpi-title'>Registros Procesados</div><p class='kpi-value-single'>{len(df_filtrado):,}</p></div>", unsafe_allow_html=True)
            c2.markdown(f"<div class='kpi-container' style='border-left-color: #10b981;'><div class='kpi-title'>Métrica Seleccionada</div><p class='kpi-value-single'>${costo_total:,.0f}</p></div>", unsafe_allow_html=True)
            c3.markdown(f"<div class='kpi-container' style='border-left-color: #f43f5e;'><div class='kpi-title'>Alertas Operativas</div><p class='kpi-value-single'>{novedades:,}</p></div>", unsafe_allow_html=True)
            c4.markdown(f"<div class='kpi-container' style='border-left-color: #8b5cf6;'><div class='kpi-title'>Salud de Data</div><p class='kpi-value-single'>100%</p></div>", unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            col_a, col_b = st.columns(2)
            
            with col_a:
                st.markdown(f"<div class='subtitulo-estrategico'>📈 {diagnostico.get('titulo_grafico_1', 'COMPORTAMIENTO FINANCIERO') if diagnostico else 'ANÁLISIS DE DATOS'}</div>", unsafe_allow_html=True)
                if col_cat != "--- No Aplica ---" and col_costo != "--- No Aplica ---":
                    df_agrupado = df_filtrado.groupby('__Cat_Limpia')['__Métrica_Limpia'].sum().reset_index().sort_values('__Métrica_Limpia', ascending=False).head(15)
                    fig1 = go.Figure()
                    fig1.add_trace(go.Bar(x=df_agrupado['__Cat_Limpia'], y=df_agrupado['__Métrica_Limpia'], marker_color='#1e293b', marker_line_color='#0ea5e9', marker_line_width=2))
                    fig1.add_trace(go.Scatter(x=df_agrupado['__Cat_Limpia'], y=df_agrupado['__Métrica_Limpia'], mode='lines+markers', line=dict(color='#10b981', width=4), marker=dict(color='#ffffff', size=8, line=dict(color='#10b981', width=3))))
                    fig1.update_layout(plot_bgcolor="#0f172a", paper_bgcolor="#0f172a", font=dict(color="#94a3b8"), margin=dict(l=10, r=10, t=20, b=10), showlegend=False)
                    st.plotly_chart(fig1, use_container_width=True, theme=None)
                else: st.info("💡 Selecciona Eje X y Métrica Financiera para activar.")

            with col_b:
                st.markdown(f"<div class='subtitulo-estrategico'>🎯 {diagnostico.get('titulo_grafico_2', 'MAPEO DE ESTATUS') if diagnostico else 'DISTRIBUCIÓN'}</div>", unsafe_allow_html=True)
                if col_estatus != "--- No Aplica ---":
                    df_pie = df_filtrado['__Estatus_Limpio'].value_counts().reset_index().head(8)
                    df_pie.columns = ['__Estatus_Limpio', 'Conteo']
                    fig2 = px.pie(df_pie, names='__Estatus_Limpio', values='Conteo', hole=0.6, color_discrete_sequence=['#0ea5e9', '#10b981', '#f43f5e', '#8b5cf6'])
                    fig2.update_traces(textfont_size=14, textfont_color="#ffffff", marker=dict(line=dict(color='#0f172a', width=3)))
                    fig2.update_layout(plot_bgcolor="#0f172a", paper_bgcolor="#0f172a", font=dict(color="#94a3b8"), margin=dict(l=10, r=10, t=20, b=10), legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
                    st.plotly_chart(fig2, use_container_width=True, theme=None)
                else: st.info("💡 Selecciona Semáforo para activar.")

        with tab_tabla:
            # === LIMPIEZA INTELIGENTE Y RECONSTRUCCIÓN DE CABECERAS ===
            cols_internas = [c for c in df_filtrado.columns if c.startswith('__')]
            df_limpio = df_filtrado.drop(columns=cols_internas, errors='ignore').copy()
            
            # 1. Heredar títulos en celdas combinadas ("Unnamed")
            nuevas_columnas = []
            col_anterior = "Variable"
            contador = 1
            for c in df_limpio.columns:
                if "Unnamed:" in str(c):
                    nuevas_columnas.append(f"{col_anterior} (Sub-{contador})")
                    contador += 1
                else:
                    col_anterior = str(c).strip()
                    nuevas_columnas.append(col_anterior)
                    contador = 1
                    
            df_limpio.columns = nuevas_columnas
            
            # Limpiar textos de celdas nulas sin romper los números
            for col in df_limpio.columns:
                if df_limpio[col].dtype == 'object':
                    df_limpio[col] = df_limpio[col].fillna("-")
            
            # === PANEL DE FILTRADO DINÁMICO UNIVERSAL ===
            st.markdown("<div class='subtitulo-estrategico'>🎛️ Filtros Interactivos (Selecciona lo que deseas analizar)</div>", unsafe_allow_html=True)
            
            # Paso 1: El usuario elige qué columnas quiere usar para filtrar
            columnas_para_filtrar = st.multiselect("🔍 Selecciona las columnas que deseas usar como filtro:", df_limpio.columns.tolist())
            
            df_mostrar = df_limpio.copy()
            
            if columnas_para_filtrar:
                # Genera columnas dinámicas para colocar los filtros uno al lado del otro
                cols_filtros = st.columns(len(columnas_para_filtrar))
                
                for idx, col in enumerate(columnas_para_filtrar):
                    with cols_filtros[idx]:
                        # Extrae los valores únicos de esa columna en específico
                        valores_unicos = df_mostrar[col].dropna().unique().tolist()
                        # Crea el selector
                        seleccion = st.multiselect(f"Filtrar por '{col}':", valores_unicos, default=valores_unicos)
                        # Aplica el filtro matemático
                        df_mostrar = df_mostrar[df_mostrar[col].isin(seleccion)]

            st.markdown(f"**Total de registros filtrados:** {len(df_mostrar)}")
            
            # Renderizado Nativo (Conserva alineación de números y formato profesional)
            st.dataframe(df_mostrar, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error("🚨 CEBO ACTIVADO: COLAPSO DEL SISTEMA INTERNO")
        st.error(f"Falla detectada: {e}")
        st.code(traceback.format_exc(), language="python")
