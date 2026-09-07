import streamlit as st
import pandas as pd
import plotly.express as px

def ejecutar(df_base, fuente_activa):
    # 💥 INYECCIÓN CSS: DISEÑO EJECUTIVO GÉNESIS
    st.markdown("""
    <style>
        /* Títulos y Jerarquía */
        .titulo-principal { color: #0d1b2a; font-family: 'Arial Black', sans-serif; font-size: 32px; border-bottom: 4px solid #d4af37; padding-bottom: 10px; margin-bottom: 25px; text-transform: uppercase; }
        .subtitulo-estrategico { color: #0d1b2a; font-size: 20px; font-weight: 900; border-bottom: 2px solid #d4af37; padding-bottom: 5px; margin-top: 15px; margin-bottom: 15px; text-transform: uppercase; }
        
        /* Endurecimiento de Selectores (Bordes y Fondos) */
        div[data-testid="stSelectbox"] > div[data-baseweb="select"] {
            border: 2px solid #0d1b2a !important;
            border-radius: 6px !important;
            background-color: #ffffff !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
        }
        div[data-testid="stSelectbox"] label p {
            font-weight: 800 !important;
            color: #0d1b2a !important;
            text-transform: uppercase !important;
            font-size: 12px !important;
        }
        
        /* Tarjetas KPI */
        .kpi-container { display: flex; flex-direction: column; justify-content: center; background-color: #0d1b2a; border-left: 5px solid #d4af37; padding: 15px 18px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); min-height: 95px; }
        .kpi-title { color: #d4af37; font-size: 11px; text-transform: uppercase; font-weight: 800; margin-bottom: 6px; letter-spacing: 0.5px; }
        .kpi-value-single { color: #ffffff; font-size: 22px; font-weight: 900; margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .kpi-currency { font-size: 12px; color: #a0aec0; font-weight: 600; margin-left: 4px; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='titulo-principal'>📊 Centro de Mando Operativo</div>", unsafe_allow_html=True)

    if df_base.empty:
        st.error("🚨 Sin datos disponibles. Sube tus archivos en la barra lateral.")
        return

    st.success(f"✅ Motor Analítico Activo | Origen: **{fuente_activa}**")
    
    st.markdown("<div class='subtitulo-estrategico'>⚙️ Configuración Dinámica (Mapeo)</div>", unsafe_allow_html=True)
    
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
    
    if col_fecha != "--- No Aplica ---":
        df_filtrado['__Fecha_Filtro'] = pd.to_datetime(df_filtrado[col_fecha], errors='coerce')
        fechas_validas = df_filtrado['__Fecha_Filtro'].dropna()
        
        if not fechas_validas.empty:
            fechas_unicas = sorted(fechas_validas.dt.date.unique())
            opciones_fechas = [f.strftime('%Y-%m-%d') for f in fechas_unicas]
            
            st.markdown("<div class='subtitulo-estrategico'>🗓️ Lupa Temporal (Rango)</div>", unsafe_allow_html=True)
            col_t1, col_t2 = st.columns(2)
            
            val_ini = col_t1.selectbox("⏳ Fecha Inicio Periodo:", opciones_fechas, index=0)
            val_fin = col_t2.selectbox("⏳ Fecha Corte Periodo:", opciones_fechas, index=len(opciones_fechas)-1)
            
            fecha_inicio = pd.to_datetime(val_ini).date()
            fecha_fin = pd.to_datetime(val_fin).date()
            
            mask = (df_filtrado['__Fecha_Filtro'].dt.date >= fecha_inicio) & (df_filtrado['__Fecha_Filtro'].dt.date <= fecha_fin)
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

    st.markdown("---")
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='kpi-container'><div class='kpi-title'>Volumen Registros</div><p class='kpi-value-single'>{total_filas:,}</p></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-container' style='border-left-color: #28a745;'><div class='kpi-title'>Capital Comprometido</div><p class='kpi-value-single'>${costo_total:,.0f}<span class='kpi-currency'>USD</span></p></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi-container' style='border-left-color: #dc3545;'><div class='kpi-title'>Alertas Operativas</div><p class='kpi-value-single'>{novedades:,}</p></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='kpi-container' style='border-left-color: #17a2b8;'><div class='kpi-title'>Índice de Fricción</div><p class='kpi-value-single'>{pct_novedad:.1f}%</p></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown("<div class='subtitulo-estrategico'>📊 Top 15 Categorías</div>", unsafe_allow_html=True)
        if col_cat != "--- No Aplica ---" and col_costo != "--- No Aplica ---" and total_filas > 0:
            df_agrupado = df_filtrado.groupby('__Cat_Limpia')['__Métrica_Limpia'].sum().reset_index()
            df_agrupado = df_agrupado.sort_values('__Métrica_Limpia', ascending=False).head(15)
            fig1 = px.bar(df_agrupado, x='__Cat_Limpia', y='__Métrica_Limpia', text_auto='.2s', color='__Métrica_Limpia', color_continuous_scale='Blues')
            fig1.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis_title=col_cat, yaxis_title="Monto")
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("💡 Despliega el selector de **Categoría** y **Métrica** arriba para activar.")

    with col_b:
        st.markdown("<div class='subtitulo-estrategico'>🎯 Estatus Operativo</div>", unsafe_allow_html=True)
        if col_estatus != "--- No Aplica ---" and total_filas > 0:
            df_pie = df_filtrado['__Estatus_Limpio'].value_counts().reset_index().head(10)
            df_pie.columns = ['__Estatus_Limpio', 'Conteo']
            fig2 = px.pie(df_pie, names='__Estatus_Limpio', values='Conteo', hole=0.4, color_discrete_sequence=px.colors.qualitative.Set1)
            fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("💡 Despliega el selector de **Estatus** arriba para ver el semáforo.")

    st.markdown("---")
    st.markdown("<div class='subtitulo-estrategico'>📈 Evolución Temporal</div>", unsafe_allow_html=True)
    if col_fecha != "--- No Aplica ---" and col_cat != "--- No Aplica ---" and col_costo != "--- No Aplica ---" and total_filas > 0:
        df_filtrado['__Fecha_Str'] = df_filtrado[col_fecha].astype(str).fillna("N/A")
        top_categorias = df_agrupado['__Cat_Limpia'].head(10).tolist() if 'df_agrupado' in locals() else []
        df_tendencia_base = df_filtrado[df_filtrado['__Cat_Limpia'].isin(top_categorias)]
        
        df_tendencia = df_tendencia_base.groupby(['__Fecha_Str', '__Cat_Limpia'])['__Métrica_Limpia'].sum().reset_index()
        df_tendencia = df_tendencia.sort_values(by='__Fecha_Str')
        
        fig3 = px.line(df_tendencia, x='__Fecha_Str', y='__Métrica_Limpia', color='__Cat_Limpia', markers=True)
        fig3.update_traces(line=dict(width=3)) 
        fig3.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", xaxis_title=col_fecha, yaxis_title=col_costo, legend_title=col_cat)
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("💡 Necesitas seleccionar **Categoría, Métrica y Eje Temporal** para trazar la tendencia.")

    st.markdown("---")
    st.markdown("<div class='subtitulo-estrategico'>🗄️ Bóveda de Datos Conciliada (Top 1000)</div>", unsafe_allow_html=True)
    cols_a_borrar = [c for c in ['__Métrica_Limpia', '__Cat_Limpia', '__Estatus_Limpio', '__Fecha_Str', '__Fecha_Filtro'] if c in df_filtrado.columns]
    df_mostrar = df_filtrado.drop(columns=cols_a_borrar, errors='ignore')
    st.dataframe(df_mostrar.head(1000), use_container_width=True, hide_index=True)
