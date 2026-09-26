import streamlit as st
import pandas as pd


def ejecutar(df_base):
    st.markdown("<div class='titulo-principal'>Motor de Fórmulas y Ajustes %</div>", unsafe_allow_html=True)

    st.markdown("""
    <style>
        .titulo-principal { color: #ffffff; font-family: 'Arial Black', sans-serif; font-size: 26px; border-bottom: 3px solid #d4af37; padding-bottom: 10px; margin-bottom: 20px; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

    if df_base is None or df_base.empty:
        st.error("🚨 Sin datos disponibles. Sube tus archivos en la barra lateral.")
        return

    st.caption("Aplica un ajuste porcentual a una o varias columnas numéricas: IVA, comisión, propina, "
               "descuento, recargo por servicio, costo administrativo, etc.")

    etiqueta_ajuste = st.text_input("🏷️ Nombre del ajuste (ej: IVA, Comisión, Propina, Descuento):", value="Ajuste")
    col_a, col_b = st.columns([2, 1])
    signo = col_b.radio("Tipo:", ["➕ Sumar", "➖ Restar"], horizontal=True)
    porcentaje = col_a.slider(f"⚙️ Porcentaje de '{etiqueta_ajuste}' (%):", min_value=0, max_value=100, value=15, step=1)

    df_split = df_base.copy()
    col_num = df_split.select_dtypes(include=['float64', 'int64']).columns.tolist()

    if not col_num:
        st.warning("⚠️ No se detectaron columnas numéricas en la base actual. Ve primero al Dashboard para limpiar los datos.")
        return

    columnas_sel = st.multiselect("💰 Columnas a las que aplicar el ajuste:", options=col_num, default=col_num[:1])

    if columnas_sel:
        factor = (1 + (porcentaje / 100)) if "Sumar" in signo else (1 - (porcentaje / 100))
        for col in columnas_sel:
            df_split[f"{col} · {etiqueta_ajuste} ({porcentaje}%)"] = df_split[col] * factor

        st.success(f"✅ Ajuste '{etiqueta_ajuste}' del {porcentaje}% aplicado sobre {len(columnas_sel)} columna(s).")
        cols_mostrar = columnas_sel + [c for c in df_split.columns if etiqueta_ajuste in c]
        st.dataframe(df_split[cols_mostrar], use_container_width=True, hide_index=True)

        total_original = df_split[columnas_sel].sum().sum()
        total_ajustado = df_split[[c for c in df_split.columns if etiqueta_ajuste in c]].sum().sum()
        k1, k2 = st.columns(2)
        k1.metric("Total original", f"{total_original:,.2f}")
        k2.metric(f"Total con '{etiqueta_ajuste}'", f"{total_ajustado:,.2f}", delta=f"{total_ajustado - total_original:,.2f}")
    else:
        st.info("Selecciona al menos una columna numérica para calcular el ajuste.")
