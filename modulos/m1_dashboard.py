"""
MOTOR RASTREADOR DE DIAGNÓSTICO (V2 - DETECTOR DE ESTABILIDAD)
==============================================================
"""
import pandas as pd
import numpy as np
import streamlit as st

def ejecutar(df_base, fuente_activa=None):
    st.title("🕵️ Laboratorio B2B (Rastreador V2)")
    st.markdown("---")

    df_raw = df_base.copy()
    data_intruso_search = None

    # =====================================================================
    # FASE 1: AISLAMIENTO BLINDADO
    # =====================================================================
    if "_Origen_Archivo" in df_raw.columns:
        data_intruso = df_raw["_Origen_Archivo"].copy()
        # Alineamos el intruso sumando 1 fila fantasma para que empate con df_search sin romper índices
        data_intruso_search = pd.concat([pd.Series(["_Origen_Archivo"]), data_intruso], ignore_index=True)
        df_raw = df_raw.drop(columns=["_Origen_Archivo"])
        st.success("🚨 TRAMPA 1: Intruso separado con alineación matemática perfecta.")

    # NO hacemos dropna aquí para no romper la gravedad geométrica del Excel
    df_search = pd.concat([pd.DataFrame([df_raw.columns.tolist()]), df_raw], ignore_index=True)

    # =====================================================================
    # FASE 2: RADIOGRAFÍA Y DETECTOR DE ESTABILIDAD
    # =====================================================================
    st.markdown("### 🚨 TRAMPA 2: Radiografía de Filas (Buscando el ADN de la tabla)")
    radiografia = []
    
    for i in range(min(15, len(df_search))):
        row = df_search.iloc[i]
        n_vacios = row.isna().sum() + sum(1 for x in row if str(x).strip().lower() in ['nan', 'none', ''])
        
        # Buscamos números reales (int/float) o textos que sean números
        n_numeros = sum(1 for x in row if isinstance(x, (int, float)) and pd.notna(x)) 
        if n_numeros == 0: 
            n_numeros = sum(1 for x in row if str(x).replace('.', '', 1).replace('-', '', 1).isdigit())
        
        muestra = str(row.dropna().tolist()[:4])
        radiografia.append({
            "Fila": i, 
            "Celdas Vacías": n_vacios, 
            "Cant. Números": n_numeros, 
            "Muestra": muestra
        })

    df_rad = pd.DataFrame(radiografia)
    st.dataframe(df_rad, use_container_width=True)

    # HEURÍSTICA DE ESTABILIDAD (Buscando el bloque de datos)
    bloque_estable_idx = 0
    for i in range(1, len(df_rad) - 2):
        vacias_window = df_rad["Celdas Vacías"].iloc[i:i+3].tolist()
        numeros_window = df_rad["Cant. Números"].iloc[i:i+3].tolist()
        
        # Si 3 filas seguidas tienen exactamente la misma estructura, encontramos la mina de oro
        if len(set(vacias_window)) == 1 and len(set(numeros_window)) == 1 and numeros_window[0] > 10:
            bloque_estable_idx = i
            break

    # Ajuste de retroceso: Miramos la fila anterior por si es una semana incompleta (Como la Fila 6)
    data_idx = bloque_estable_idx
    if bloque_estable_idx > 0:
        fila_anterior = df_rad.iloc[bloque_estable_idx - 1]
        # Si la fila anterior tiene algunos números (como semana 52), pero no es un enjambre de años (como la 5)
        if 0 < fila_anterior["Cant. Números"] < df_rad.iloc[bloque_estable_idx]["Cant. Números"]:
            data_idx = bloque_estable_idx - 1

    # Si todo falla, asumimos estándar
    if data_idx == 0: data_idx = 1 
    
    st.warning(f"**Razonamiento de la Máquina:** El bloque perfecto de datos se estabiliza en la **Fila {bloque_estable_idx}**. Ajustando para no perder semanas incompletas, el corte oficial se hará en la **Fila {data_idx}**.")

    # =====================================================================
    # FASE 3: FUSIÓN DE LINAJE (EFECTO CASCADA)
    # =====================================================================
    st.markdown("### 🚨 TRAMPA 3: Fusión de Títulos")
    df_headers = df_search.iloc[0:data_idx].copy()
    
    def limpiar_header(val):
        s = str(val).strip().lower()
        if 'unnamed' in s or s in ['', 'nan', 'none']: return np.nan
        return val
        
    # Rellenamos hacia la derecha las celdas combinadas
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

    st.dataframe(pd.DataFrame({"Columna": range(len(nuevas_cols)), "Nombre Generado": nuevas_cols}).head(12))

    # =====================================================================
    # FASE 4: ENSAMBLAJE FINAL
    # =====================================================================
    st.markdown("### 🚨 TRAMPA 4: Matriz Operativa Final")
    df_final = df_search.iloc[data_idx:].copy()
    
    # Prevenir nombres duplicados
    s = pd.Series(nuevas_cols)
    df_final.columns = s.where(~s.duplicated(), s + ' (' + s.groupby(s).cumcount().astype(str) + ')')
    
    # Inyectamos al Intruso matemáticamente alineado
    if data_intruso_search is not None:
        intruso_recortado = data_intruso_search.iloc[data_idx:].values
        df_final.insert(0, "_Origen_Archivo", intruso_recortado)

    # Purga de nulos visuales para la UI
    df_final = df_final.dropna(how='all', axis=0).dropna(how='all', axis=1)
    for col in df_final.columns:
        df_final[col] = df_final[col].apply(lambda x: "" if pd.isna(x) or str(x).strip().lower() in ['nan', 'none', ''] else x)

    st.dataframe(df_final.head(15), use_container_width=True)
    st.success("✅ Si la tabla de arriba muestra los datos limpios y los títulos combinados (Ej: PLANTAS | EMBOLSE | 2026), tenemos luz verde para el Dashboard.")
