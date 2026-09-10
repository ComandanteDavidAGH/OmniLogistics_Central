"""
MOTOR RASTREADOR DE DIAGNÓSTICO (V3 - BLINDAJE NUMPY)
=====================================================
"""
import pandas as pd
import numpy as np
import streamlit as st

def ejecutar(df_base, fuente_activa=None):
    st.title("🕵️ Laboratorio B2B (Rastreador V3 - Blindaje Numpy)")
    st.markdown("---")

    df_raw = df_base.copy()
    data_intruso_search = None

    # =====================================================================
    # FASE 1: AISLAMIENTO BLINDADO
    # =====================================================================
    if "_Origen_Archivo" in df_raw.columns:
        data_intruso = df_raw["_Origen_Archivo"].copy()
        # Alineación matemática perfecta usando Numpy puro
        data_intruso_search = np.concatenate([np.array(["_Origen_Archivo"]), data_intruso.values])
        df_raw = df_raw.drop(columns=["_Origen_Archivo"])
        st.success("🚨 TRAMPA 1: Intruso separado.")
    else:
        st.info("🚨 TRAMPA 1: No se detectó la columna intrusa.")

    # =====================================================================
    # FASE 2: ALINEACIÓN GEOMÉTRICA (NUMPY) Y RADIOGRAFÍA
    # =====================================================================
    # Apilamos la fila de columnas sobre los datos como bloques, sin usar Pandas
    nombres_cols = np.array(df_raw.columns)[np.newaxis, :]
    datos_matriz = df_raw.values
    matriz_completa = np.vstack([nombres_cols, datos_matriz])
    df_search = pd.DataFrame(matriz_completa)

    st.markdown("### 🚨 TRAMPA 2: Radiografía de Filas (Buscando el ADN)")
    radiografia = []
    
    for i in range(min(20, len(df_search))):
        row = df_search.iloc[i]
        n_vacios = row.isna().sum() + sum(1 for x in row if str(x).strip().lower() in ['nan', 'none', ''])
        
        # Buscamos números reales
        n_numeros = sum(1 for x in row if isinstance(x, (int, float)) and pd.notna(x)) 
        if n_numeros == 0: 
            n_numeros = sum(1 for x in row if str(x).replace('.', '', 1).replace('-', '', 1).isdigit())
        
        muestra = str(row.dropna().tolist()[:4])
        radiografia.append({"Fila": i, "Vacías": n_vacios, "Números": n_numeros, "Muestra": muestra})

    df_rad = pd.DataFrame(radiografia)
    st.dataframe(df_rad, use_container_width=True)

    # HEURÍSTICA DE ESTABILIDAD (Buscando 3 filas seguidas con > 10 números)
    bloque_estable_idx = 0
    for i in range(1, len(df_rad) - 2):
        numeros_window = df_rad["Números"].iloc[i:i+3].tolist()
        if all(n >= 10 for n in numeros_window):
            bloque_estable_idx = i
            break

    # Ajuste de retroceso: verificamos la fila anterior por semanas incompletas
    data_idx = bloque_estable_idx
    if bloque_estable_idx > 0:
        fila_anterior = df_rad.iloc[bloque_estable_idx - 1]
        # Si la fila anterior tiene algunos números (Ej: Semana 52), la arrastramos
        if 0 < fila_anterior["Números"] < df_rad.iloc[bloque_estable_idx]["Números"]:
            data_idx = bloque_estable_idx - 1

    if data_idx == 0: data_idx = 1 # Red de seguridad
    
    st.warning(f"**Razonamiento de la Máquina:** El bloque masivo de datos empieza en la **Fila {bloque_estable_idx}**. Ajustando por semanas incompletas, el corte oficial es en la **Fila {data_idx}**.")

    # =====================================================================
    # FASE 3: FUSIÓN DE LINAJE (EFECTO CASCADA)
    # =====================================================================
    st.markdown("### 🚨 TRAMPA 3: Fusión de Títulos")
    df_headers = df_search.iloc[0:data_idx].copy()
    
    def limpiar_header(val):
        s = str(val).strip().lower()
        if 'unnamed' in s or s in ['', 'nan', 'none']: return np.nan
        return val
        
    df_headers = df_headers.applymap(limpiar_header).ffill(axis=1)
    
    nuevas_cols = []
    for col_idx in range(len(df_headers.columns)):
        jerarquia = []
        for fila_idx in range(len(df_headers)):
            val = df_headers.iloc[fila_idx, col_idx]
            if pd.notna(val):
                v_str = str(val).strip()
                if v_str.endswith(".0"): v_str = v_str[:-2]
                if not jerarquia or jerarquia[-1] != v_str:
                    jerarquia.append(v_str)
        nuevas_cols.append(" | ".join(jerarquia) if jerarquia else f"Col_Vacia_{col_idx}")

    st.dataframe(pd.DataFrame({"Columna": range(len(nuevas_cols)), "Nombre Generado": nuevas_cols}).head(15))

    # =====================================================================
    # FASE 4: ENSAMBLAJE FINAL
    # =====================================================================
    st.markdown("### 🚨 TRAMPA 4: Matriz Operativa Final")
    df_final = df_search.iloc[data_idx:].copy()
    
    # Prevenir nombres duplicados
    s = pd.Series(nuevas_cols)
    df_final.columns = s.where(~s.duplicated(), s + ' (' + s.groupby(s).cumcount().astype(str) + ')')
    
    # Inyectamos al Intruso matemáticamente
    if data_intruso_search is not None:
        intruso_recortado = data_intruso_search[data_idx:]
        df_final.insert(0, "_Origen_Archivo", intruso_recortado)

    # Purga de nulos visuales
    df_final = df_final.dropna(how='all', axis=0).dropna(how='all', axis=1)
    for col in df_final.columns:
        df_final[col] = df_final[col].apply(lambda x: "" if pd.isna(x) or str(x).strip().lower() in ['nan', 'none', ''] else x)

    st.dataframe(df_final.head(15), use_container_width=True)
    st.success("✅ Si la radiografía marcó la Fila 6 (o similar) y esta tabla final se ve limpia, el núcleo está reparado.")
