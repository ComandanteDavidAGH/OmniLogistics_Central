"""
MOTOR UNIVERSAL INTELIGENTE DE DATOS (V-ENTERPRISE)
===================================================
Arquitectura con Cazador de Encabezados Tridimensional y Motor Génesis IA.
"""
import io
import json
import traceback
import hashlib
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

# ==============================================================================
# 1. UTILIDADES Y FORMATO
# ==============================================================================
def fmt_es(valor, decimales=2, prefijo="", sufijo=""):
    if valor is None or (isinstance(valor, float) and (np.isnan(valor) or np.isinf(valor))):
        return ""
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return str(valor)
    texto = f"{v:,.{decimales}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return f"{prefijo}{texto}{sufijo}"

def decimales_sugeridos(serie: pd.Series, config_decimales):
    if config_decimales != "AUTO": return int(config_decimales)
    serie_valida = serie.dropna()
    if serie_valida.empty: return 0
    if np.allclose(serie_valida % 1, 0, atol=1e-9): return 0
    return 2

# ==============================================================================
# 2. CAZADOR DE ENCABEZADOS (TOPOGRAFÍA DE DATOS)
# ==============================================================================
def cazador_de_encabezados(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Escanea el lienzo, rellena celdas combinadas y detecta el inicio de la data real."""
    # Como app.py pudo haber usado la fila 0 como columnas, bajamos las columnas a los datos
    df_search = pd.concat([pd.DataFrame([df_raw.columns.tolist()]), df_raw.copy()]).reset_index(drop=True)
    df_search = df_search.dropna(how='all', axis=0).dropna(how='all', axis=1).reset_index(drop=True)
    if df_search.empty: return df_search

    data_idx = 0
    # 1. Buscar dónde empieza la data (fila con alta densidad de números)
    for i, row in df_search.iterrows():
        numeros = sum(1 for x in row if isinstance(x, (int, float)) and not pd.isna(x))
        llenas = row.notna().sum()
        if (numeros >= len(row) * 0.25) or (llenas >= len(row) * 0.8 and i > 2):
            data_idx = i
            break

    if data_idx == 0:
        df_search.columns = df_search.iloc[0].astype(str)
        return df_search.iloc[1:].reset_index(drop=True)

    # 2. Aislar bloque de encabezados (ignorar títulos flotantes solitarios)
    df_headers = df_search.iloc[0:data_idx].copy()
    valid_headers = df_headers[df_headers.notna().sum(axis=1) >= 3]
    if valid_headers.empty: valid_headers = df_headers

    # 3. EFECTO CASCADA: Relleno horizontal para celdas combinadas
    valid_headers = valid_headers.ffill(axis=1)

    # 4. COMPRESIÓN VERTICAL DE LINAJE
    new_columns = []
    for col in valid_headers.columns:
        jerarquia = []
        for val in valid_headers[col]:
            if pd.notna(val) and str(val).strip() and not str(val).startswith("Unnamed"):
                s = str(val).strip()
                if s.endswith(".0"): s = s[:-2] # Limpiar años tipo 2025.0
                if not jerarquia or jerarquia[-1] != s:
                    jerarquia.append(s)
        
        nombre_final = " | ".join(jerarquia) if jerarquia else f"Col_{col}"
        new_columns.append(nombre_final)

    # Desduplicación de columnas idénticas
    s = pd.Series(new_columns)
    new_columns = s.where(~s.duplicated(), s + ' (' + s.groupby(s).cumcount().astype(str) + ')')

    # 5. Acoplar al dataframe final
    df_data = df_search.iloc[data_idx:].copy()
    df_data.columns = new_columns
    
    return df_data.reset_index(drop=True)

# ==============================================================================
# 3. NORMALIZACIÓN Y LIMPIEZA
# ==============================================================================
def limpiar_nulos_reales(df: pd.DataFrame) -> pd.DataFrame:
    def _limpiar(v):
        if pd.isna(v): return np.nan
        if isinstance(v, str):
            s = v.strip()
            # PARCHE: Solo borrar nulos reales, NO la palabra Unnamed (evita la evaporación de datos)
            if s.lower() in VALORES_NULOS: return np.nan
            return s
        return v
    return df.apply(lambda serie: serie.map(_limpiar))

@st.cache_data(show_spinner=False)
def normalizar_datos(df_raw: pd.DataFrame) -> Dict[str, Any]:
    df = cazador_de_encabezados(df_raw)
    df = df.dropna(how="all", axis=0).dropna(how="all", axis=1)
    df = limpiar_nulos_reales(df)

    # Rescate de números atrapados en texto
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]) or pd.api.types.is_datetime64_any_dtype(df[col]): continue
        serie = df[col].dropna().astype(str).str.strip()
        if serie.empty: continue
        
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
        if pd.api.types.is_datetime64_any_dtype(serie): sem[col] = "fecha"
        elif pd.api.types.is_numeric_dtype(serie):
            if any(p in nombre for p in PALABRAS_CODIGO) and serie.dropna().apply(lambda x: float(x).is_integer()).all(): sem[col] = "codigo"
            elif any(p in nombre for p in PALABRAS_PORCENTAJE): sem[col] = "porcentaje"
            elif any(p in nombre for p in PALABRAS_MONEDA): sem[col] = "moneda"
            else: sem[col] = "cantidad"
        else:
            sem[col] = "categoria" if (len(df) > 0 and serie.nunique(dropna=True)/len(df) < 0.5) else "texto"
    return sem

# ==============================================================================
# 4. MOTOR DE DIAGNÓSTICO IA (GÉNESIS)
# ==============================================================================
@st.cache_data(show_spinner=False)
def generar_diagnostico_ia(muestra_json, stats_json, columnas):
    if not _GENAI_OK: return None
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
        if not api_key: return None
        genai.configure(api_key=api_key)
        
        prompt = f"""
        Eres Génesis IA, motor analítico gerencial.
        Analiza esta estructura de datos:
        Columnas: {columnas}
        Muestra: {muestra_json}
        Resumen: {stats_json}
        
        Genera un JSON EXACTO con:
        {{
            "titulo_contextual": "Título profesional corporativo de la base de datos",
            "resumen_gerencial": "Análisis táctico en 2 oraciones para la toma de decisiones basada en métricas",
            "cuellos_de_botella": ["Riesgo u oportunidad 1", "Riesgo u oportunidad 2"]
        }}
        """
        model = genai.GenerativeModel("gemini-1.5-flash", generation_config={"response_mime_type": "application/json"})
        respuesta = model.generate_content(prompt).text.strip()
        if "```json" in respuesta: respuesta = respuesta.split("```json")[1].split("```")[0].strip()
        return json.loads(respuesta)
    except Exception:
        return None

# ==============================================================================
# 5. RENDERIZADO VISUAL Y DASHBOARD
# ==============================================================================
def inyectar_css():
    st.markdown("""
    <style>
        .title-bar { color:#0f172a; font-family:'Inter',sans-serif; font-size:26px; font-weight:900; border-bottom:2px solid #cbd5e1; padding-bottom:12px; margin-bottom:20px; text-transform:uppercase; }
        .ia-card { background: linear-gradient(145deg, #111827, #1f2937); border-left: 6px solid #10b981; padding: 25px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5); }
        .ia-title { color: #10b981; font-size: 15px; font-weight: 900; text-transform: uppercase; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;}
        .ia-summary { color: #f3f4f6; font-size: 16px; font-weight: 400; line-height: 1.6; margin-bottom: 15px;}
        .ia-alert { color: #fb7185; font-size: 14px; font-weight: 700; margin-top: 8px; padding-left: 10px; border-left: 3px solid #fb7185;}
        .kpi-card { background:#fff; padding:15px; border-radius:8px; border:1px solid #e2e8f0; border-left:4px solid #3b82f6;}
        .kpi-title { font-size:11px; color:#64748b; font-weight:800; text-transform:uppercase;}
        .kpi-val { font-size:22px; color:#0f172a; font-weight:900;}
        button[data-baseweb="tab"] { font-size:16px !important; font-weight:700 !important; color:#64748b !important; }
        button[data-baseweb="tab"][aria-selected="true"] { color:#0f172a !important; border-bottom:3px solid #3b82f6 !important; }
    </style>
    """, unsafe_allow_html=True)

def ejecutar(df_base, fuente_activa=None):
    inyectar_css()
    
    with st.spinner("Decodificando topografía del archivo..."):
        res = normalizar_datos(df_base)
        df_norm = res["df_norm"]
        
        # 🛡️ BLINDAJE ESTRUCTURAL: Prevenir colapso si la tabla no tiene columnas
        if df_norm.empty or len(df_norm.columns) == 0:
            st.error("🚨 La matriz de datos quedó vacía tras el escaneo. Esto ocurre si el archivo tiene un formato no tabular o está en blanco.")
            st.caption("Vista en bruto de lo que intentó leer el sistema:")
            st.dataframe(df_base.head(10))
            return
            
        semantica = inferir_semantica(df_norm)

    # 🛡️ BLINDAJE MATEMÁTICO: Proteger a Pandas al intentar describir la tabla
    try:
        stats_json = df_norm.describe().to_json()
    except ValueError:
        stats_json = "{}"

    # IA DIAGNÓSTICO
    diagnostico = generar_diagnostico_ia(df_norm.head(3).to_json(date_format="iso"), stats_json, list(df_norm.columns))
    
    titulo = diagnostico.get("titulo_contextual", "MOTOR UNIVERSAL B2B") if diagnostico else "MOTOR UNIVERSAL B2B"
    st.markdown(f"<div class='title-bar'>💠 {titulo}</div>", unsafe_allow_html=True)
    if fuente_activa:
        st.caption(f"Origen de datos: {fuente_activa}")

    if diagnostico:
        alerts_html = "".join([f"<div class='ia-alert'>⚠️ {alerta}</div>" for alerta in diagnostico.get("cuellos_de_botella", [])])
        st.markdown(f"""
        <div class='ia-card'>
            <div class='ia-title'>🧠 DIAGNÓSTICO TÁCTICO AUTOMÁTICO (GÉNESIS IA)</div>
            <div class='ia-summary'>{diagnostico.get('resumen_gerencial', '')}</div>
            <div style='margin-top: 15px;'>{alerts_html}</div>
        </div>
        """, unsafe_allow_html=True)

    tab_dash, tab_datos = st.tabs(["📊 DASHBOARD GERENCIAL", "🗄️ BÓVEDA DE DATOS NORMALIZADA"])

    with tab_dash:
        cols_num = [c for c, t in semantica.items() if t in ("cantidad", "moneda", "porcentaje")]
        if not cols_num:
            st.warning("Se requieren métricas numéricas para generar analítica.")
        else:
            kpis = st.columns(4)
            for i, col in enumerate(cols_num[:4]):
                val = df_norm[col].sum()
                formato = f"${fmt_es(val)}" if semantica[col]=="moneda" else fmt_es(val, decimales_sugeridos(df_norm[col], "AUTO"))
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
        buscar = st.text_input("Búsqueda Global en Datos", placeholder="Buscar cualquier coincidencia...")
        df_mostrar = df_norm.copy()
        
        if buscar:
            mask = np.column_stack([df_mostrar[col].astype(str).str.contains(buscar, case=False, na=False) for col in df_mostrar.columns]).any(axis=1)
            df_mostrar = df_mostrar[mask]

        with st.expander("👁️ Configurar Columnas Visibles"):
            opciones = list(df_mostrar.columns)
            default_guardados = st.session_state.get("cols_visibles_b2b", opciones)
            default_seguros = [c for c in default_guardados if c in opciones]
            cols_visibles = st.multiselect("Columnas:", opciones, default=default_seguros, key="cols_visibles_b2b")

        df_final = df_mostrar[cols_visibles] if cols_visibles else df_mostrar

        for col in df_final.columns:
            if df_final[col].dtype == 'object': df_final[col] = df_final[col].fillna("")

        config = {}
        for col in df_final.columns:
            if semantica.get(col) == "moneda": config[col] = st.column_config.NumberColumn(col, format="$ %.2f")
            elif semantica.get(col) == "porcentaje": config[col] = st.column_config.NumberColumn(col, format="%.2f%%")
            elif semantica.get(col) == "cantidad": config[col] = st.column_config.NumberColumn(col, format="localized")
        
        st.dataframe(df_final, column_config=config, use_container_width=True, hide_index=True, height=600)
