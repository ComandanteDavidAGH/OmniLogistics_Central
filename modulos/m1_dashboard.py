"""
MOTOR RASTREADOR DE DIAGNÓSTICO (MODO DEBUG B2B)
================================================
Este código no genera el dashboard final. 
Coloca trampas visuales para depurar la topografía del Excel.
"""
import pandas as pd
import numpy as np
import streamlit as st

def ejecutar(df_base, fuente_activa=None):
    st.title("🕵️ Laboratorio de Topografía de Datos (Modo Rastreador)")
    st.markdown("---")

    # =====================================================================
    # FASE 1: AISLAMIENTO DEL INTRUSO
    # =====================================================================
    df_raw = df_base.copy()
    columna_intruso = None
    data_intruso = None

    if "_Origen_Archivo" in df_raw.columns:
        columna_intruso = "_Origen_Archivo"
        data_intruso = df_raw["_Origen_Archivo"].copy()
        df_raw = df_raw.drop(columns=["_Origen_Archivo"])
        st.success(f"🚨 TRAMPA 1 SUPERADA: Intruso `{columna_intruso}` detectado y extraído temporalmente para no dañar la geometría.")
    else:
        st.info("🚨 TRAMPA 1: No se detectó la columna intrusa `_Origen_Archivo`.")

    # Bajamos las columnas al nivel de los datos porque app.py ya las rompió al cargarlas
    df_search = pd.concat([pd.DataFrame([df_raw.columns.tolist()]), df_raw]).reset_index(drop=True)

    # =====================================================================
    # FASE 2: EL ESCÁNER DE PROFUNDIDAD (Buscando el Horizonte Real)
    # =====================================================================
    st.markdown("### 🚨 TRAMPA 2: Radiografía de las primeras 15 filas")
    st.caption("Aquí vemos cómo la máquina califica cada fila para decidir dónde termina el título y dónde empieza la data.")
    
    radiografia = []
    data_idx = 0

    for i in range(min(15, len(df_search))):
        row = df_search.iloc[i]
        
        n_unnamed = sum(1 for x in row if 'unnamed' in str(x).lower())
        n_vacios = row.isna().sum() + sum(1 for x in row if str(x).strip().lower() in ['nan', 'none', ''])
        n_numeros = sum(1 for x in row if str(x).replace('.', '', 1).replace('-', '', 1).isdigit())
        
        # Muestra de las primeras 3 columnas para orientarnos visualmente
        muestra = str(row.dropna().tolist()[:3])
        
        radiografia.append({
            "Fila": i, 
            "Celdas 'Unnamed'": n_unnamed, 
            "Celdas Vacías": n_vacios, 
            "Cant. Números": n_numeros, 
            "Muestra (Primeros datos)": muestra
        })

    df_radiografia = pd.DataFrame(radiografia)
    st.dataframe(df_radiografia, use_container_width=True)

    # HEURÍSTICA DE CORTE: 
    # Buscamos la primera fila (después de la 0) que tenga 0 'Unnamed' y donde las celdas vacías bajen drásticamente.
    for i in range(1, len(df_radiografia)):
        if df_radiografia.iloc[i]["Celdas 'Unnamed'"] == 0 and df_radiografia.iloc[i]["Celdas Vacías"] < len(df_search.columns) * 0.4:
            data_idx = i
            break

    st.warning(f"**Conclusión del Algoritmo:** El horizonte de datos empieza en la **Fila {data_idx}**. (Todo lo que esté por encima será aplastado como encabezado).")

    # =====================================================================
    # FASE 3: FUSIÓN TRIDIMENSIONAL (Cascada y Aplastamiento)
    # =====================================================================
    st.markdown("### 🚨 TRAMPA 3: Resultado de la Fusión de Celdas (Linaje)")
    
    if data_idx > 0:
        df_headers = df_search.iloc[0:data_idx].copy()
        
        # 1. Borramos la palabra Unnamed y volvemos los vacíos NaN reales
        def limpiar_basura_header(val):
            if 'unnamed' in str(val).lower() or str(val).strip().lower() in ['', 'nan', 'none']: return np.nan
            return val
            
        df_headers = df_headers.applymap(limpiar_basura_header)
        
        # 2. Cascada Horizontal (Rellena hacia la derecha)
        df_headers = df_headers.ffill(axis=1)
        
        # 3. Aplastamiento Vertical
        nuevas_columnas = []
        ejemplos_fusion = []
        
        for col_idx in range(len(df_headers.columns)):
            jerarquia = []
            for fila_idx in range(len(df_headers)):
                val = df_headers.iloc[fila_idx, col_idx]
                if pd.notna(val):
                    v_str = str(val).strip()
                    if v_str.endswith(".0"): v_str = v_str[:-2] # Arregla los años (2025.0 -> 2025)
                    if not jerarquia or jerarquia[-1] != v_str:
                        jerarquia.append(v_str)
            
            nombre_final = " | ".join(jerarquia) if jerarquia else f"Columna_Vacia_{col_idx}"
            nuevas_columnas.append(nombre_final)
            
            # Guardamos un ejemplo para la trampa visual
            if col_idx < 8: # Mostramos solo las primeras 8 para no saturar
                ejemplos_fusion.append({"Columna Num": col_idx, "Nombre Fusionado": nombre_final})

        st.table(pd.DataFrame(ejemplos_fusion))
    else:
        st.error("No se detectó profundidad de encabezados.")
        nuevas_columnas = df_search.iloc[0].astype(str).tolist()

    # =====================================================================
    # FASE 4: RE-ENSAMBLAJE Y LIMPIEZA FINAL
    # =====================================================================
    st.markdown("### 🚨 TRAMPA 4: Matriz Final (Lista para la IA y el Dashboard)")
    
    # Cortamos la tabla desde donde empieza la data real
    df_final = df_search.iloc[data_idx:].copy()
    
    # Desduplicamos columnas por si quedaron dos llamadas igual
    s = pd.Series(nuevas_columnas)
    df_final.columns = s.where(~s.duplicated(), s + ' (' + s.groupby(s).cumcount().astype(str) + ')')
    
    # Re-insertamos al Intruso si existía
    if data_intruso is not None:
        # Alineamos el índice del intruso con la nueva tabla
        intruso_recortado = data_intruso.iloc[data_idx:].values
        df_final.insert(0, "_Origen_Archivo", intruso_recortado)

    # Ocultamos los Nulos visuales (None, NaN) por un simple vacío
    for col in df_final.columns:
        df_final[col] = df_final[col].apply(lambda x: "" if pd.isna(x) or str(x).strip().lower() in ['nan', 'none', ''] else x)

    # Mostramos los primeros 15 registros para confirmar la victoria
    st.dataframe(df_final.head(15), use_container_width=True)
    
    st.success("🏁 Si esta última tabla se ve perfecta, con los años integrados a sus padres (Ej: EMBOLSE | POR HECTAREA | 2025) y sin palabras raras... ¡El algoritmo funciona!")
