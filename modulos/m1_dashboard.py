"""
MOTOR UNIVERSAL INTELIGENTE DE DATOS (V-ENTERPRISE FINAL)
=========================================================
Arquitectura con Cazador Topográfico, Procesador Semántico y Génesis IA.
"""
import io
import json
import traceback
import re
from datetime import datetime
from typing import Tuple, Dict, Any, List

import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

try:
    import google.generativeai as genai
    _GENAI_OK = True
except Exception:
    _GENAI_OK = False

VALORES_NULOS = {"none", "nan", "nat", "null", "n/a", "#n/a", "-", "--", "", " "}
PALABRAS_MONEDA = ("precio", "costo", "valor", "ingreso", "venta", "presupuesto", "salario", "pago", "gasto", "monto")
PALABRAS_PORCENTAJE = ("%", "porcentaje", "pct", "cumplim", "participac", "tasa", "avance")
PALABRAS_CODIGO = ("id", "código", "codigo", "cod_", "nit", "documento", "referencia", "ref_")

def fmt_es(valor, decimales=2, prefijo="", sufijo=""):
    if pd.isna(valor) or valor == "": return ""
    try: v = float(valor)
    except: return str(valor)
    texto = f"{v:,.{decimales}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return f"{prefijo}{texto}{sufijo}"

def decimales_sugeridos(serie: pd.Series, config_decimales="AUTO"):
    if config_decimales != "AUTO": return int(config_decimales)
    serie_valida = serie.dropna()
    if serie_valida.empty: return 0
    if np.allclose(serie_valida % 1, 0, atol=1e-9): return 0
    return 2

def limpiar_semantica(texto):
    s = str(texto).strip()
    # Eliminar secuencias de años continuas (Ej: 2023-2024-2025-2026)
    s = re.sub(r'\b20\d{2}(?:\s*-\s*20\d{2})+\b', '', s)
    # Limpiar guiones huérfanos y formatear a Title Case
    s = s.replace('-', ' ').replace('_', ' ')
    s = " ".join(s.split())
    return s.title()

def cazador_de_encabezados(df_raw: pd.DataFrame) -> pd.DataFrame:
    data_intruso = None
    if "_Origen_Archivo" in df_raw.columns:
        data_intruso = df_raw["_Origen_Archivo"].copy()
        df_raw = df_raw.drop(columns=["_Origen_Archivo"])

    nombres_cols = np.array(df_raw.columns)[np.newaxis, :]
    matriz_completa = np.vstack([nombres_cols, df_raw.values])
    df_search = pd.DataFrame(matriz_completa)

    radiografia = []
    for i in range(min(20, len(df_search))):
        row = df_search.iloc[i]
        n_nums = sum(1 for x in row if isinstance(x, (int, float)) and pd.notna(x))
        if n_nums == 0: n_nums = sum(1 for x in row if str(x).replace('.', '', 1).replace('-', '', 1).isdigit())
        radiografia.append(n_nums)

    bloque_estable_idx = 0
    for i in range(1, len(radiografia) - 2):
        if all(n >= 10 for n in radiografia[i:i+3]):
            bloque_estable_idx = i
            break

    data_idx = bloque_estable_idx
    if bloque_estable_idx > 0 and 0 < radiografia[bloque_estable_idx - 1] < radiografia[bloque_estable_idx]:
        data_idx = bloque_estable_idx - 1
    if data_idx == 0: data_idx = 1 

    df_headers = df_search.iloc[0:data_idx].copy()
    
    def limpiar_basico(val):
        s = str(val).strip()
        if pd.isna(val) or 'unnamed' in s.lower() or s.lower() in ['', 'nan', 'none']: return np.nan
        return s
        
    df_headers = df_headers.apply(lambda col: col.map(limpiar_basico))
    
    start_row = 0
    for idx in range(len(df_headers)):
        valores_unicos = df_headers.iloc[idx].dropna().unique()
        if len(valores_unicos) >= 2:
            start_row = idx
            break
            
    df_headers = df_headers.iloc[start_row:].ffill(axis=1)
    
    nuevas_cols = []
    for col_idx in range(len(df_headers.columns)):
        jerarquia = []
        for fila_idx in range(len(df_headers)):
            val = df_headers.iloc[fila_idx, col_idx]
            if pd.notna(val):
                v_str = str(val).strip()
                if v_str.endswith(".0"): v_str = v_str[:-2]
                v_str_limpio = limpiar_semantica(v_str)
                if v_str_limpio and (not jerarquia or jerarquia[-1] != v_str_limpio):
                    jerarquia.append(v_str_limpio)
        
        nombre_final = " | ".join(jerarquia) if jerarquia else f"Col_{col_idx}"
        nuevas_cols.append(nombre_final)

    df_final = df_search.iloc[data_idx:].copy()
    s = pd.Series(nuevas_cols)
    df_final.columns = s.where(~s.duplicated(), s + ' (' + s.groupby(s).cumcount().astype(str) + ')')
    
    if data_intruso is not None:
        intruso_array = np.concatenate([np.array(["_Origen_Archivo"]), data_intruso.values])
        df_final.insert(0, "_Origen_Archivo", intruso_array[data_idx:])

    df_final = df_final.dropna(how='all', axis=0).dropna(how='all', axis=1)
    return df_final.reset_index(drop=True)

@st.cache_data(show_spinner=False)
def normalizar_datos(df_raw: pd.DataFrame) -> Dict[str, Any]:
    df = cazador_de_encabezados(df_raw)
    def _limpiar(v):
        if pd.isna(v): return np.nan
        if isinstance(v, str):
            s = v.strip()
            if s.lower() in VALORES_NULOS or s.lower().startswith("unnamed"): return np.nan
            return s
        return v
    df = df.apply(lambda serie: serie.map(_limpiar))
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]) or pd.api.types.is_datetime64_any_dtype(df[col]): continue
        serie = df[col].dropna().astype(str).str.strip()
        if serie.empty: continue
        limpio = serie.str.replace(r"[$\s]", "", regex=True).str.replace("%", "", regex=False)
        limpio = limpio.str.replace(r"\.(?=\d{3}(?:\D|$))", "", regex=True).str.replace(",", ".", regex=False)
        num = pd.to_numeric(limpio, errors="coerce")
        if num.notna().sum() / max(len(serie), 1) > 0.6: df[col] = num
    return {"df_norm": df}

def inferir_semantica(df: pd.DataFrame) -> Dict[str, str]:
    sem = {}
    for col in df.columns:
        nombre, serie = col.lower(), df[col]
        if pd.api.types.is_datetime64_any_dtype(serie): sem[col] = "fecha"
        elif pd.api.types.is_numeric_dtype(serie):
            if any(p in nombre for p in PALABRAS_CODIGO) and serie.dropna().apply(lambda x: float(x).is_integer()).all(): sem[col] = "codigo"
            elif any(p in nombre for p in PALABRAS_PORCENTAJE): sem[col] = "porcentaje"
            elif any(p in nombre for p in PALABRAS_MONEDA): sem[col] = "moneda"
            else: sem[col] = "cantidad"
        else:
            sem[col] = "categoria" if (len(df) > 0 and serie.nunique(dropna=True)/len(df) < 0.5) else "texto"
    return sem

@st.cache_data(show_spinner=False)
def generar_diagnostico_ia(muestra_json, stats_json, columnas):
    if not _GENAI_OK: return None
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
        if not api_key: return None
        genai.configure(api_key=api_key)
        prompt = f"Eres Génesis IA. Analiza: Columnas: {columnas} Muestra: {muestra_json} Resumen: {stats_json}. Genera JSON EXACTO: {{\"titulo_contextual\": \"Título\", \"resumen_gerencial\": \"Análisis táctico\", \"cuellos_de_botella\": [\"Riesgo 1\"]}}"
        model = genai.GenerativeModel("gemini-1.5-flash", generation_config={"response_mime_type": "application/json"})
        respuesta = model.generate_content(prompt).text.strip()
        if "```json" in respuesta: respuesta = respuesta.split("
