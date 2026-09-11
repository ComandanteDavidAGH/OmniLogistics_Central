"""
MOTOR B2B IMPULSADO POR AGENTE IA (GÉNESIS ORQUESTRATOR)
========================================================================
- Estética Corporativa: Diseño Navy & Gold (Sobrio y elegante).
- Formateo Inteligente: Detección de moneda y abreviación de cifras grandes (M, B).
- Agente IA: Selección de gráficos basada en la densidad y tipo de datos.
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

# Paleta Corporativa Elegante (Dorados, Azules, Verdes sobrios)
PALETA_CORP = ["#eab308", "#3b82f6", "#10b981", "#6366f1", "#f43f5e", "#8b5cf6"]
VALORES_NULOS = {"none", "nan", "nat", "null", "n/a", "#n/a", "-", "--", ""}

def format_kpi(val, col_name):
    """Formatea números grandes con M/B y detecta si es moneda automáticamente."""
    is_currency = any(x in str(col_name).lower() for x in ['costo', 'precio', 'valor', 'cop', 'usd', 'monto', 'ingreso'])
    if pd.isna(val): return "$ 0" if is_currency else "0"
    
    prefix = "$ " if is_currency else ""
    
    # Abreviación para tarjetas KPI
    if abs(val) >= 1_000_000_000:
        return f"{prefix}{val/1_000_000_000:,.2f} B".replace(",", "§").replace(".", ",").replace("§", ".")
    elif abs(val) >= 1_000_000:
        return f"{prefix}{val/1_000_000:,.2f} M".replace(",", "§").replace(".", ",").replace("§", ".")
    else:
        return f"{prefix}{val:,.0f}".replace(",", "§").replace(".", ",").replace("§", ".")

def obtener_nombre_limpio(col_completa):
    """Limpia guiones bajos y extrae un título legible."""
    if not col_completa or pd.isna(col_completa): return "Métrica"
    
    # Limpiar guiones bajos
    texto_limpio = str(col_completa).replace("_", " ")
    
    partes = [p.strip() for p in texto_limpio.split(" | ") if p.strip()]
    if not partes: return texto_limpio.title()
    
    if len(partes) >= 2:
        anio = partes[-1] if re.match(r'^\d{4}$', partes[-1]) else ""
        métrica = partes[-2] if anio and len(partes)>=2 else partes[-1]
        modulo = partes[0] if len(partes) >= 3 else ""
        prefijo = f"{modulo} - " if modulo and modulo != métrica else ""
        resultado = f"{prefijo}{métrica} ({anio})" if anio else f"{prefijo}{métrica}"
        return resultado.title()
        
    return partes[0].title()

def sugerir_grafico(df, eje_x, metrica):
    """La IA determina el mejor gráfico analizando los datos reales."""
    if df.empty or eje_x not in df.columns: return "Barras (Comparación)"
    
    unique_x = df[eje_x].nunique()
    x_lower = str(eje_x).lower()
    metrica_lower = str(metrica).lower()
    
    if unique_x <= 6 and not any(t in x_lower for t in ['semana', 'fecha', 'mes', 'año']):
        return "Dona (Distribución)"
    elif any(t in x_lower for t in ['semana', 'fecha', 'mes', 'año', 'date']):
        return "Líneas (Tendencia)"
    elif any(t in metrica_lower for t in ['acumulado', 'total', 'crecimiento']):
        return "Área (Acumulado)"
    else:
        return "Barras (Comparación)"

def cazador_de_encabezados(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    origen = "Archivo Base"
    if "_Origen_Archivo" in df_raw.columns:
        origen = str(df_raw["_Origen_Archivo"].dropna().iloc[0]) if not df_raw["_Origen_Archivo"].dropna().empty else origen
        df_raw = df_raw.drop(columns=["_Origen_Archivo"])

    df_search = pd.DataFrame(np.vstack([np.array(df_raw.columns)[np.newaxis, :], df_raw.values]))

    radiografia = [sum(1 for x in row if isinstance(x, (int, float)) and pd.notna(x) or str(x).replace('.', '', 1).isdigit()) for i, row in df_search.head(20).iterrows()]
    
    data_idx = 1
    for i in range(1, len(radiografia) - 2):
        if all(n >= 10 for n in radiografia[i:i+3]):
            data_idx = i - 1 if radiografia[i-1] > 0 else i
            break

    df_headers = df_search.iloc[0:max(1, data_idx)].copy()
    df_headers = df_headers.apply(lambda col: col.map(
        lambda v: np.nan if pd.isna(v) or 'unnamed' in str(v).lower() or str(v).strip() == '' else str(v).strip()
    ))
    df_headers = df_headers.ffill(axis=1)

    nuevas_cols = []
    for col_idx in range(len(df_headers.columns)):
        jerarquia = []
        for fila_idx in range(len(df_headers)):
            val = df_headers.iloc[fila_idx, col_idx]
            if pd.notna(val):
                v_str = re.sub(r'\b20\d{2}(?:\s*-\s*20\d{2})+\b', '', str(val).replace('.0', '')).strip().title()
                if v_str and (not jerarquia or jerarquia[-1] != v_str):
                    jerarquia.append(v_str)
        nuevas_cols.append(" | ".join(jerarquia) if jerarquia else f"Col_{col_idx}")

    df_final = df_search.iloc[data_idx:].copy()
    
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
    df, origen = cazador_de_encabezados(df_raw)
    df = df.apply(lambda col: col.map(lambda v: np.nan if str(v).lower().strip() in VALORES_NULOS else v))
    
    for col in df.columns:
        serie_str = df[col].dropna().astype(str).str.replace(r"[$\s%]", "", regex=True).str.replace(",", ".")
        num = pd.to_numeric(serie_str, errors="coerce")
        if num.notna().sum() / max(len(serie_str), 1) > 0.6:
            df[col] = num
    return {"df": df, "origen": origen}

class AgenteOrquestador:
    def __init__(self, df: pd.DataFrame):
        self.df = df
        self.columnas = df.columns.tolist()
        self.dimensiones, self.metricas, self.modulos, self.anios = [], [], {}, []
        self.mapeo_nombres = {}

    def planear_y_organizar(self):
        for col in self.columnas:
            serie = self.df[col].dropna()
            if pd.api.types.is_numeric_dtype(serie) and not any(p in col.lower() for p in ['semana', 'código', 'id', 'cinta', 'nit', 'documento']):
                self.metricas.append(col)
            elif len(serie.unique()) < 100:
                self.dimensiones.append(col)

        anios_set = set()
        for col in self.metricas:
            match = re.search(r'\b(20\d{2})\b', col)
            if match: anios_set.add(match.group(1))
        self.anios = sorted(list(anios_set))

        for col in self.metricas:
            partes = [p.strip() for p in col.split(" | ")]
            anio = partes[-1] if re.match(r'^\d{4}$', partes[-1]) else ""
            metrica_base = partes[-2] if anio and len(partes)>=2 else partes[-1]
            modulo = partes[0] if len(partes) > 1 else "General"
            if modulo == metrica_base and len(partes) >= 3: modulo = partes[1]
                
            if modulo not in self.modulos: self.modulos[modulo] = []
            self.modulos[modulo].append(col)
            self.mapeo_nombres[col] = obtener_nombre_limpio(col)

        self.dimensiones = sorted(self.dimensiones, key=lambda x: (0 if 'cinta' in x.lower() else 1 if 'semana' in x.lower() else 2))
        if not self.dimensiones: self.dimensiones = self.columnas[:1]

    def generar_insights(self):
        if not _GENAI_OK: return self._fallback_insight()
        try:
            api_key = st.secrets.get("GEMINI_API_KEY", "")
            if not api_key: return self._fallback_insight()
            genai.configure(api_key=api_key)
            prompt = f"""
            Eres el Director de Operaciones IA. Analiza estos datos: {self.df.head(3).to_json()}
            Devuelve un diagnóstico en JSON:
            {{
                "titulo": "ANÁLISIS ESTRATÉGICO DE OPERACIONES",
                "resumen": "Resumen táctico de 2 líneas.",
                "alertas": ["Alerta 1 detectada", "Recomendación operativa 2"]
            }}
            """
            model = genai.GenerativeModel("gemini-1.5-flash", generation_config={"response_mime_type": "application/json"})
            resp = model.generate_content(prompt).text.strip()
            if "```json" in resp: resp = resp.split("```json")[1].split("```")[0].strip()
            return json.loads(resp)
        except Exception: return self._fallback_insight()

    def _fallback_insight(self):
        return {
            "titulo": "SISTEMA ORQUESTADOR EN LÍNEA",
            "resumen": "Mapeo topográfico completado. Dimensiones y métricas financieras catalogadas.",
            "alertas": ["Control: Verifique las tendencias de costos contra los niveles de alerta mínima.", "Optimización: Aísle los indicadores clave utilizando los selectores de rango de tiempo."]
        }

def inyectar_css():
    st.markdown("""
    <style>
        @import url('[https://fonts.googleapis.com/css2?family=Orbitron:wght@500;800;900&family=Rajdhani:wght@500;600;700&display=swap](https://fonts.googleapis.com/css2?family=Orbitron:wght@500;800;900&family=Rajdhani:wght@500;600;700&display=swap)');
        
        /* Paleta Corporativa Elegante (Navy & Gold) */
        .main { background-color: #0b1120; }
        
        /* Títulos limpios */
        .title-bar { color: #eab308; font-family: 'Orbitron', sans-serif; font-size: 22px; font-weight: 800; border-bottom: 1px solid #1e293b; padding-bottom: 12px; margin-bottom: 20px; letter-spacing: 1px; } 
        .source-badge { display: inline-block; background: #1e293b; border: 1px solid #334155; color: #94a3b8; padding: 4px 12px; border-radius: 4px; font-family: 'Rajdhani', sans-serif; font-size: 13px; font-weight: 700; margin-bottom: 18px; }
        
        /* Tarjeta IA */
        .ia-card { background: #111827; border-left: 4px solid #eab308; padding: 20px; border-radius: 8px; margin-bottom: 25px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5); } 
        .ia-title { color: #eab308; font-family: 'Orbitron', sans-serif; font-size: 13px; font-weight: 800; margin-bottom: 10px; text-transform: uppercase; } 
        .ia-summary { color: #d1d5db; font-family: 'Rajdhani', sans-serif; font-size: 16px; font-weight: 500; line-height: 1.5; margin-bottom: 12px; } 
        .ia-alert { color: #fb7185; font-family: 'Rajdhani', sans-serif; font-size: 14px; font-weight: 600; margin-top: 6px; padding-left: 10px; border-left: 2px solid #fb7185; } 
        
        /* Tarjetas KPI sin neón, centradas y limpias */
        .kpi-card { background: #111827; padding: 18px 15px; border-radius: 8px; border: 1px solid #1f2937; border-top: 3px solid #3b82f6; display: flex; flex-direction: column; justify-content: center; min-height: 110px; }
        .kpi-title { font-family: 'Rajdhani', sans-serif; font-size: 12px; color: #9ca3af; font-weight: 700; text-transform: uppercase; line-height: 1.3; word-wrap: break-word; } 
        .kpi-val { font-family: 'Orbitron', sans-serif; font-size: 24px; color: #f3f4f6; font-weight: 800; margin-top: 6px; word-break: break-word; }
        
        /* Cajas de Gráficos */
        .chart-box { background: #111827; padding: 15px; border-radius: 8px; border: 1px solid #1f2937; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

def ejecutar(df_base, fuente_activa=None):
    inyectar_css()

    # ==========================================
    # 1. ESTADO VACÍO (WELCOME SCREEN CORPORATIVO)
    # ==========================================
    if df_base is None or df_base.empty:
        st.markdown("<div class='title-bar'>PANEL GERENCIAL DE OPERACIONES</div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='background: #111827; border-left: 4px solid #3b82f6; padding: 40px; border-radius: 8px; margin-top: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.5); text-align: center;'>
            <h2 style='color: #f3f4f6; font-family: Orbitron; margin-bottom: 15px;'>SISTEMA EN ESPERA DE DATOS</h2>
            <p style='color: #9ca3af; font-family: Rajdhani; font-size: 18px; line-height: 1.6;'>
                El Orquestador de Inteligencia Artificial está en línea.<br>
                <strong>Por favor, suba un archivo (Excel/CSV) en el panel lateral para iniciar el análisis automático.</strong>
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    # ==========================================
    # 2. EJECUCIÓN DEL AGENTE (CON DATOS)
    # ==========================================
    if "ultima_fuente" not in st.session_state or st.session_state["ultima_fuente"] != fuente_activa:
        st.session_state["ultima_fuente"] = fuente_activa
        st.cache_data.clear()

    with st.spinner("La IA está mapeando y estructurando la información..."):
        res = procesar_archivo(df_base)
        df_norm = res["df"]
        
        if df_norm.empty or len(df_norm.columns) == 0:
            st.error("⚠️ Archivo irreconocible o sin columnas numéricas válidas tras la limpieza.")
            st.stop()

        agente = AgenteOrquestador(df_norm)
        agente.planear_y_organizar()
        insights = agente.generar_insights()

    st.markdown(f"<div class='title-bar'>{insights.get('titulo', 'PANEL GERENCIAL').upper()}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='source-badge'>📁 {res['origen']}</div>", unsafe_allow_html=True)

    alerts = "".join([f"<div class='ia-alert'>⚠️ {alerta}</div>" for alerta in insights.get('alertas', [])])
    st.markdown(
        f"""
        <div class='ia-card'>
            <div class='ia-title'>🤖 DIAGNÓSTICO TÁCTICO IA</div>
            <div class='ia-summary'>{insights.get('resumen', '')}</div>
            <div>{alerts}</div>
        </div>
        """, 
        unsafe_allow_html=True
    )

    tab_dash, tab_datos = st.tabs(["🚀 DASHBOARD IA (MULTI-PANEL)", "🗄️ MATRIZ DE DATOS"])

    with tab_dash:
        if not agente.metricas:
            st.warning("La IA no detectó métricas numéricas graficables en este archivo.")
            st.stop()

        # TARJETAS KPI CON FORMATO INTELIGENTE Y ABREVIACIONES
        kpi_cols = st.columns(min(4, len(agente.metricas)))
        for i, col in enumerate(agente.metricas[:4]):
            val_sum = df_norm[col].sum()
            nombre_kpi = agente.mapeo_nombres.get(col, col)
            formato = format_kpi(val_sum, col)
            
            with kpi_cols[i]:
                st.markdown(f"<div class='kpi-card'><div class='kpi-title'>{nombre_kpi}</div><div class='kpi-val'>{formato}</div></div>", unsafe_allow_html=True)
        
        st.markdown("<br><hr style='border-color: #1f2937;'><br>", unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns([1.2, 0.8, 1.0, 1.0])
        eje_x = c1.selectbox("1. Dimensión Analítica (Eje X):", agente.dimensiones, format_func=lambda x: obtener_nombre_limpio(x))
        anio_sel = c2.selectbox("2. Año:", ["TODOS"] + agente.anios)

        col_semana = next((c for c in df_norm.columns if "semana" in c.lower()), None)
        df_filtrado = df_norm.copy()
        
        if col_semana:
            semanas = sorted([int(float(str(v))) for v in df_norm[col_semana].dropna().unique() if str(v).replace('.', '', 1).isdigit()])
            if not semanas: semanas = [1, 52]
            
            s_ini = c3.selectbox("3. Inicio (Secuencia):", semanas, index=0)
            s_fin = c4.selectbox("4. Fin (Secuencia):", semanas, index=len(semanas)-1)
            
            df_filtrado = df_filtrado[df_filtrado[col_semana].apply(lambda x: s_ini <= int(float(str(x))) <= s_fin if pd.notna(x) and str(x).replace('.','',1).isdigit() else True)]

        c_mod, c_met = st.columns([1.0, 2.0])
        modulo_sel = c_mod.selectbox("5. Módulo Gerencial:", ["TODOS"] + list(agente.modulos.keys()))
        
        opciones_disponibles = agente.metricas if modulo_sel == "TODOS" else agente.modulos[modulo_sel]
        if anio_sel != "TODOS":
            opciones_disponibles = [c for c in opciones_disponibles if anio_sel in c]

        metricas_sel = c_met.multiselect(
            "6. Métricas activas:", 
            options=opciones_disponibles, 
            default=opciones_disponibles[:min(4, len(opciones_disponibles))],
            format_func=lambda c: agente.mapeo_nombres.get(c, c)
        )

        st.markdown("<br>", unsafe_allow_html=True)

        if metricas_sel:
            for i in range(0, len(metricas_sel), 2):
                grid = st.columns(2)
                for j in range(2):
                    if i + j < len(metricas_sel):
                        m_col = metricas_sel[i+j]
                        alias = agente.mapeo_nombres.get(m_col, m_col)
                        
                        with grid[j]:
                            st.markdown("<div class='chart-box'>", unsafe_allow_html=True)
                            c_hdr, c_tipo = st.columns([1.5, 1.0])
                            
                            # Título con contexto (Ej: STOCK FÍSICO POR CATEGORÍA)
                            titulo_grafico = f"{alias} por {obtener_nombre_limpio(eje_x)}"
                            c_hdr.markdown(f"<span style='color:#9ca3af; font-family:Rajdhani; font-size:14px; font-weight:700; text-transform:uppercase;'>{titulo_grafico}</span>", unsafe_allow_html=True)
                            
                            # Sugerencia inteligente del gráfico
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
        st.markdown("<h4 style='color: #eab308; font-family: Orbitron;'>🗄️ BOVEDA DE DATOS</h4>", unsafe_allow_html=True)
        df_mostrar = df_norm.copy()
        for col in df_mostrar.columns:
            if "semana" in col.lower() or "cinta" in col.lower():
                df_mostrar[col] = df_mostrar[col].apply(lambda x: str(int(float(x))) if pd.notna(x) and str(x).replace('.','',1).isdigit() else str(x) if pd.notna(x) else "")
            elif df_mostrar[col].dtype == 'object':
                df_mostrar[col] = df_mostrar[col].fillna("")
                
        config = {col: st.column_config.NumberColumn(col, format="%.0f") for col in agente.metricas}
        st.dataframe(df_mostrar, column_config=config, use_container_width=True, hide_index=True, height=550)
