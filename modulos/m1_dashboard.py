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

    st.success(f"✅ Procesamiento Ultra-Rápido: Origen **{fuente_activa}**")
    
    st.markdown("**⚙️ Configuración Dinámica de Gráficos (Mapeo en vivo)**")
    
    col_costo_auto = [c for c in df_base.columns if any(p in c.lower() for p in ['costo', 'valor', 'monto', 'precio', 'fob', 'cif', 'total', 'usd'])]
    col_estatus_auto = [c for c in df_base.columns if any(p in c.lower() for p in ['estatus', 'estado', 'status', 'novedad', 'alerta', 'condicion', 'retraso', 'etapa'])]
    col_cat_auto = [c for c in df_base.columns if any(p in c.lower() for p in ['transp', 'proveedor', 'categoria', 'bodega', 'origen', 'destino', 'modo', 'tipo', 'via', 'puerto'])]

    c_cfg1, c_cfg2, c_cfg3 = st.columns(3)
    
    col_cat = c_cfg1.selectbox("📊 Eje X (Agrupación/Categoría):", df_base.columns, index=df_base.columns.get_loc(col_cat_auto[0]) if col_cat_auto else 0)
    col_costo = c_cfg2.selectbox("💰 Métrica (Dinero/Volumen):", df_base.columns, index=df_base.columns.get_loc(col_costo_auto[0]) if col_costo_auto else 0)
    col_estatus = c_cfg3.selectbox("🚦 Columna de Estatus (Semáforo):", df_base.columns, index=df_base.columns.get_loc(col_estatus_auto[0]) if col_estatus_auto else 0)

    total_filas = len(df_base)
    
    df_base['Costo_Limpio'] = pd.to_numeric(df_base[col_costo].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
    costo_total = df_base['Costo_Limpio'].sum()
    
    df_base[col_estatus] = df_base[col_estatus].astype(str)
    novedades = len(df_base[df_base[col_estatus].str.lower().str.contains('retras|novedad|pendiente|quiebre|sobre|error|falla', na=False)])
        
    pct_novedad = (novedades / total_filas * 100) if total_filas > 0 else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='kpi-container'><div class='kpi-title'>Volumen de Registros</div><p class='kpi-value-single'>{total_filas:,}</p></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi-container' style='border-left-color: #28a745;'><div class='kpi-title'>Capital Comprometido</div><p class='kpi-value-single'>${costo_total:,.0f}<span class='kpi-currency'>COP/USD</span></p></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi-container' style='border-left-color: #dc3545;'><div class='kpi-title'>Novedades / Alertas</div><p class='kpi-value-single'>{novedades:,}</p></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='kpi-container' style='border-left-color: #17a2b8;'><div class='kpi-title'>Índice de Fricción</div><p class='kpi-value-single'>{pct_novedad:.1f}%</p></div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.markdown(f"### 📊 Distribución por {col_cat}")
        df_agrupado = df_base.groupby(col_cat)['Costo_Limpio'].sum().reset_index()
        fig1 = px.bar(df_agrupado, x=col_cat, y='Costo_Limpio', text_auto='.2s', color='Costo_Limpio', color_continuous_scale='Blues')
        fig1.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
        st.plotly_chart(fig1, use_container_width=True)

    with col_b:
        st.markdown(f"### 🎯 Semáforo Operativo ({col_estatus})")
        df_pie = df_base[col_estatus].value_counts().reset_index().head(10)
        df_pie.columns = [col_estatus, 'Conteo']
        fig2 = px.pie(df_pie, names=col_estatus, values='Conteo', hole=0.4, color_discrete_sequence=px.colors.qualitative.Set1)
        fig2.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### 🗄️ Bóveda de Datos Conciliada")
    st.dataframe(df_base, use_container_width=True, hide_index=True)
