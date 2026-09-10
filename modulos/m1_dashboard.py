"""
MOTOR RASTREADOR DE DIAGNÓSTICO (V4 - LINAJE CORTO Y ANTI-RUIDO)
================================================================
"""
import pandas as pd
import numpy as np
import streamlit as st

def ejecutar(df_base, fuente_activa=None):
    st.title("🕵️ Laboratorio B2B (Rastreador V4 - Linaje Corto)")
    st.markdown("---")

    df_raw = df_base.copy()
    data_intruso_search = None

    # =====================================================================
    # FASE 1: AISLAMIENTO BLINDADO
    # =====================================================================
    if "_Origen_Archivo" in df_raw.columns:
        data_intruso = df_raw["_Origen_Archivo"].copy()
        data_intruso_search = np.concatenate([np.array(["_Origen_Archivo"]), data_intruso.values])
        df_raw = df_raw.drop(columns=["_Origen_Archivo"])

    # =====================================================================
    # FASE 2: ALINEACIÓN GEOMÉTRICA (NUMPY) Y CORTE
    # =====================================================================
    nombres_cols = np.array(df_raw.columns)[np.newaxis, :]
    matriz_completa = np.vstack([nombres_cols, df_raw.values])
    df_search = pd.DataFrame(matriz_completa)

    radiografia = []
    for i in range(min(20, len(df_search))):
        row = df_search.iloc[i]
        n_numeros = sum(1 for x in row if isinstance(x, (int, float)) and pd.notna(x)) 
        if n_numeros == 0: 
            n_numeros = sum(1 for x in row if str(x).replace('.', '', 1).replace('-', '', 1).isdigit())
        radiografia.append(n_numeros)

    bloque_estable_idx = 0
    for i in range(1, len(radiografia) - 2):
        if all(n >= 10 for n in radiografia[i:i+3]):
            bloque_estable_idx = i
            break

    data_idx = bloque_estable_idx
    if bloque_estable_idx > 0 and 0 < radiografia[bloque_estable_idx - 1] < radiografia[bloque_estable_idx]:
        data_idx = bloque_estable_idx - 1
    if data_idx == 0: data_idx = 1 
    
    st.info(f"🚨 TRAMPA 1 y 2 SUPERADAS: El corte oficial se mantiene exacto en la **Fila {data_idx}**.")

    # =====================================================================
    # FASE 3: FUSIÓN DE LINAJE (REGLA ANTI-RUIDO Y LINAJE CORTO)
    # =====================================================================
    st.markdown("### 🚨 TRAMPA 3: Fusión de Títulos (Nueva Lógica de Linaje)")
    df_headers = df_search.iloc[0:data_idx].copy()
    
    def limpiar_header(val):
        s = str(val).strip()
        # REGLA 1: Si es nulo, 'unnamed', o muy largo (> 40 chars), lo matamos.
        if pd.isna(val) or 'unnamed' in s.lower() or s.lower() in ['', 'nan', 'none']: return np.nan
        if len(s) > 40: return np.nan  # FILTRO ANTI-RUIDO ACTIVO
        return s
        
    df_headers = df_headers.apply(lambda col: col.map(limpiar_header)).ffill(axis=1)
    
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
        
        # REGLA 2: LINAJE CORTO. Conservamos solo los últimos 3 niveles (máximo)
        jerarquia_corta = jerarquia[-3:] if len(jerarquia) > 3 else jerarquia
        
        nombre_final = " | ".join(jerarquia_corta) if jerarquia_corta else f"Col_Vacia_{col_idx}"
        nuevas_cols.append(nombre_final)

    st.dataframe(pd.DataFrame({"Columna (Excel)": range(len(nuevas_cols)), "Nombre Nuevo y Limpio": nuevas_cols}).head(30))

    # =====================================================================
    # FASE 4: ENSAMBLAJE FINAL
    # =====================================================================
    st.markdown("### 🚨 TRAMPA 4: Matriz Operativa Final (Años Visibles)")
    df_final = df_search.iloc[data_idx:].copy()
    
    s = pd.Series(nuevas_cols)
    df_final.columns = s.where(~s.duplicated(), s + ' (' + s.groupby(s).cumcount().astype(str) + ')')
    
    if data_intruso_search is not None:
        intruso_recortado = data_intruso_search[data_idx:]
        df_final.insert(0, "_Origen_Archivo", intruso_recortado)

    df_final = df_final.dropna(how='all', axis=0).dropna(how='all', axis=1)
    for col in df_final.columns:
        df_final[col] = df_final[col].apply(lambda x: "" if pd.isna(x) or str(x).strip().lower() in ['nan', 'none', ''] else x)

    st.dataframe(df_final.head(15), use_container_width=True)
    st.success("✅ Verifica la Trampa 3 y 4. ¿Los años ahora se ven limpios, al final de nombres cortos, y listos para ser graficados?")
