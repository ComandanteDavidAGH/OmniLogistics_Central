import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go  # <-- NUEVO: Para gráficos futuristas avanzados
import google.generativeai as genai
import json

# --- MOTOR DE INTELIGENCIA DE CONTEXTO ---
@st.cache_data(show_spinner=False)
def generar_diagnostico_ia(df_sample_json, df_stats_json, columns_list):
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
        if not api_key:
            st.error("🚨 No se encontró la variable GEMINI_API_KEY en st.secrets.")
            return None

        genai.configure(api_key=api_key)
        modelo_a_usar = 'gemini-3.6-flash'

        prompt = f"""
        Eres el motor analítico de un sistema operativo logístico de alto nivel.
        Analiza los metadatos de esta matriz de datos:
        
        - Columnas presentes: {columns_list}
        - Muestra de filas: {df_sample_json}
        - Resumen estadístico: {df_stats_json}
        
        Genera un diagnóstico táctico y responde ÚNICAMENTE en formato JSON con la siguiente estructura:
        {{
            "titulo_contextual": "Título profesional basado en lo que representa la data",
            "resumen_gerencial": "Resumen ejecutivo en 2 oraciones identificando oportunidades financieras.",
            "cuellos_de_botella": ["Anomalía o riesgo crítico 1", "Anomalía o riesgo crítico 2"],
            "titulo_grafico_1": "Título gerencial para gráfico de costos vs categorías",
            "titulo_grafico_2": "Título gerencial para distribución de estatus"
        }}
        """
        
        model = genai.GenerativeModel(
            modelo_a_usar,
            generation_config={"response_mime_type": "application/json"}
        )
        response = model.generate_content(prompt)
        return json.loads(response.text)
        
    except Exception as e:
        st.error(f"🚨 Error de ejecución con la IA: {e}")
        return None


def ejecutar(df_base, fuente_activa):
    # 💥 INYECCIÓN CSS: DISEÑO FUTURISTA Y CORRECCIÓN DE COLORES
    st.markdown("""
    <style>
        /* Títulos corregidos a color oscuro para fondo claro */
        .titulo-principal { color: #0d1b2a; font-family: 'Arial Black', sans-serif; font-size: 32px; border-bottom: 4px solid #d4af37; padding-bottom: 10px; margin-bottom: 25px; text-transform: uppercase; }
        .subtitulo-estrategico { color: #0d1b2a; font-size: 16px; font-weight: 900; border-bottom: 2px solid #d4af37; padding-bottom: 5px; margin-top: 20px; margin-bottom: 15px; text-transform: uppercase; }
        
        /* Caja de Diagnóstico IA - Estilo Premium */
        .ia-card { background: linear-gradient(145deg, #111827, #1f2937); border-left: 6px solid #10b981; padding: 25px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); border-right: 1px solid #374151; border-top: 1px solid #374151; border-bottom: 1px solid #374151; }
        .ia-title { color: #10b981; font-size: 15px; font-weight: 900; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;}
        .ia-summary { color: #f3f4f6; font-size: 16px; font-weight: 400; line-height: 1.6; margin-bottom: 15px;}
        .ia-alert { color: #fb7185; font-size: 14px; font-weight: 700; margin-top: 8px; padding-left: 10px; border-left: 3px solid #fb7185;}

        /* Contenedores KPI - High Tech */
        .kpi-container { background: #0f172a; border-left: 5px solid #3b82f6; padding: 20px; border-radius: 10px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3); min-height: 100px; position: relative; overflow: hidden;}
        .kpi-title { color: #94a3b8; font-size: 11px; text-transform: uppercase; font-weight: 800; margin-bottom: 8px; letter-spacing: 1px; }
        .kpi-value-single { color: #ffffff; font-size: 26px; font-weight: 900; margin: 0; }
        .kpi-currency { font-size: 12px; color: #10b981; font-weight: 800; margin-left: 6px; }
    </style>
    """, unsafe_allow_html=True)

    if df_base.empty:
        st.error("🚨 Sin datos disponibles. Sube tus archivos.")
        return

    # --- ANÁLISIS AUTOMÁTICO DE IA ---
    sample_json = df_base.head(5).to_json(date_format='iso')
    stats_json = df_base.describe(include='all').fillna("").to_json()
    cols_list = list(df_base.columns)
    
    diagnostico = generar_diagnostico_ia(sample_json, stats_json, cols_list)

    # Título Adaptativo (Corregido color oscuro)
    titulo_header = diagnostico.get("titulo_contextual", "CENTRO DE MANDO OPERATIVO") if diagnostico else "CENTRO DE MANDO OPERATIVO"
    st.markdown(f"<div class='titulo-principal'>📊 {titulo_header}</div>", unsafe_allow_html=True)

    # Tarjeta de Resumen Gerencial IA
    if diagnostico:
        alerts_html = "".join([f"<div class='ia-alert'>⚠️ {alerta}</div>" for alerta in diagnostico.get("cuellos_de_botella", [])])
        st.markdown(f"""
        <div class='ia-card'>
            <div class='ia-title'>🧠 INTELIGENCIA ESTRATÉGICA ACTIVA</div>
            <div class='ia-summary'>{diagnostico.get('resumen_gerencial', '')}</div>
            <div style='margin-top: 15px;'>{alerts_html}</div>
        </div>
        """, unsafe_allow_html=True)

    # --- CONFIGURACIÓN DE COLUMNAS ---
    st.markdown("<div class='subtitulo-estrategico'>⚙️ Configuración del Motor de Datos</div>", unsafe_allow_html=True)
    
    col_costo_auto = [c for c in df_base.columns if any(p in c.lower() for p in ['costo', 'valor', 'monto', 'precio', 'fob', 'cif', 'total', 'usd'])]
    col_estatus_auto = [c for c in df_base.columns if any(p in c.lower() for p in ['estatus', 'estado', 'status', 'novedad', 'alerta', 'condicion', 'retraso', 'etapa'])]
    col_cat_auto = [c for c in df_base.columns if any(p in c.lower() for p in ['transp', 'proveedor', 'categoria', 'bodega', 'origen', 'destino', 'modo', 'tipo', 'via', 'puerto'])]
    col_fecha_auto = [c for c in df_base.columns if any(p in c.lower() for p in ['fecha', 'date', 'mes', 'año', 'year', 'periodo', 'creacion'])]

    opciones_columnas = ["--- No Aplica ---"] + list(df_base.columns)

    c_cfg1, c_cfg2, c_cfg3, c_cfg4 = st.columns(4)
    col_cat = c_cfg1.selectbox("Eje X (Categoría):", opciones_columnas, index=(df_base.columns.get_loc(col_cat_auto[0]) + 1) if col_cat_auto else 0)
    col_costo = c_cfg2.selectbox("Métrica Financiera:", opciones_columnas, index=(df_base.columns.get_loc(col_costo_auto[0]) + 1) if col_costo_auto else 0)
    col_estatus = c_cfg3.selectbox("Semáforo (Estatus):", opciones_columnas, index=(df_base.columns.get_loc(col_estatus_auto[0]) + 1) if col_estatus_auto else 0)
    col_fecha = c_cfg4.selectbox("Filtro Temporal:", opciones_columnas, index=(df_base.columns.get_loc(col_fecha_auto[0]) + 1) if col_fecha_auto else 0)

    df_filtrado = df_base.copy()
    
    if col_fecha != "--- No Aplica ---":
        df_filtrado['__Fecha_Filtro'] = pd.to_datetime(df_filtrado[col_fecha], errors='coerce')
        fechas_validas = df_filtrado['__Fecha_Filtro'].dropna()
        if not fechas_validas.empty:
            fechas_unicas = sorted(fechas_validas.dt.date.unique())
            opciones_fechas = [f.strftime('%Y-%m-%d') for f in fechas_unicas]
            
            c_f1, c_f2 = st.columns(2)
            val_ini = c_f1.selectbox("⏳ Inicio Rango:", opciones_fechas, index=0)
            val_fin = c_f2.selectbox("⏳ Fin Rango:", opciones_fechas, index=len(opciones_fechas)-1)
            
            mask = (df_filtrado['__Fecha_Filtro'].dt.date >= pd.to_datetime(val_ini).date()) & (df_filtrado['__Fecha_Filtro'].dt.date <= pd.to_datetime(val_fin).date())
            df_filtrado = df_filtrado.loc[mask]

    total_filas = len(df_filtrado)
    if col_costo != "--- No Aplica ---":
        df_filtrado['__Métrica_Limpia'] = pd.to_numeric(df_filtrado[col_costo].astype(str).str.replace(r'[^\d.-]', '', regex=True), errors='coerce').fillna(0)
        costo_total = df_filtrado['__Métrica_Limpia'].sum()
    else:
        df_filtrado['__Métrica_Limpia'] = 0
        costo_total = 0

    if col_cat != "--- No Aplica ---":
        df_filtrado['__Cat_Limpia'] = df_filtrado[col_cat].astype(str).fillna("N/A")
        
    if col_estatus != "--- No Aplica ---":
        df_filtrado['__Estatus_Limpio'] = df_filtrado[col_estatus].astype(str).fillna("N/A")
        novedades = len(df_filtrado[df_filtrado['__Estatus_Limpio'].str.lower().str.contains('retras|novedad|pendiente|quiebre|sobre|error|falla', na=False)])
    else:
        novedades = 0
        
    pct_novedad = (novedades / total_filas * 100) if total_filas > 0 else 0

    # TARJETAS KPI
    st.markdown("<br>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='kpi-container' style='border-left-color: #3b82f6;'><div class='kpi-title'>Registros Procesados</div><p class='kpi-value-single'>{total_filas:,}</p></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-container' style='border-left-color: #10b981;'><div class='kpi-title'>Capital Comprometido</div><p class='kpi-value-single'>${costo_total:,.0f}<span class='kpi-currency'>USD</span></p></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi-container' style='border-left-color: #f43f5e;'><div class='kpi-title'>Novedades Críticas</div><p class='kpi-value-single'>{novedades:,}</p></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='kpi-container' style='border-left-color: #8b5cf6;'><div class='kpi-title'>Fricción Operativa</div><p class='kpi-value-single'>{pct_novedad:.1f}%</p></div>", unsafe_allow_html=True)

    # VISUALIZACIÓN DE GRÁFICOS FUTURISTAS
    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    
    title_g1 = diagnostico.get("titulo_grafico_1", "COMPORTAMIENTO FINANCIERO X CATEGORÍA") if diagnostico else "COMPORTAMIENTO FINANCIERO"
    title_g2 = diagnostico.get("titulo_grafico_2", "MAPEO DE ESTATUS OPERATIVO") if diagnostico else "MAPEO DE ESTATUS"

    with col_a:
        st.markdown(f"<div class='subtitulo-estrategico'>📈 {title_g1}</div>", unsafe_allow_html=True)
        if col_cat != "--- No Aplica ---" and col_costo != "--- No Aplica ---" and total_filas > 0:
            df_agrupado = df_filtrado.groupby('__Cat_Limpia')['__Métrica_Limpia'].sum().reset_index()
            df_agrupado = df_agrupado.sort_values('__Métrica_Limpia', ascending=False).head(15)
            
            # Gráfico de Barras Oscuras + Línea de Tendencia Neón (Como en el video)
            fig1 = go.Figure()
            
            # Capa 1: Barras Oscuras
            fig1.add_trace(go.Bar(
                x=df_agrupado['__Cat_Limpia'], y=df_agrupado['__Métrica_Limpia'],
                marker_color='#1e293b', # Azul/Gris muy oscuro
                marker_line_color='#0ea5e9', # Borde Cyan neón
                marker_line_width=2,
                name='Volumen Real'
            ))
            
            # Capa 2: Línea de tendencia Neón Verde superpuesta
            fig1.add_trace(go.Scatter(
                x=df_agrupado['__Cat_Limpia'], y=df_agrupado['__Métrica_Limpia'],
                mode='lines+markers',
                line=dict(color='#10b981', width=4), # Verde Neón brillante
                marker=dict(color='#ffffff', size=8, line=dict(color='#10b981', width=3)),
                name='Trayectoria'
            ))
            
            # Fondo del gráfico futurista
            fig1.update_layout(
                plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
                font=dict(color="#94a3b8", family="Arial"),
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='#334155', gridwidth=1),
                margin=dict(l=10, r=10, t=20, b=10),
                showlegend=False
            )
            # NOTA: theme=None es vital para bloquear la pantalla blanca de Streamlit
            st.plotly_chart(fig1, use_container_width=True, theme=None)
            
    with col_b:
        st.markdown(f"<div class='subtitulo-estrategico'>🎯 {title_g2}</div>", unsafe_allow_html=True)
        if col_estatus != "--- No Aplica ---" and total_filas > 0:
            df_pie = df_filtrado['__Estatus_Limpio'].value_counts().reset_index().head(8)
            df_pie.columns = ['__Estatus_Limpio', 'Conteo']
            
            # Gráfico Donut estilo Cyber-Panel
            fig2 = px.pie(df_pie, names='__Estatus_Limpio', values='Conteo', hole=0.6,
                          color_discrete_sequence=['#0ea5e9', '#10b981', '#f43f5e', '#8b5cf6', '#eab308'])
            
            fig2.update_traces(textfont_size=14, textfont_color="#ffffff", marker=dict(line=dict(color='#0f172a', width=3)))
            fig2.update_layout(
                plot_bgcolor="#0f172a", paper_bgcolor="#0f172a",
                font=dict(color="#94a3b8"),
                margin=dict(l=10, r=10, t=20, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig2, use_container_width=True, theme=None)

    # TABLA DE DATOS
    st.markdown("---")
    st.markdown("<div class='subtitulo-estrategico'>🗄️ Bóveda de Datos Conciliada</div>", unsafe_allow_html=True)
    cols_a_borrar = [c for c in ['__Métrica_Limpia', '__Cat_Limpia', '__Estatus_Limpio', '__Fecha_Str', '__Fecha_Filtro'] if c in df_filtrado.columns]
    df_mostrar = df_filtrado.drop(columns=cols_a_borrar, errors='ignore')
    st.dataframe(df_mostrar.head(1000), use_container_width=True, hide_index=True)
