import streamlit as st
import pandas as pd

def ejecutar(df_base):
    st.markdown("<div class='titulo-principal'>Motor de Prorrateo Dinámico</div>", unsafe_allow_html=True)
    
    st.markdown("""
    <style>
        .titulo-principal { color: #ffffff; font-family: 'Arial Black', sans-serif; font-size: 26px; border-bottom: 3px solid #d4af37; padding-bottom: 10px; margin-bottom: 20px; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

    if not df_base.empty:
        overhead = st.slider("⚙️ Ajuste de Carga Administrativa (Overhead %):", min_value=0, max_value=50, value=15, step=1)
        df_split = df_base.copy()
        
        # Detecta automáticamente columnas numéricas para aplicar el overhead
        col_num = df_split.select_dtypes(include=['float64', 'int64']).columns
        if len(col_num) > 0:
            for col in col_num:
                df_split[f"{col}_Ajustado"] = df_split[col] * (1 + (overhead / 100))
            
            st.success(f"✅ Prorrateo recalculado sobre base activa con factor overhead del {overhead}%.")
            st.dataframe(df_split, use_container_width=True, hide_index=True)
    else:
        st.error("🚨 Sin datos disponibles. Sube tus archivos en la barra lateral.")
