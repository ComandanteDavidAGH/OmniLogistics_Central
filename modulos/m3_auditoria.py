import streamlit as st
import pandas as pd

def ejecutar(df_base):
    st.markdown("<div class='titulo-principal'>Auditoría de Calidad y Desviaciones</div>", unsafe_allow_html=True)
    
    st.markdown("""
    <style>
        .titulo-principal { color: #ffffff; font-family: 'Arial Black', sans-serif; font-size: 26px; border-bottom: 3px solid #d4af37; padding-bottom: 10px; margin-bottom: 20px; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

    if not df_base.empty:
        st.info("🔍 Escaneando la matriz en busca de ineficiencias ocultas, errores de tipeo y duplicados...")
        
        # 1. Búsqueda de Duplicados
        duplicados = df_base[df_base.duplicated(keep=False)]
        
        # 2. Análisis de Texto (Espacios, Casos Mixtos)
        cols_texto = df_base.select_dtypes(include=['object']).columns
        lista_espacios = []
        lista_casos = []
        
        for col in cols_texto:
            # Detectar espacios al inicio o final
            mask_espacios = df_base[col].astype(str).str.contains(r'^\s+|\s+$', regex=True, na=False)
            if mask_espacios.any():
                temp_df = df_base[mask_espacios].copy()
                temp_df['Problema_Detectado'] = f"Espacios fantasma en: {col}"
                lista_espacios.append(temp_df)
                
            # Detectar inconsistencias de mayúsculas/minúsculas
            mask_casos = df_base[col].astype(str).apply(lambda x: not (str(x).isupper() or str(x).islower() or str(x).istitle()) if pd.notna(x) and str(x).strip() != "" else False)
            if mask_casos.any():
                temp_df2 = df_base[mask_casos].copy()
                temp_df2['Problema_Detectado'] = f"Formato mixto en: {col}"
                lista_casos.append(temp_df2)

        df_espacios = pd.concat(lista_espacios) if lista_espacios else pd.DataFrame()
        df_casos = pd.concat(lista_casos) if lista_casos else pd.DataFrame()

        t1, t2, t3 = st.tabs([f"👯 Duplicados Exactos ({len(duplicados)})", f"👻 Espacios Ocultos ({len(df_espacios)})", f"🔤 Formato Inconsistente ({len(df_casos)})"])
        
        with t1:
            if not duplicados.empty:
                st.error("Se encontraron registros exactamente iguales que inflan los costos logísticos.")
                st.dataframe(duplicados, use_container_width=True)
            else: st.success("Cero duplicados detectados.")
            
        with t2:
            if not df_espacios.empty:
                st.warning("Estos registros fallarán en cruces de bases de datos de SAP (Ej: 'BOGOTA ' vs 'BOGOTA').")
                st.dataframe(df_espacios, use_container_width=True)
            else: st.success("Sin espacios residuales.")
            
        with t3:
            if not df_casos.empty:
                st.warning("Nombres escritos sin estandarización. Afecta la agrupación de costos y reportes financieros.")
                st.dataframe(df_casos, use_container_width=True)
            else: st.success("Textos estandarizados.")
    else:
        st.error("🚨 Carga una base de datos primero en la barra lateral.")
