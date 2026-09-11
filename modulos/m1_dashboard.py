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
    if pd.isna(valor) or valor == "":
        return ""
    try:
        v = float(valor)
    except Exception:
        return str(valor)
    texto = f"{v:,.{decimales}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return f"{prefijo}{texto}{sufijo}"

def decimales_sugeridos(serie: pd.Series, config_decimales="AUTO"):
    if config_decimales != "AUTO":
        return int(config_decimales)
    serie_valida = serie.dropna()
    if serie_valida.empty:
        return 0
    if np.allclose(serie_valida % 1, 0, atol=1e-9):
        return 0
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
        if n_nums == 0:
            n_nums = sum(1 for x in row if str(x).replace('.', '', 1).replace('-', '', 1).isdigit())
        radiografia.append(n_nums)

    bloque_estable_idx = 0
    for i in range(1, len(radiografia) - 2):
        if all(n >= 10 for n in radiografia[i:i+3]):
            bloque_estable_idx = i
            break

    data_idx = bloque_estable_idx
    if bloque_estable_idx > 0 and 0 < radiografia[bloque_estable_idx - 1] < radiografia[bloque_estable_idx]:
        data_idx = bloque_estable_idx - 1
    
    if data_idx == 0:
        data_idx = 1 

    df_headers = df_search.iloc[0:data_idx].copy()
    
    def limpiar_basico(val):
        s = str(val).strip()
        if pd.isna(val) or 'unnamed' in s.lower() or s.lower() in ['', 'nan', 'none']:
            return np.nan
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
                if v_str.endswith(".0"):
                    v_str = v_str[:-2]
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
        if pd.isna(v):
            return np.nan
        if isinstance(v, str):
            s = v.strip()
            if s.lower() in VALORES_NULOS or s.lower().startswith("unnamed"):
                return np.nan
            return s
        return v
        
    df = df.apply(lambda serie: serie.map(_limpiar))
    
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]) or pd.api.types.is_datetime64_any_dtype(df[col]):
            continue
        serie = df[col].dropna().astype(str).str.strip()
        if serie.empty:
            continue
        limpio = serie.str.replace(r"[$\s]", "", regex=True).str.replace("%", "", regex=False)
        limpio = limpio.str.replace(r"\.(?=\d{3}(?:\D|$))", "", regex=True).str.replace(",", ".", regex=False)
        num = pd.to_numeric(limpio, errors="coerce")
        if num.notna().sum() / max(len(serie), 1) > 0.6:
            df[col] = num
            
    return {"df_norm": df}

def inferir_semantica(df: pd.DataFrame) -> Dict[str, str]:
    sem = {}
    for col in df.columns:
        nombre, serie = col.lower(), df[col]
        if pd.api.types.is_datetime64_any_dtype(serie):
            sem[col] = "fecha"
        elif pd.api.types.is_numeric_dtype(serie):
            if any(p in nombre for p in PALABRAS_CODIGO) and serie.dropna().apply(lambda x: float(x).is_integer()).all():
                sem[col] = "codigo"
            elif any(p in nombre for p in PALABRAS_PORCENTAJE):
                sem[col] = "porcentaje"
            elif any(p in nombre for p in PALABRAS_MONEDA):
                sem[col] = "moneda"
            else:
                sem[col] = "cantidad"
        else:
            sem[col] = "categoria" if (len(df) > 0 and serie.nunique(dropna=True)/len(df) < 0.5) else "texto"
    return sem

@st.cache_data(show_spinner=False)
def generar_diagnostico_ia(muestra_json, stats_json, columnas):
    if not _GENAI_OK:
        return None
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
        if not api_key:
            return None
        genai.configure(api_key=api_key)
        
        prompt = f"""
        Eres Génesis IA, motor analítico gerencial.
        Analiza esta estructura:
        Columnas: {columnas}
        Muestra: {muestra_json}
        Resumen: {stats_json}
        
        Genera un JSON EXACTO con:
        {{
            "titulo_contextual": "Título B2B",
            "resumen_gerencial": "Análisis táctico",
            "cuellos_de_botella": ["Riesgo 1"]
        }}
        """
        model = genai.GenerativeModel("gemini-1.5-flash", generation_config={"response_mime_type": "application/json"})
        respuesta = model.generate_content(prompt).text.strip()
        
        if "```json" in respuesta:
            respuesta = respuesta.split("```json")[1].split("```")[0].strip()
        return json.loads(respuesta)
    except Exception:
        return None

def inyectar_css():
    st.markdown('''
    <style>
        .title-bar { color:#0f172a; font-family:'Inter',sans-serif; font-size:26px; font-weight:900; border-bottom:2px solid #cbd5e1; padding-bottom:12px; margin-bottom:20px; text-transform:uppercase; } 
        .ia-card { background: linear-gradient(145deg, #111827, #1f2937); border-left: 6px solid #10b981; padding: 25px; border-radius: 12px; margin-bottom: 25px; } 
        .ia-title { color: #10b981; font-size: 15px; font-weight: 900; margin-bottom: 12px;} 
        .ia-summary { color: #f3f4f6; font-size: 16px; margin-bottom: 15px;} 
        .ia-alert { color: #fb7185; font-size: 14px; font-weight: 700; margin-top: 8px; padding-left: 10px; border-left: 3px solid #fb7185;} 
        .kpi-card { background:#fff; padding:15px; border-radius:8px; border:1px solid #e2e8f0; border-left:4px solid #3b82f6;} 
        .kpi-title { font-size:11px; color:#64748b; font-weight:800; text-transform:uppercase;} 
        .kpi-val { font-size:22px; color:#0f172a; font-weight:900;}
    </style>
    ''', unsafe_allow_html=True)

def ejecutar(df_base, fuente_activa=None):
    inyectar_css()
    with st.spinner("Construyendo topografía corporativa y limpiando semántica..."):
        res = normalizar_datos(df_base)
        df_norm = res["df_norm"]
        semantica = inferir_semantica(df_norm)

    try:
        stats_json = df_norm.describe().to_json()
    except ValueError:
        stats_json = "{}"
        
    diagnostico = generar_diagnostico_ia(df_norm.head(3).to_json(date_format="iso"), stats_json, list(df_norm.columns))
    
    titulo = diagnostico.get("titulo_contextual", "MOTOR UNIVERSAL B2B") if diagnostico else "MOTOR UNIVERSAL B2B"
    st.markdown(f"<div class='title-bar'>💠 {titulo}</div>", unsafe_allow_html=True)

    if diagnostico:
        alerts = "".join([f"<div class='ia-alert'>⚠️ {alerta}</div>" for alerta in diagnostico.get("cuellos_de_botella", [])])
        st.markdown(f"<div class='ia-card'><div class='ia-title'>🧠 DIAGNÓSTICO TÁCTICO (GÉNESIS IA)</div><div class='ia-summary'>{diagnostico.get('resumen_gerencial', '')}</div><div>{alerts}</div></div>", unsafe_allow_html=True)

    tab_dash, tab_datos = st.tabs(["📊 DASHBOARD GERENCIAL", "🗄️ BÓVEDA NORMALIZADA"])

    with tab_dash:
        cols_num = [c for c, t in semantica.items() if t in ("cantidad", "moneda", "porcentaje")]
        if not cols_num:
            st.warning("Se requieren métricas numéricas para generar analítica.")
        else:
            kpis = st.columns(4)
            for i, col in enumerate(cols_num[:4]):
                val = df_norm[col].sum()
                formato = f"${fmt_es(val)}" if semantica[col]=="moneda" else fmt_es(val, decimales_sugeridos(df_norm[col]))
                with kpis[i]:
                    st.markdown(f"<div class='kpi-card'><div class='kpi-title'>{col[:20]}</div><div class='kpi-val'>{formato}</div></div>", unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            c_x, c_y = st.columns(2)
            eje_x = c_x.selectbox("Eje X (Segmento):", df_norm.columns)
            eje_y = c_y.selectbox("Eje Y (Métrica):", cols_num)
            
            if eje_x and eje_y:
                df_g = df_norm.groupby(eje_x)[eje_y].sum().reset_index(name='Total').sort_values('Total', ascending=False).head(20)
                fig = px.bar(df_g, x=eje_x, y='Total', template="plotly_white")
                fig.update_traces(marker_color='#3b82f6')
                st.plotly_chart(fig, use_container_width=True)

    with tab_datos:
        df_mostrar = df_norm.copy()
        for col in df_mostrar.columns:
            if df_mostrar[col].dtype == 'object':
                df_mostrar[col] = df_mostrar[col].fillna("")
        
        config = {}
        for col in df_mostrar.columns:
            if semantica.get(col) == "moneda":
                config[col] = st.column_config.NumberColumn(col, format="$ %.2f")
            elif semantica.get(col) == "porcentaje":
                config[col] = st.column_config.NumberColumn(col, format="%.2f%%")
            elif semantica.get(col) == "cantidad":
                config[col] = st.column_config.NumberColumn(col, format="localized")
        
        st.dataframe(df_mostrar, column_config=config, use_container_width=True, hide_index=True, height=600)
