import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import json

# --- MOTOR DE INTELIGENCIA DE CONTEXTO ---
@st.cache_data(show_spinner=False)
def generar_diagnostico_ia(df_sample_json, df_stats_json, columns_list):
    """
    Envía metadatos anonimizados a la API para deducción semántica y diagnóstico gerencial.
    """
    try:
        # Configurar clave de API desde st.secrets o campo directo
        api_key = st.secrets.get("GEMINI_API_KEY", "")
        if not api_key:
            return None

        genai.configure(api_key=api_key)
        
        prompt = f"""
        Eres el motor analítico de un sistema operativo logístico de alto nivel.
        Analiza los metadatos de esta matriz de datos:
        
        - Columnas presentes: {columns_list}
        - Muestra de filas: {df_sample_json}
        - Resumen estadístico: {df_stats_json}
        
        Genera un diagnóstico táctico y responde ÚNICAMENTE en formato JSON con la siguiente estructura:
        {{
            "titulo_contextual": "Título profesional basado en lo que representa la data",
            "resumen_gerencial": "Resumen ejecutivo en 2 oraciones sobre el estado general.",
            "cuellos_de_botella": ["Anomalía o riesgo 1", "Anomalía o riesgo 2"],
            "titulo_grafico_1": "Título dinámico para el gráfico de categorías",
            "titulo_grafico_2": "Título dinámico para el semáforo operativo"
        }}
        """
        
        try:
    model = genai.GenerativeModel(
        'gemini-2.0-flash',
        generation_config={"response_mime_type": "application/json"}
    )
except Exception:
    model = genai.GenerativeModel(
        'gemini-1.5-pro',
        generation_config={"response_mime_type": "application/json"}
    )
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        st.error(f"🚨 Error de conexión con la IA: {e}")
        return None

def ejecutar(df_base, fuente_activa):
    # 💥 INYECCIÓN CSS: DISEÑO EJECUTIVO GÉNESIS
    st.markdown("""
    <style>
        .titulo-principal { color: #ffffff; font-family: 'Arial Black', sans-serif; font-size: 32px; border-bottom: 4px solid #d4af37; padding-bottom: 10px; margin-bottom: 25px; text-transform: uppercase; }
        .subtitulo-estrategico { color: #d4af37; font-size: 18px; font-weight: 900; border-bottom: 2px solid #d4af37; padding-bottom: 5px; margin-top: 20px; margin-bottom: 15px; text-transform: uppercase; }
        
        /* Caja de Diagnóstico IA */
        .ia-card { background-color: #1a1c23; border-left: 6px solid #d4af37; padding: 20px; border-radius: 8px; margin-bottom: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.4); }
        .ia-title { color: #d4af37; font-size: 14px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }
        .ia-summary { color: #e2e8f0; font-size: 15px; font-weight: 500; line-height: 1.5; }
        .ia-alert { color: #fc8181; font-size: 13px; font-weight: 700; margin-top: 5px; }

        /* Contenedores KPI */
        .kpi-container { display: flex; flex-direction: column; justify-content: center; background-color: #0d1b2a; border-left: 5px solid #d4af37; padding: 15px 18px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); min-height: 95px; }
        .kpi-title { color: #d4af37; font-size: 11px; text-transform: uppercase; font-weight: 800; margin-bottom: 6px; letter-spacing: 0.5px; }
        .kpi-value-single { color: #ffffff; font-size: 22px; font-weight: 900; margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .kpi-currency { font-size: 12px; color: #a0aec0; font-weight: 600; margin-left: 4px; }
    </style>
    """, unsafe_allow_html=True)

    if df_base.empty:
        st.error("🚨 Sin datos disponibles. Sube tus archivos en la barra lateral.")
        return

    # --- ANÁLISIS AUTOMÁTICO DE IA ---
    sample_json = df_base.head(3).to_json(date_format='iso')
    stats_json = df_base.describe(include='all').fillna("").to_json()
    cols_list = list(df_base.columns)
    
    diagnostico = generar_diagnostico_ia(sample_json, stats_json, cols_list)

    # Título Adaptativo
    titulo_header = diagnostico.get("titulo_contextual", "CENTRO DE MANDO OPERATIVO") if diagnostico else "CENTRO DE MANDO OPERATIVO"
    st.markdown(f"<div class='titulo-principal'>📊 {titulo_header}</div>", unsafe_allow_html=True)
    st.success(f"✅ Motor Analítico Activo | Origen: **{fuente_activa}**")

    # Tarjeta de Resumen Gerencial IA
    if diagnostico:
        alerts_html = "".join([f"<li class='ia-alert'>⚠️ {alerta}</li>" for alerta in diagnostico.get("cuellos_de_botella", [])])
        st.markdown(f"""
        <div class='ia-card'>
            <div class='ia-title'>🤖 DIAGNÓSTICO TÁCTICO AUTOMÁTICO (GÉNESIS IA)</div>
            <div class='ia-summary'>{diagnostico.get('resumen_gerencial', '')}</div>
            <ul style='margin-bottom: 0; padding-left: 20px;'>{alerts_html}</ul>
        </div>
        """, unsafe_allow_html=True)

    # --- CONFIGURACIÓN DE COLUMNAS (MAPEO AUTOMÁTICO) ---
    st.markdown("<div class='subtitulo-estrategico'>⚙️ Mapeo Dinámico de Variables</div>", unsafe_allow_html=True)
    
    col_costo_auto = [c for c in df_base.columns if any(p in c.lower() for p in ['costo', 'valor', 'monto', 'precio', 'fob', 'cif', 'total', 'usd'])]
    col_estatus_auto = [c for c in df_base.columns if any(p in c.lower() for p in ['estatus', 'estado', 'status', 'novedad', 'alerta', 'condicion', 'retraso', 'etapa'])]
    col_cat_auto = [c for c in df_base.columns if any(p in c.lower() for p in ['transp', 'proveedor', 'categoria', 'bodega', 'origen', 'destino', 'modo', 'tipo', 'via', 'puerto'])]
    col_fecha_auto = [c for c in df_base.columns if any(p in c.lower() for p in ['fecha', 'date', 'mes', 'año', 'year', 'periodo', 'creacion'])]

    opciones_columnas = ["--- No Aplica ---"] + list(df_base.columns)

    c_cfg1, c_cfg2, c_cfg3, c_cfg4 = st.columns(4)
    col_cat = c_cfg1.selectbox("📊 Categoría (Eje X/Color):", opciones_columnas, index=(df_base.columns.get_loc(col_cat_auto[0]) + 1) if col_cat_auto else 0)
    col_costo = c_cfg2.selectbox("💰 Métrica (Dinero):", opciones_columnas, index=(df_base.columns.get_loc(col_costo_auto[0]) + 1) if col_costo_auto else 0)
    col_estatus = c_cfg3.selectbox("🚦 Estatus (Semáforo):", opciones_columnas, index=(df_base.columns.get_loc(col_estatus_auto[0]) + 1) if col_estatus_auto else 0)
    col_fecha = c_cfg4.selectbox("📅 Eje Temporal:", opciones_columnas, index=(df_base.columns.get_loc(col_fecha_auto[0]) + 1) if col_fecha_auto else 0)

    df_filtrado = df_base.copy()
    
    # Filtro Temporal
    if col_fecha != "--- No Aplica ---":
        df_filtrado['__Fecha_Filtro'] = pd.to_datetime(df_filtrado[col_fecha], errors='coerce')
        fechas_validas = df_filtrado['__Fecha_Filtro'].dropna()
        
        if not fechas_validas.empty:
            fechas_unicas = sorted(fechas_validas.dt.date.unique())
            opciones_fechas = [f.strftime('%Y-%m-%d') for f in fechas_unicas]
            
            st.markdown("<div class='subtitulo-estrategico'>🗓️ Lupa Temporal</div>", unsafe_allow_html=True)
            col_t1, col_t2 = st.columns(2)
            val_ini = col_t1.selectbox("⏳ Fecha Inicio:", opciones_fechas, index=0)
            val_fin = col_t2.selectbox("⏳ Fecha Corte:", opciones_fechas, index=len(opciones_fechas)-1)
            
            mask = (df_filtrado['__Fecha_Filtro'].dt.date >= pd.to_datetime(val_ini).date()) & (df_filtrado['__Fecha_Filtro'].dt.date <= pd.to_datetime(val_fin).date())
            df_filtrado = df_filtrado.loc[mask]

    # Métrica de Limpieza de Costos
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

    # TARJETAS DE MÉTRICAS
    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='kpi-container'><div class='kpi-title'>Volumen Registros</div><p class='kpi-value-single'>{total_filas:,}</p></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-container' style='border-left-color: #28a745;'><div class='kpi-title'>Capital Comprometido</div><p class='kpi-value-single'>${costo_total:,.0f}<span class='kpi-currency'>USD</span></p></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi-container' style='border-left-color: #dc3545;'><div class='kpi-title'>Alertas Operativas</div><p class='kpi-value-single'>{novedades:,}</p></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='kpi-container' style='border-left-color: #17a2b8;'><div class='kpi-title'>Índice de Fricción</div><p class='kpi-value-single'>{pct_novedad:.1f}%</p></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # VISUALIZACIÓN DE GRÁFICOS
    col_a, col_b = st.columns(2)
    
    # Nombres dinámicos de gráficos
    title_g1 = diagnostico.get("titulo_grafico_1", "Top Categorías") if diagnostico else "Top Categorías"
    title_g2 = diagnostico.get("titulo_grafico_2", "Estatus Operativo") if diagnostico else "Estatus Operativo"

    with col_a:
        st.markdown(f"<div class='subtitulo-estrategico'>📊 {title_g1}</div>", unsafe_allow_html=True)
        if col_cat != "--- No Aplica ---" and col_costo != "--- No Aplica ---" and total_filas > 0:
            df_agrupado = df_filtrado.groupby('__Cat_Limpia')['__Métrica_Limpia'].sum().reset_index()
            df_agrupado = df_agrupado.sort_values('__Métrica_Limpia', ascending=False).head(15)
            fig1 = px.bar(df_agrupado, x='__Cat_Limpia', y='__Métrica_Limpia', text_auto='.2s', color='__Métrica_Limpia', color_continuous_scale='Blues')
            fig1.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis_title=col_cat, yaxis_title="Monto", template="plotly_dark")
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("💡 Mapea Categoría y Métrica arriba para activar el gráfico.")

    with col_b:
        st.markdown(f"<div class='subtitulo-estrategico'>🎯 {title_g2}</div>", unsafe_allow_html=True)
        if col_estatus != "--- No Aplica ---" and total_filas > 0:
            df_pie = df_filtrado['__Estatus_Limpio'].value_counts().reset_index().head(10)
            df_pie.columns = ['__Estatus_Limpio', 'Conteo']
            fig2 = px.pie(df_pie, names='__Estatus_Limpio', values='Conteo', hole=0.4, color_discrete_sequence=px.colors.qualitative.Set1)
            fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", template="plotly_dark")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("💡 Mapea Estatus arriba para ver la distribución.")

    # TABLA DE DATOS CONCILIADA
    st.markdown("---")
    st.markdown("<div class='subtitulo-estrategico'>🗄️ Bóveda de Datos Conciliada</div>", unsafe_allow_html=True)
    cols_a_borrar = [c for c in ['__Métrica_Limpia', '__Cat_Limpia', '__Estatus_Limpio', '__Fecha_Str', '__Fecha_Filtro'] if c in df_filtrado.columns]
    df_mostrar = df_filtrado.drop(columns=cols_a_borrar, errors='ignore')
    st.dataframe(df_mostrar.head(1000), use_container_width=True, hide_index=True)
