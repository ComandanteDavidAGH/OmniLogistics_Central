"""
MOTOR B2B (ARQUITECTURA DE ALTA PRECISIÓN Y CONTROL DINÁMICO)
========================================================================
- Lienzo en Blanco: Multiselect inicia vacío por defecto.
- KPIs Dinámicos: Las tarjetas superiores responden y se calculan según la selección.
- Exterminador de Resúmenes: Elimina automáticamente filas de "Total", "AÑO sem", etc.
- Títulos Claros: Cajas con títulos resaltados para cada gráfico.
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

# Paleta Corporativa Elegante (Navy & Gold)
PALETA_CORP = ["#eab308", "#3b82f6", "#10b981", "#6366f1", "#f43f5e", "#8b5cf6"]
VALORES_NULOS = {"none", "nan", "nat", "null", "n/a", "#n/a", "-", "--", ""}

def format_kpi(val, col_name):
    """Abreviación gerencial (M/B) y detección automática de moneda."""
    is_currency = any(x in str(col_name).lower() for x in ['costo', 'precio', 'valor', 'cop', 'usd', 'monto', 'ingreso'])
    if pd.isna(val) or val == "": return "$ 0" if is_currency else "0"
    
    try: v = float(val)
    except Exception: return str(val)

    prefix = "$ " if is_currency else ""
    if abs(v) >= 1_000_000_000:
        return f"{prefix}{v/1_000_000_000:,.2f} B".replace(",", "§").replace(".", ",").replace("§", ".")
    elif abs(v) >= 1_000_000:
        return f"{prefix}{v/1_000_000:,.2f} M".replace(",", "§").replace(".", ",").replace("§", ".")
    else:
        return f"{prefix}{v:,.0f}".replace(",", "§").replace(".", ",").replace("§", ".")

def obtener_nombre_limpio(col_completa):
    """Suprime la jerarquía larga y deja solo Métrica y Año para la UI."""
    if not col_completa or pd.isna(col_completa): return "Métrica"
    texto_limpio = str(col_completa).replace("_", " ")
    partes = [p.strip() for p in texto_limpio.split(" | ") if p.strip()]
    if not partes: return texto_limpio.title()
    
    if len(partes) >= 2:
        anio = partes[-1] if re.match(r'^\d{4}$', partes[-1]) else ""
        metrica = partes[-2] if anio and len(partes)>=2 else partes[-1]
        return f"{metrica} ({anio})" if anio else metrica.title()
    return partes[0].title()

def extractor_semantico_inteligente(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    """El cerebro: Busca la cuadrícula de datos ignorando títulos decorativos."""
    origen = "Archivo Base"
    if "_Origen_Archivo" in df_raw.columns:
        origen = str(df_raw["_Origen_Archivo"].dropna().iloc[0]) if not df_raw["_Origen_Archivo"].dropna().empty else origen
        df_raw = df_raw.drop(columns=["_Origen_Archivo"])

    df_matriz = pd.DataFrame(np.vstack([df_raw.columns, df_raw.values]))

    fila_operativa = 0
    max_textos = 0
    for i in range(min(15, len(df_matriz))):
        textos = sum(1 for x in df_matriz.iloc[i] if pd.notna(x) and any(c.isalpha() for c in str(x)))
        if textos > max_textos:
            max_textos = textos
            fila_operativa = i

    inicio = max(0, fila_operativa - 2)
    fin = fila_operativa + 1 
    if fin < len(df_matriz):
        next_row_nums = sum(1 for x in df_matriz.iloc[fin] if pd.notna(x) and str(x).replace('.0','').isdigit())
        if next_row_nums >= 3:
            fin += 1

    df_headers = df_matriz.iloc[inicio:fin].copy().ffill(axis=1)

    nuevas_cols = []
    for col_idx in range(len(df_headers.columns)):
        jerarquia = []
        for fila_idx in range(len(df_headers)):
            val = df_headers.iloc[fila_idx, col_idx]
            if pd.notna(val) and str(val).strip() != "" and str(val).lower() != 'nan':
                v_str = str(val).replace('.0', '').strip()
                if len(v_str) > 50: continue 
                
                v_str = re.sub(r'\b20\d{2}(?:\s*-\s*20\d{2})+\b', '', v_str).strip('- ')
                v_str = " ".join(v_str.split()) 
                if v_str and (not jerarquia or jerarquia[-1].lower() != v_str.lower()):
                    jerarquia.append(v_str.title() if not v_str.isdigit() else v_str)
                    
        nuevas_cols.append(" | ".join(jerarquia) if jerarquia else f"Col_{col_idx}")

    df_final = df_matriz.iloc[fin:].copy()
    
    cols_unicas, conteo = [], {}
    for col in nuevas_cols:
        if col in conteo:
            conteo[col] += 1
            cols_unicas.append(f"{col} ({conteo[col]})")
        else:
            conteo[col] = 0
            cols_unicas.append(col)
            
    df_final.columns = cols_unicas
    return df_final.dropna(how='all', axis=0).dropna(how='all', axis=1), origen

@st.cache_data(show_spinner=False)
def procesar_archivo(df_raw: pd.DataFrame) -> Dict[str, Any]:
    df, origen = extractor_semantico_inteligente(df_raw)
    df = df.apply(lambda col: col.map(lambda v: np.nan if str(v).lower().strip() in VALORES_NULOS else v))
    
    # EXTERMINADOR UNIVERSAL DE BASURA (Sumatorias, Totales, Años mezclados en el eje)
    # Revisa las 3 primeras columnas para cazar y borrar filas de resumen.
    mask = pd.Series([True] * len(df), index=df.index)
    for col in df.columns[:3]:
        if df[col].dtype == 'object':
            filtro = df[col].astype(str).str.lower().str.contains(r'total|promedio|acumulado|año\b|ano\b|sem\b', regex=True, na=False)
            mask = mask & (~filtro)
    df = df[mask].reset_index(drop=True)
    
    for col in df.columns:
        serie_str = df[col].dropna().astype(str).str.replace(r"[$\s%]", "", regex=True).str.replace(",", ".")
        num = pd.to_numeric(serie_str, errors="coerce")
        if num.notna().sum() / max(len(serie_str), 1) > 0.5:
            df[col] = num
            
    return {"df": df, "origen": origen}

def sugerir_grafico(df, eje_x, metrica):
    if df.empty or eje_x not in df.columns: return "Barras (Comparación)"
    unique_x = df[eje_x].nunique()
    x_lower = str(eje_x).lower()
    metrica_lower = str(metrica).lower()
    
    if unique_x <= 7 and not any(t in x_lower for t in ['semana', 'fecha']): return "Dona (Distribución)"
    elif any(t in x_lower for t in ['semana', 'fecha', 'mes']): return "Líneas (Tendencia)"
    elif any(t in metrica_lower for t in ['acumulado', 'total']): return "Área (Acumulado)"
    else: return "Barras (Comparación)"

def generar_diagnostico_ia(muestra_json, stats_json, columnas):
    if _GENAI_OK:
        try:
            api_key = st.secrets.get("GEMINI_API_KEY", "")
            if api_key:
                genai.configure(api_key=api_key)
                prompt = f"""Eres un Director de Operaciones B2B. Escribe 2 alertas basadas en esto: {columnas}. Devuelve JSON estricto: {{"titulo": "TÍTULO", "resumen": "resumen", "alertas": ["alerta 1", "alerta 2"]}}"""
                model = genai.GenerativeModel("gemini-1.5-flash", generation_config={"response_mime_type": "application/json"})
                resp = model.generate_content(prompt).text.strip()
                if "```json" in resp: resp = resp.split("```json")[1].split("```")[0].strip()
                return json.loads(resp)
        except Exception: pass
    
    return {
        "titulo": "SISTEMA OPERATIVO EN LÍNEA",
        "resumen": "Datos tabulares mapeados y purificados. Trazabilidad lista para inspección visual.",
        "alertas": ["Seleccione sus métricas en el panel para inicializar el Dashboard.", "Los KPIs superiores se calcularán automáticamente según su selección."]
    }

def inyectar_css():
    st.markdown("""
    <style>
        @import url('[https://fonts.googleapis.com/css2?family=Orbitron:wght@500;800;900&family=Rajdhani:wght@500;600;700&display=swap](https://fonts.googleapis.com/css2?family=Orbitron:wght@500;800;900&family=Rajdhani:wght@500;600;700&display=swap)');
        .main { background-color: #0b1120; }
        .title-bar { color: #eab308; font-family: 'Orbitron', sans-serif; font-size: 22px; font-weight: 800; border-bottom: 1px solid #1e293b; padding-bottom: 12px; margin-bottom: 20px; letter-spacing: 1px; } 
        .source-badge { display: inline-block; background: #1e293b; border: 1px solid #334155; color: #94a3b8; padding: 4px 12px; border-radius: 4px; font-family: 'Rajdhani', sans-serif; font-size: 13px; font-weight: 700; margin-bottom: 18px; }
        .ia-card { background: #111827; border-left: 4px solid #eab308; padding: 20px; border-radius: 8px; margin-bottom: 25px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5); } 
        .ia-title { color: #eab308; font-family: 'Orbitron', sans-serif; font-size: 13px; font-weight: 800; margin-bottom: 10px; text-transform: uppercase; } 
        .ia-summary { color: #d1d5db; font-family: 'Rajdhani', sans-serif; font-size: 16px; font-weight: 500; line-height: 1.5; margin-bottom: 12px; } 
        .ia-alert { color: #fb7185; font-family: 'Rajdhani', sans-serif; font-size: 14px; font-weight: 600; margin-top: 6px; padding-left: 10px; border-left: 2px solid #fb7185; } 
        .kpi-card { background: #111827; padding: 18px 15px; border-radius: 8px; border: 1px solid #1f2937; border-top: 3px solid #3b82f6; display: flex; flex-direction: column; justify-content: center; min-height: 100px; margin-bottom: 15px; }
        .kpi-title { font-family: 'Rajdhani', sans-serif; font-size: 13px; color: #9ca3af; font-weight: 700; text-transform: uppercase; line-height: 1.3; word-wrap: break-word; } 
        .kpi-val { font-family: 'Orbitron', sans-serif; font-size: 24px; color: #f3f4f6; font-weight: 800; margin-top: 6px; word-break: break-word; }
        .chart-box { background: #111827; padding: 20px; border-radius: 10px; border: 1px solid #1f2937; margin-bottom: 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        .chart-header { background-color: #1e293b; padding: 10px 15px; border-radius: 6px; margin-bottom: 15px; display: inline-block; border-left: 4px solid #eab308; }
        .chart-title { color:#eab308; font-family: 'Orbitron', sans-serif; font-size: 14px; font-weight: 800; letter-spacing: 0.5px; margin: 0; }
    </style>
    """, unsafe_allow_html=True)

def ejecutar(df_base, fuente_activa=None):
    inyectar_css()

    if df_base is None or df_base.empty:
        st.markdown("<div class='title-bar'>CENTRO DE INTELIGENCIA OPERATIVA</div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='background: #111827; border-left: 4px solid #3b82f6; padding: 40px; border-radius: 8px; margin-top: 20px; text-align: center;'>
            <h2 style='color: #f3f4f6; font-family: Orbitron; margin-bottom: 15px;'>SISTEMA EN ESPERA DE DATOS</h2>
            <p style='color: #9ca3af; font-family: Rajdhani; font-size: 18px; line-height: 1.6;'>
                El Motor Analítico está en línea y configurado para arquitecturas de alto volumen.<br>
                <strong>Suba un archivo (Excel/CSV) para desplegar el Lienzo de Mando.</strong>
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    if "ultima_fuente" not in st.session_state or st.session_state["ultima_fuente"] != fuente_activa:
        st.session_state["ultima_fuente"] = fuente_activa
        st.cache_data.clear()

    with st.spinner("Motor de Extracción purificando y estructurando la topografía de datos..."):
        res = procesar_archivo(df_base)
        df_norm = res["df"]
        
        if df_norm.empty or len(df_norm.columns) == 0:
            st.error("⚠️ El archivo no contiene datos estructurados reconocibles tras la limpieza.")
            st.stop()

        cols_num = [c for c in df_norm.columns if pd.api.types.is_numeric_dtype(df_norm[c].dropna())]
        cols_cat = [c for c in df_norm.columns if c not in cols_num]
        
        cols_eje_x = [c for c in df_norm.columns if any(p in c.lower() for p in ("semana", "cinta", "categoría", "producto", "fecha"))]
        if not cols_eje_x: cols_eje_x = cols_cat if cols_cat else [df_norm.columns[0]]
        
        metricas_reales = [c for c in cols_num if not any(p in c.lower() for p in ("semana", "cinta", "id", "código", "nit", "columna"))]
        if not metricas_reales: metricas_reales = cols_num

        insights = generar_diagnostico_ia(df_norm.head(2).to_json(), "{}", metricas_reales[:10])

    st.markdown("<div class='title-bar'>PANEL GERENCIAL DE OPERACIONES</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='source-badge'>📁 ORIGEN DE EXTRACCIÓN: {res['origen']}</div>", unsafe_allow_html=True)

    alerts = "".join([f"<div class='ia-alert'>⚠️ {alerta}</div>" for alerta in insights.get('alertas', [])])
    st.markdown(f"<div class='ia-card'><div class='ia-title'>🤖 DIAGNÓSTICO TÁCTICO IA</div><div class='ia-summary'>{insights.get('resumen', '')}</div><div>{alerts}</div></div>", unsafe_allow_html=True)

    tab_dash, tab_datos = st.tabs(["🚀 DASHBOARD DE MANDO", "🗄️ MATRIZ DE DATOS PURA"])

    with tab_dash:
        if not metricas_reales:
            st.warning("No se detectaron métricas numéricas financieras o de volumen.")
            st.stop()

        # CONTROLES MULTIVARIABLE
        c1, c2, c3, c4 = st.columns([1.2, 0.8, 1.0, 1.0])
        eje_x = c1.selectbox("1. Dimensión Analítica (Eje X):", cols_eje_x, format_func=obtener_nombre_limpio)
        
        anios = sorted(list(set(re.findall(r'\b20\d{2}\b', " ".join(metricas_reales)))))
        anio_sel = c2.selectbox("2. Filtrar por Año:", ["TODOS"] + anios)

        col_semana = next((c for c in df_norm.columns if "semana" in c.lower()), None)
        df_filtrado = df_norm.copy()
        
        if col_semana:
            semanas = sorted([int(float(str(v))) for v in df_norm[col_semana].dropna().unique() if str(v).replace('.', '', 1).isdigit()])
            if not semanas: semanas = [1, 52]
            s_ini = c3.selectbox("3. Inicio del Periodo:", semanas, index=0)
            s_fin = c4.selectbox("4. Fin del Periodo:", semanas, index=len(semanas)-1)
            
            df_filtrado = df_filtrado[df_filtrado[col_semana].apply(lambda x: s_ini <= int(float(str(x))) <= s_fin if pd.notna(x) and str(x).replace('.','',1).isdigit() else True)]

        opciones_disponibles = metricas_reales
        if anio_sel != "TODOS":
            opciones_disponibles = [c for c in opciones_disponibles if anio_sel in c]

        # LIENZO EN BLANCO: Default vacío para mantener el panel limpio hasta que el usuario decida.
        metricas_sel = st.multiselect("5. Agregue métricas al Cuadro de Mando:", options=opciones_disponibles, default=[], format_func=obtener_nombre_limpio)
        st.markdown("<br>", unsafe_allow_html=True)

        # SI NO HAY SELECCIÓN, SE MUESTRA UN AVISO ELEGANTE Y SE OCULTAN LOS GRÁFICOS
        if not metricas_sel:
            st.info("📌 El lienzo está listo. Seleccione una o más métricas en el panel superior para generar los KPIs y los gráficos de inteligencia.")
        else:
            # TARJETAS KPI DINÁMICAS (Responden exactamente a lo que seleccionaste)
            max_kpis = min(len(metricas_sel), 8) # Límite de seguridad
            for row_idx in range(0, max_kpis, 4):
                kpi_cols = st.columns(4)
                for col_idx in range(4):
                    idx = row_idx + col_idx
                    if idx < max_kpis:
                        m_col = metricas_sel[idx]
                        # EL KPI SE CALCULA SOBRE EL DATAFRAME FILTRADO POR SEMANAS
                        val_sum = df_filtrado[m_col].sum() 
                        nombre_kpi = obtener_nombre_limpio(m_col)
                        formato = format_kpi(val_sum, m_col)
                        with kpi_cols[col_idx]:
                            st.markdown(f"<div class='kpi-card'><div class='kpi-title'>{nombre_kpi}</div><div class='kpi-val'>{formato}</div></div>", unsafe_allow_html=True)
            
            st.markdown("<br><hr style='border-color: #1f2937;'><br>", unsafe_allow_html=True)

            # RENDERIZADO DE GRÁFICOS
            for i in range(0, len(metricas_sel), 2):
                grid = st.columns(2)
                for j in range(2):
                    if i + j < len(metricas_sel):
                        m_col = metricas_sel[i+j]
                        alias = obtener_nombre_limpio(m_col)
                        
                        with grid[j]:
                            st.markdown("<div class='chart-box'>", unsafe_allow_html=True)
                            c_hdr, c_tipo = st.columns([1.5, 1.0])
                            
                            # TÍTULO BLINDADO Y VISIBLE DENTRO DEL CONTENEDOR
                            c_hdr.markdown(f"<div class='chart-header'><p class='chart-title'>{alias.upper()}</p></div>", unsafe_allow_html=True)
                            
                            sugerencia = sugerir_grafico(df_filtrado, eje_x, m_col)
                            tipo_grafico = c_tipo.selectbox("Tipo:", ["Barras (Comparación)", "Líneas (Tendencia)", "Área (Acumulado)", "Dona (Distribución)"], index=["Barras (Comparación)", "Líneas (Tendencia)", "Área (Acumulado)", "Dona (Distribución)"].index(sugerencia), key=f"g_{m_col}", label_visibility="collapsed")
                            
                            df_g = df_filtrado.groupby(eje_x)[m_col].sum().reset_index(name='Valor')
                            df_g[eje_x] = df_g[eje_x].apply(lambda x: str(int(float(x))) if pd.notna(x) and str(x).replace('.','',1).isdigit() else str(x) if pd.notna(x) else "")
                            df_g['Orden'] = df_g[eje_x].apply(lambda x: int(x) if str(x).isdigit() else str(x))
                            df_g = df_g.sort_values('Orden').drop(columns=['Orden'])

                            is_currency = any(x in str(m_col).lower() for x in ['costo', 'precio', 'valor', 'cop', 'usd', 'monto'])
                            unidad_fmt = "$ " if is_currency else ""

                            if "Dona" in tipo_grafico:
                                fig = px.pie(df_g, names=eje_x, values='Valor', hole=0.45, template="plotly_dark", color_discrete_sequence=PALETA_CORP)
                                fig.update_traces(textinfo="label+percent", hovertemplate=f"<b>%{{label}}:</b> {unidad_fmt}%{{value:,.0f}}<extra></extra>")
                            elif "Líneas" in tipo_grafico:
                                fig = px.line(df_g, x=eje_x, y='Valor', text='Valor', markers=True, template="plotly_dark")
                                fig.update_traces(texttemplate="%{text:,.2s}", textposition="top center", line=dict(width=3, color="#3b82f6"), marker=dict(size=8, color="#eab308"), hovertemplate=f"<b>{eje_x}:</b> %{{x}}<br><b>Valor:</b> {unidad_fmt}%{{y:,.0f}}<extra></extra>")
                            elif "Área" in tipo_grafico:
                                fig = px.area(df_g, x=eje_x, y='Valor', text='Valor', template="plotly_dark")
                                fig.update_traces(texttemplate="%{text:,.2s}", textposition="top center", fillcolor="rgba(59, 130, 246, 0.2)", line=dict(width=2, color="#3b82f6"), hovertemplate=f"<b>{eje_x}:</b> %{{x}}<br><b>Valor:</b> {unidad_fmt}%{{y:,.0f}}<extra></extra>")
                            else:
                                fig = px.bar(df_g, x=eje_x, y='Valor', text='Valor', template="plotly_dark", color_discrete_sequence=[PALETA_CORP[0]])
                                fig.update_traces(texttemplate="%{text:,.2s}", textposition="outside", cliponaxis=False, hovertemplate=f"<b>{eje_x}:</b> %{{x}}<br><b>Valor:</b> {unidad_fmt}%{{y:,.0f}}<extra></extra>", marker_line_color="#1e293b", marker_line_width=1)

                            fig.update_layout(
                                paper_bgcolor='rgba(11, 15, 25, 0)', plot_bgcolor='rgba(11, 15, 25, 0)',
                                xaxis=dict(title=dict(text="", font=dict(color='#94a3b8')), tickfont=dict(color='#9ca3af'), type='category'),
                                yaxis=dict(title=dict(text="", font=dict(color='#94a3b8')), tickfont=dict(color='#9ca3af'), showgrid=True, gridcolor='#1f2937'),
                                coloraxis_showscale=False, margin=dict(l=10, r=10, t=20, b=30), height=320
                            )

                            st.plotly_chart(fig, use_container_width=True)
                            st.markdown("</div>", unsafe_allow_html=True)

    with tab_datos:
        st.markdown("<h4 style='color: #eab308; font-family: Orbitron;'>🗄️ MATRIZ DE DATOS PURA</h4>", unsafe_allow_html=True)
        df_mostrar = df_norm.copy()
        for col in df_mostrar.columns:
            if "semana" in col.lower() or "cinta" in col.lower():
                df_mostrar[col] = df_mostrar[col].apply(lambda x: str(int(float(x))) if pd.notna(x) and str(x).replace('.','',1).isdigit() else str(x) if pd.notna(x) else "")
            elif df_mostrar[col].dtype == 'object':
                df_mostrar[col] = df_mostrar[col].fillna("")
                
        config = {col: st.column_config.NumberColumn(col, format="%.0f") for col in metricas_reales}
        st.dataframe(df_mostrar, column_config=config, use_container_width=True, hide_index=True, height=550)
