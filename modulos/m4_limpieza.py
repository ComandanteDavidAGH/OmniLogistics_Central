import streamlit as st
import pandas as pd
import time
import re

def ejecutar(df_base):
    st.markdown("<div class='titulo-principal'>Motor de Limpieza Automática</div>", unsafe_allow_html=True)
    
    st.markdown("""
    <style>
        .titulo-principal { color: #ffffff; font-family: 'Arial Black', sans-serif; font-size: 26px; border-bottom: 3px solid #d4af37; padding-bottom: 10px; margin-bottom: 20px; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

    if not df_base.empty:
        st.info("Este motor erradica los problemas encontrados en la auditoría con un solo clic, preparando la data para inyección directa al ERP.")
        
        if st.button("🚀 Ejecutar Limpieza Estructural (Sanitización)", type="primary"):
            with st.spinner("Destruyendo espacios, unificando formatos y purgando duplicados..."):
                time.sleep(1.5)
                df_limpio = df_base.copy()
                
                # 1. Eliminar duplicados
                filas_antes = len(df_limpio)
                df_limpio = df_limpio.drop_duplicates()
                duplicados_borrados = filas_antes - len(df_limpio)
                
                # 2. Limpieza de texto profunda
                cols_texto = df_limpio.select_dtypes(include=['object']).columns
                for col in cols_texto:
                    df_limpio[col] = df_limpio[col].astype(str).str.strip().str.upper()
                    # Eliminar dobles espacios intermedios (ej: "LOS    ANGELES" -> "LOS ANGELES")
                    df_limpio[col] = df_limpio[col].apply(lambda x: re.sub(r'\s+', ' ', x))
                
                st.success(f"✅ Matriz Sanitizada. Se eliminaron {duplicados_borrados} duplicados y se estandarizaron {len(cols_texto)} columnas de texto al formato universal.")
                st.dataframe(df_limpio, use_container_width=True, hide_index=True)
    else:
        st.error("🚨 Carga una base de datos primero en la barra lateral.")
