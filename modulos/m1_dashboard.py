import streamlit as st
import pandas as pd
import plotly.express as px

def ejecutar(df_base, fuente_activa):
    st.markdown("""
    <style>
        .titulo-principal { color: #ffffff; font-family: 'Arial Black', sans-serif; font-size: 26px; border-bottom: 3px solid #d4af37; padding-bottom: 10px; margin-bottom: 20px; text-transform: uppercase; }
        .kpi-container { display: flex; flex-direction: column; justify-content: center; background-color: #1a1c23; border-left: 5px solid #d4af37; padding: 15px 18px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); min-height: 95px; }
        .kpi-title { color: #a0aec0; font-size: 11px; text-transform: uppercase; font-weight: 700; margin-bottom: 6px; }
        .kpi-value-single { color: #ffffff; font-size: 21px; font-weight: 900; margin: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .kpi-currency { font-size: 12px; color: #a0aec0; font-weight: 600; margin-left: 4px; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='titulo-principal'>Centro de Mando Operativo</div>", unsafe_allow_html=True)

    if df_base.empty:
        st.error("🚨 Sin datos disponibles. Sube tus archivos en la barra lateral.")
        return

    st.success(f"✅ Procesamiento Turbo Activado: Origen **{fuente_activa}**")
    
    st.markdown("**⚙️ Configuración Dinámica de Gráficos (Mapeo en vivo)**")
    
    col_costo_auto = [c for c in df_base.columns if any(p in c.lower() for p in ['costo', 'valor', 'monto', 'precio', 'fob', 'cif', 'total', 'usd'])]
    col_estatus_auto = [c for c in df_base.columns if any(p in c.lower() for p in ['estatus', 'estado', 'status', 'novedad', 'alerta', 'condicion', 'retraso', 'etapa'])]
    col_cat_auto = [c for c in df_base.columns if any(p in c.lower() for p in ['transp', 'proveedor', 'categoria', 'bodega', 'origen', 'destino', 'modo', 'tipo', 'via', 'puerto'])]
    col_fecha_auto = [c for c in df_base.columns if any(p in c.lower() for p in ['fecha', 'date', 'mes', 'año', 'year', 'periodo', 'creacion'])]

    # 💥 INYECCIÓN: Opción global para apagar variables
    opciones_columnas = ["--- No Aplica ---"] + list(df_base.columns)

    c_cfg1, c_cfg2, c_cfg3, c_cfg4 = st.columns(4)
    
    col_cat = c_cfg1.selectbox("📊 Categoría (Eje X/Color):", opciones_columnas, index=(df_base.columns.get_loc(col_cat_auto[0]) + 1) if col_cat_auto else 0)
    col_costo = c_cfg2.selectbox("💰 Métrica (Dinero):", opciones_columnas, index=(df_base.columns.get_loc(col_costo_auto[0]) + 1) if col_costo_auto else 0)
    col_estatus = c_cfg3.selectbox("🚦 Estatus (Semáforo):", opciones_columnas, index=(df_base.columns.get_loc(col_estatus_auto[0]) + 1) if col_estatus_auto else 0)
    col_fecha = c_cfg4.selectbox("📅 Eje Temporal:", opciones_columnas, index=(df_base.columns.get_loc(col_fecha_auto[0]) + 1) if col_fecha_auto else 0)

    # --- MOTOR TURBO: SANITIZACIÓN RÁPIDA DE TIPOS CON FILTRO "NO APLICA" ---
    total_filas = len(df_base)
    
    if col_costo != "--- No Aplica ---":
        df_base['__Métrica_Limpia'] = pd.to_numeric(df_base[col_costo].astype(str).str.replace(r'[^\d.-]', '', regex=True), errors='coerce').fillna(0)
        costo_total = df_base['__Métrica_Limpia'].sum()
    else:
        df_base['__Métrica_Limpia'] = 0
        costo_total = 0

    if col_cat != "--- No Aplica ---":
        df_base['__Cat_Limpia'] = df_base[col_cat].astype(str).fillna("N/A")
        
    if col_estatus != "--- No Aplica ---":
        df_base['__Estatus_Limpio'] = df_base[col_estatus].astype(str).fillna("N/A")
        novedades = len(df_base[df_base['__Estatus_Limpio'].str.lower().str.contains('retras|novedad|pendiente|quiebre|sobre|error|falla', na=False)])
    else:
        novedades = 0
        
    pct_novedad = (novedades / total_filas * 100) if total_filas > 0 else 0

    # --- TARJETAS DE KPI ---
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='kpi-container'><div class='kpi-title'>Volumen de Registros</div><p class='kpi-value-single'>{total_filas:,}</p></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-container' style='border-left-color: #28a745;'><div class='kpi-title'>Capital Comprometido</div><p class='kpi-value-single'>${costo_total:,.0f}<span class='kpi-currency'>COP/USD</span></p></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi-container' style='border-left-color: #dc3545;'><div class='kpi-title'>Novedades / Alertas</div><p class='kpi-value-single'>{novedades:,}</p></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='kpi-container' style='border-left-color: #17a2b8;'><div class='kpi-title'>Índice de Fricción</div><p class='kpi-value-single'>{pct_novedad:.1f}%</p></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # --- FILA 1: BARRAS Y SEMÁFORO ---
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown("### 📊 Top 15 por Categoría")
        if col_cat != "--- No Aplica ---" and col_costo != "--- No Aplica ---":
            df_agrupado = df_base.groupby('__Cat_Limpia')['__Métrica_Limpia'].sum().reset_index()
            df_agrupado = df_agrupado.sort_values('__Métrica_Limpia', ascending=False).head(15)
            fig1 = px.bar(df_agrupado, x='__Cat_Limpia', y='__Métrica_Limpia', text_auto='.2s', color='__Métrica_Limpia', color_continuous_scale='Blues')
            fig1.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"), xaxis_title=col_cat, yaxis_title="Monto")
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("💡 Despliega el selector de **Categoría** y **Métrica** arriba para activar este gráfico.")

    with col_b:
        st.markdown("### 🎯 Estatus Operativo")
        if col_estatus != "--- No Aplica ---":
            df_pie = df_base['__Estatus_Limpio'].value_counts().reset_index().head(10)
            df_pie.columns = ['__Estatus_Limpio', 'Conteo']
            fig2 = px.pie(df_pie, names='__Estatus_Limpio', values='Conteo', hole=0.4, color_discrete_sequence=px.colors.qualitative.Set1)
            fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("💡 Despliega el selector de **Estatus** arriba para ver el semáforo de novedades.")

    # --- FILA 2: TENDENCIA TEMPORAL MULTILÍNEA ---
    st.markdown("---")
    st.markdown("### 📈 Evolución Temporal")
    if col_fecha != "--- No Aplica ---" and col_cat != "--- No Aplica ---" and col_costo != "--- No Aplica ---":
        df_base['__Fecha_Limpia'] = df_base[col_fecha].astype(str).fillna("N/A")
        top_categorias = df_agrupado['__Cat_Limpia'].head(10).tolist()
        df_tendencia_base = df_base[df_base['__Cat_Limpia'].isin(top_categorias)]
        
        df_tendencia = df_tendencia_base.groupby(['__Fecha_Limpia', '__Cat_Limpia'])['__Métrica_Limpia'].sum().reset_index()
        df_tendencia = df_tendencia.sort_values(by='__Fecha_Limpia')
        
        fig3 = px.line(df_tendencia, x='__Fecha_Limpia', y='__Métrica_Limpia', color='__Cat_Limpia', markers=True)
        fig3.update_traces(line=dict(width=3)) 
        fig3.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"),
            xaxis_title=col_fecha, yaxis_title=col_costo, legend_title=col_cat
        )
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("💡 Necesitas seleccionar **Categoría, Métrica y Eje Temporal** para trazar la tendencia.")

    st.markdown("---")
    st.markdown("### 🗄️ Bóveda de Datos Conciliada (Muestra Top 1000)")
    cols_a_borrar = [c for c in ['__Métrica_Limpia', '__Cat_Limpia', '__Estatus_Limpio', '__Fecha_Limpia'] if c in df_base.columns]
    df_mostrar = df_base.drop(columns=cols_a_borrar)
    st.dataframe(df_mostrar.head(1000), use_container_width=True, hide_index=True)
