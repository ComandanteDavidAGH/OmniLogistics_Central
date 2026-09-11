"""
MOTOR UNIVERSAL INTELIGENTE DE DATOS (FUTURISTIC B2B EDITION)
=============================================================
Arquitectura con Cazador Topográfico, Filtro Semántico, UI Cyberpunk 
y Motor Analítico Conectado a Google Gemini IA.
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
import plotly.graph_objects as go

try:
    import google.generativeai as genai
    _GENAI_OK = True
except Exception:
    _GENAI_OK = False

VALORES_NULOS = {"none", "nan", "nat", "null", "n/a", "#n/a", "-", "--", "", " "}
PALABRAS_MONEDA = ("precio", "costo", "valor", "ingreso", "venta", "presupuesto", "salario", "pago", "gasto", "monto", "usd", "cop")
PALABRAS_PORCENTAJE = ("%", "porcentaje", "pct", "cumplim", "participac", "tasa", "avance")
PALABRAS_CODIGO = ("id", "código", "codigo", "cod_", "nit", "documento", "referencia", "ref_")

# ==============================================================================
# 1. FORMATO Y CLASIFICACIÓN CONTEXTUAL
# ==============================================================================
def fmt_es(valor, decimales=2, prefijo="", sufijo=""):
    if pd.isna(valor) or valor == "":
        return ""
    try:
        v = float(valor)
    except Exception:
        return str(valor)
    texto = f"{v:,.{decimales}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return f"{prefijo}{texto}{sufijo}"

def decimales_sugeridos(serie: pd.Series):
    serie_valida = serie.dropna()
    if serie_valida.empty:
        return 0
    if np.allclose(serie_valida % 1, 0, atol=1e-9):
        return 0
    return 2

def limpiar_semantica(texto):
    s = str(texto).strip()
    s = re.sub(r'\b20\d{2}(?:\s*-\s*20\d{2})+\b', '', s)
    s = s.replace('-', ' ').replace('_', ' ')
    s = " ".join(s.split())
    return s.title()

# ==============================================================================
# 2. CAZADOR DE ENCABEZADOS (TOPOGRAFÍA NUMPY)
# ==============================================================================
def cazador_de_encabezados(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    origen_etiqueta = "Desconocido"
    if "_Origen_Archivo" in df_raw.columns:
        val_origen = df_raw["_Origen_Archivo"].dropna().iloc[0] if not df_raw["_Origen_Archivo"].dropna().empty else "Archivo"
        origen_etiqueta = str(val_origen)
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
        
        nombre_final = " | ".join(jerarquia) if jerarquia else f"Métrica_{col_idx}"
        nuevas_cols.append(nombre_final)

    df_final = df_search.iloc[data_idx:].copy()
    s = pd.Series(nuevas_cols)
    df_final.columns = s.where(~s.duplicated(), s + ' (' + s.groupby(s).cumcount().astype(str) + ')')
    
    df_final = df_final.dropna(how='all', axis=0).dropna(how='all', axis=1)
    return df_final.reset_index(drop=True), origen_etiqueta

@st.cache_data(show_spinner=False)
def normalizar_datos(df_raw: pd.DataFrame) -> Dict[str, Any]:
    df, etiqueta_origen = cazador_de_encabezados(df_raw)
    
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
            
    return {"df_norm": df, "origen": etiqueta_origen}

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

# ==============================================================================
# 3. CONEXIÓN CON GOOGLE GEMINI IA
# ==============================================================================
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
        Eres Génesis IA, el motor de inteligencia de negocios B2B de alto rendimiento.
        Analiza la estructura operativa de estos datos:
        Columnas: {columnas}
        Muestra Operativa: {muestra_json}
        Resumen Estadístico: {stats_json}
        
        Responde estrictamente en un objeto JSON estructurado con estas llaves exactas:
        {{
            "titulo_contextual": "Título dinámico y corporativo corto (Ej: ANALÍTICA DE PRODUCCIÓN BANANERA)",
            "resumen_gerencial": "Evaluación táctica de 2-3 oraciones identificando patrones clave de rendimiento.",
            "cuellos_de_botella": ["Alerta o riesgo operativo 1", "Oportunidad de optimización 2"]
        }}
        """
        model = genai.GenerativeModel("gemini-1.5-flash", generation_config={"response_mime_type": "application/json"})
        respuesta = model.generate_content(prompt).text.strip()
        
        if "```json" in respuesta:
            respuesta = respuesta.split("```json")[1].split("```")[0].strip()
        return json.loads(respuesta)
    except Exception:
        return None

# ==============================================================================
# 4. DISEÑO FUTURISTA B2B (CSS STYLES)
# ==============================================================================
def inyectar_css():
    st.markdown('''
    <style>
        @import url('[https://fonts.googleapis.com/css2?family=Orbitron:wght@500;800;900&family=Rajdhani:wght@500;600;700&display=swap](https://fonts.googleapis.com/css2?family=Orbitron:wght@500;800;900&family=Rajdhani:wght@500;600;700&display=swap)');
        
        .main { background-color: #0b0f19; }
        .title-bar { 
            color: #38bdf8; 
            font-family: 'Orbitron', sans-serif; 
            font-size: 24px; 
            font-weight: 800; 
            letter-spacing: 1.5px;
            border-bottom: 2px solid #1e293b; 
            padding-bottom: 12px; 
            margin-bottom: 20px; 
            text-shadow: 0 0 10px rgba(56, 189, 248, 0.3);
        } 
        .source-badge {
            display: inline-block;
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid #38bdf8;
            color: #38bdf8;
            padding: 4px 12px;
            border-radius: 20px;
            font-family: 'Rajdhani', sans-serif;
            font-size: 13px;
            font-weight: 700;
            margin-bottom: 18px;
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.2);
        }
        .ia-card { 
            background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.8)); 
            border-left: 5px solid #10b981; 
            border-top: 1px solid rgba(255, 255, 255, 0.05);
            padding: 22px; 
            border-radius: 12px; 
            margin-bottom: 25px; 
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
            backdrop-filter: blur(10px);
        } 
        .ia-title { 
            color: #10b981; 
            font-family: 'Orbitron', sans-serif;
            font-size: 14px; 
            font-weight: 800; 
            letter-spacing: 1px;
            margin-bottom: 10px;
        } 
        .ia-summary { 
            color: #e2e8f0; 
            font-family: 'Rajdhani', sans-serif;
            font-size: 17px; 
            font-weight: 500;
            line-height: 1.5; 
            margin-bottom: 12px;
        } 
        .ia-alert { 
            color: #fb7185; 
            font-family: 'Rajdhani', sans-serif;
            font-size: 15px; 
            font-weight: 700; 
            margin-top: 6px; 
            padding-left: 10px; 
            border-left: 3px solid #fb7185;
        } 
        .kpi-card { 
            background: rgba(15, 23, 42, 0.75); 
            padding: 18px; 
            border-radius: 10px; 
            border: 1px solid rgba(255, 255, 255, 0.08); 
            border-top: 3px solid #06b6d4;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            transition: transform 0.2s;
        }
        .kpi-title { 
            font-family: 'Rajdhani', sans-serif;
            font-size: 13px; 
            color: #94a3b8; 
            font-weight: 700; 
            text-transform: uppercase;
            letter-spacing: 0.5px;
        } 
        .kpi-val { 
            font-family: 'Orbitron', sans-serif;
            font-size: 22px; 
            color: #f8fafc; 
            font-weight: 800;
            margin-top: 6px;
            text-shadow: 0 0 8px rgba(6, 182, 212, 0.4);
        }
    </style>
    ''', unsafe_allow_html=True)

# ==============================================================================
# 5. DASHBOARD CONTROL CENTER
# ==============================================================================
def ejecutar(df_base, fuente_activa=None):
    inyectar_css()
    
    with st.spinner("Decodificando topografía y sincronizando Inteligencia artificial..."):
        res = normalizar_datos(df_base)
        df_norm = res["df_norm"]
        origen_etiqueta = res["origen"]
        semantica = inferir_semantica(df_norm)

    try:
        stats_json = df_norm.describe().to_json()
    except ValueError:
        stats_json = "{}"
        
    diagnostico = generar_diagnostico_ia(df_norm.head(3).to_json(date_format="iso"), stats_json, list(df_norm.columns))
    
    titulo = diagnostico.get("titulo_contextual", "SISTEMA OPERATIVO DE DATOS B2B") if diagnostico else "SISTEMA OPERATIVO DE DATOS B2B"
    st.markdown(f"<div class='title-bar'>⚡ {titulo}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='source-badge'>📁 FUENTE: {origen_etiqueta}</div>", unsafe_allow_html=True)

    if diagnostico:
        alerts = "".join([f"<div class='ia-alert'>⚠️ {alerta}</div>" for alerta in diagnostico.get("cuellos_de_botella", [])])
        st.markdown(
            f"""
            <div class='ia-card'>
                <div class='ia-title'>🤖 DIAGNÓSTICO TÁCTICO (GOOGLE GEMINI IA)</div>
                <div class='ia-summary'>{diagnostico.get('resumen_gerencial', '')}</div>
                <div>{alerts}</div>
            </div>
            """, 
            unsafe_allow_html=True
        )

    tab_dash, tab_datos = st.tabs(["🚀 COMMAND CENTER (DASHBOARD)", "🗄️ BÓVEDA DE DATOS NORMALIZADA"])

    with tab_dash:
        cols_num = [c for c, t in semantica.items() if t in ("cantidad", "moneda", "porcentaje")]
        
        if not cols_num:
            st.warning("No se detectaron variables numéricas para generar analítica de gráficos.")
        else:
            # 1. TARJETAS KPI FUTURISTAS
            kpi_cols = st.columns(min(4, len(cols_num)))
            for i, col in enumerate(cols_num[:4]):
                val_total = df_norm[col].sum()
                if semantica[col] == "moneda":
                    formato = f"${fmt_es(val_total)}"
                elif semantica[col] == "porcentaje":
                    formato = f"{fmt_es(val_total, 2)}%"
                else:
                    formato = fmt_es(val_total, decimales_sugeridos(df_norm[col]))
                    
                nombre_kpi = col.split(" | ")[-1] if " | " in col else col
                with kpi_cols[i]:
                    st.markdown(
                        f"""
                        <div class='kpi-card'>
                            <div class='kpi-title'>{nombre_kpi[:25]}</div>
                            <div class='kpi-val'>{formato}</div>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
            
            st.markdown("<br><hr style='border-color: #1e293b;'><br>", unsafe_allow_html=True)

            # 2. CONTROLES Y FILTROS INTELIGENTES
            c_sec1, c_sec2, c_sec3 = st.columns([1.5, 1.5, 1])
            
            # Formateador de opciones para los selectores (Etiquetas limpias)
            opciones_y = {col: (f"{col.split(' | ')[-2]} ({col.split(' | ')[-1]})" if len(col.split(" | ")) >= 2 else col) for col in cols_num}
            
            eje_x = c_sec1.selectbox("Eje Principal (Segmento / Categoría):", df_norm.columns)
            eje_y_col = c_sec2.selectbox("Métrica de Comparación:", list(opciones_y.keys()), format_func=lambda x: opciones_y[x])
            
            # Selector de filtro por Años (Detectados dinámicamente)
            anios_detectados = sorted(list(set(re.findall(r'\b20\d{2}\b', " ".join(df_norm.columns)))))
            anio_filtro = "TODOS"
            if anios_detectados:
                anio_filtro = c_sec3.selectbox("Filtro Temporal (Año):", ["TODOS"] + anios_detectados)

            # 3. PROCESAMIENTO Y GRÁFICO FUTURISTA (PLOTLY CYBERPUNK)
            df_chart = df_norm.copy()
            if anio_filtro != "TODOS":
                cols_filtradas = [c for c in df_chart.columns if anio_filtro in c or df_chart[c].dtype == 'object']
                if eje_y_col in cols_filtradas:
                    df_chart = df_chart[cols_filtradas]

            df_g = df_chart.groupby(eje_x)[eje_y_col].sum().reset_index(name='Valor').sort_values('Valor', ascending=False).head(15)

            # Construcción gráfica en Plotly
            fig = px.bar(
                df_g, 
                x=eje_x, 
                y='Valor',
                text='Valor',
                template="plotly_dark",
                color='Valor',
                color_continuous_scale="Electric"
            )

            # Personalización de la interfaz del gráfico
            unidad_formato = "$" if semantica.get(eje_y_col) == "moneda" else ""
            fig.update_traces(
                texttemplate=f'{unidad_formato}%{{text:,.1f}}', 
                textposition='outside',
                marker_line_color='#06b6d4',
                marker_line_width=1.5,
                opacity=0.9
            )
            
            fig.update_layout(
                title=dict(
                    text=f"ANÁLISIS DE COMPARATIVA: {opciones_y[eje_y_col].upper()}",
                    font=dict(family='Orbitron', size=16, color='#38bdf8')
                ),
                paper_bgcolor='rgba(11, 15, 25, 0)',
                plot_bgcolor='rgba(15, 23, 42, 0.5)',
                xaxis=dict(title=dict(font=dict(color='#94a3b8')), tickfont=dict(color='#cbd5e1')),
                yaxis=dict(title=dict(text="Volumen / Métrica", font=dict(color='#94a3b8')), tickfont=dict(color='#cbd5e1')),
                coloraxis_showscale=False,
                margin=dict(l=20, r=20, t=60, b=40),
                height=480
            )

            st.plotly_chart(fig, use_container_width=True)

    with tab_datos:
        st.markdown("<h4 style='color: #38bdf8; font-family: Orbitron;'>🗄️ BÓVEDA DE DATOS OPERATIVOS NORMALIZADA</h4>", unsafe_allow_html=True)
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
        
        st.dataframe(df_mostrar, column_config=config, use_container_width=True, hide_index=True, height=550)
