"""
MOTOR B2B (ARQUITECTURA UNIVERSAL - DASHBOARD Y MATRIZ)
========================================================================
- 100% Agnóstico: No hay reglas duras para negocios específicos.
- Dashboard Dinámico: Detecta dimensiones (textos) y métricas (números).
- KPIs en Tiempo Real: Sumarización automática de las variables elegidas.
"""
import re
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
from typing import Tuple

VALORES_NULOS = {"none", "nan", "nat", "null", "n/a", "#n/a", "-", "--", ""}
PALETA_CORP = ["#eab308", "#3b82f6", "#10b981", "#6366f1", "#f43f5e", "#8b5cf6"]

def format_latam(valor):
    """Convierte número a formato LATAM visual (1.234,56)."""
    if pd.isna(valor) or valor == "": return ""
    try:
        v = float(valor)
        if v.is_integer(): return f"{int(v):,}".replace(",", ".")
        else: return f"{v:,.2f}".replace(",", "§").replace(".", ",").replace("§", ".")
    except Exception:
        return str(valor)

def format_kpi(val):
    """Abreviación gerencial (M/B) para las tarjetas KPI."""
    if pd.isna(val) or val == "": return "0"
    try: v = float(val)
    except: return str(val)

    if abs(v) >= 1_000_000_000: return f"{v/1_000_000_000:,.2f} B".replace(",", "§").replace(".", ",").replace("§", ".")
    elif abs(v) >= 1_000_000: return f"{v/1_000_000:,.2f} M".replace(",", "§").replace(".", ",").replace("§", ".")
    else: return f"{v:,.0f}".replace(",", "§").replace(".", ",").replace("§", ".")

def ui_nombre_limpio(col_html):
    """Convierte el título piramidal HTML en texto lineal para selectores."""
    texto = str(col_html).replace("<br>", " ➔ ").replace("&nbsp;", "")
    return texto.strip()

def extractor_logico_estricto(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    origen = "Archivo Base"
    if "_Origen_Archivo" in df_raw.columns:
        origen = str(df_raw["_Origen_Archivo"].dropna().iloc[0]) if not df_raw["_Origen_Archivo"].dropna().empty else origen
        df_raw = df_raw.drop(columns=["_Origen_Archivo"])

    fila_eje = 0
    for i in range(min(20, len(df_raw))):
        text_row = " ".join([str(x).lower() for x in df_raw.iloc[i] if pd.notna(x)])
        # Palabras comunes de cruce, pero aplica para cualquier matriz
        if any(w in text_row for w in ['semana', 'cinta', 'categoría', 'producto', 'fecha', 'código', 'id', 'cliente']):
            fila_eje = i
            break

    fin_encabezados = fila_eje
    if fila_eje + 1 < len(df_raw):
        vals = [str(x).replace('.0','') for x in df_raw.iloc[fila_eje + 1] if pd.notna(x)]
        if sum(1 for x in vals if x.isdigit() and len(x) == 4) >= 2:
            fin_encabezados = fila_eje + 1

    ecuador_datos = fin_encabezados + 1

    inicio_encabezados = max(0, fila_eje - 1) 
    df_headers = df_raw.iloc[inicio_encabezados:fin_encabezados + 1].copy().astype(object)
    
    df_headers = df_headers.ffill(axis=0).ffill(axis=1)

    nuevas_cols = []
    for col_idx in range(len(df_headers.columns)):
        jerarquia = []
        for f_idx in range(len(df_headers)):
            val = df_headers.iloc[f_idx, col_idx]
            if pd.notna(val) and str(val).strip() != "" and str(val).lower() != 'nan':
                texto = str(val).replace('.0', '').strip()
                texto = re.sub(r'\b20\d{2}(?:\s*-\s*20\d{2})+\b', '', texto).strip('- ')
                if len(texto) > 30 and "año" in texto.lower(): continue 
                
                texto_format = " ".join(texto.split()).title() if not texto.isdigit() else " ".join(texto.split())
                if texto_format:
                    if not jerarquia or jerarquia[-1].lower() != texto_format.lower():
                        jerarquia.append(texto_format)
        
        if not jerarquia: jerarquia = [f"⚠️ Fuga_Col_{col_idx}"]
        elif len(jerarquia) > 4: jerarquia[0] = "⚠️ " + jerarquia[0]
            
        nombre_final = "<br>".join(jerarquia)
        nuevas_cols.append(nombre_final)

    df_datos = df_raw.iloc[ecuador_datos:].copy()
    
    cols_unicas, conteo = [], {}
    for col in nuevas_cols:
        if col in conteo:
            conteo[col] += 1
            cols_unicas.append(f"{col}{'&nbsp;' * conteo[col]}")
        else:
            conteo[col] = 0
            cols_unicas.append(col)
            
    df_datos.columns = cols_unicas
    
    mask = pd.Series([True] * len(df_datos), index=df_datos.index)
    if not df_datos.empty and len(df_datos.columns) > 0:
        for col in df_datos.columns[:3]:
            if df_datos[col].dtype == 'object':
                filtro = df_datos[col].astype(str).str.lower().str.contains(r'total|promedio|acumulado|año\b|ano\b|sem\b|sem\d', regex=True, na=False)
                mask = mask & (~filtro)
                
    df_datos = df_datos[mask].reset_index(drop=True).dropna(how='all', axis=0)

    for col in df_datos.columns:
        df_datos[col] = df_datos[col].map(lambda v: np.nan if str(v).lower().strip() in VALORES_NULOS else v)
        serie_str = df_datos[col].dropna().astype(str).str.replace(r"[$\s%]", "", regex=True).str.replace(",", ".")
        num = pd.to_numeric(serie_str, errors="coerce")
        if num.notna().sum() / max(len(serie_str), 1) > 0.5: df_datos[col] = num

    return df_datos, origen

def generar_tabla_html_piramidal(df: pd.DataFrame, columnas_fijas: int = 0) -> str:
    html = """
    <div style="overflow: auto; max-height: 60vh; border: 1px solid #1f2937; border-radius: 8px; margin-bottom: 20px; position: relative;">
        <table style="width: 100%; border-collapse: collapse; font-family: 'Rajdhani', sans-serif; background-color: #0b1120; color: #f3f4f6; text-align: center; font-size: 14px;">
            <thead style="background-color: #1e293b; position: sticky; top: 0; z-index: 10;">
                <tr>
    """
    ancho_fijo = 120 
    for i, col in enumerate(df.columns):
        if i < columnas_fijas:
            left_pos = i * ancho_fijo
            sombra = "box-shadow: 3px 0 5px -2px rgba(0,0,0,0.6);" if i == columnas_fijas - 1 else ""
            estilo = f"position: sticky; left: {left_pos}px; min-width: {ancho_fijo}px; max-width: {ancho_fijo}px; background-color: #1e293b; z-index: 11; {sombra}"
        else:
            estilo = "z-index: 9;"
            
        if "⚠️" in col: estilo += " color: #f43f5e;"
        html += f"<th style='padding: 12px 15px; border: 1px solid #334155; color: #eab308; font-weight: 700; white-space: nowrap; vertical-align: bottom; {estilo}'>{col}</th>"
    
    html += "</tr></thead><tbody>"
    for _, row in df.iterrows():
        html += "<tr style='border-bottom: 1px solid #1f2937;'>"
        for i, col in enumerate(df.columns):
            val = row[col]
            val_str = "" if pd.isna(val) or val == "" else (format_latam(val) if isinstance(val, (int, float)) else str(val))
            
            if i < columnas_fijas:
                left_pos = i * ancho_fijo
                sombra = "box-shadow: 3px 0 5px -2px rgba(0,0,0,0.6);" if i == columnas_fijas - 1 else ""
                estilo = f"position: sticky; left: {left_pos}px; min-width: {ancho_fijo}px; max-width: {ancho_fijo}px; background-color: #0f172a; font-weight: 600; color: #38bdf8; z-index: 5; {sombra}"
            else:
                estilo = ""
            html += f"<td style='padding: 10px 15px; border-right: 1px solid #1f2937; white-space: nowrap; {estilo}'>{val_str}</td>"
        html += "</tr>"
    html += "</tbody></table></div>"
    return html

def inyectar_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;800;900&family=Rajdhani:wght@500;600;700&display=swap');
        .main { background-color: #0b1120; }
        .title-bar { color: #eab308; font-family: 'Orbitron', sans-serif; font-size: 22px; font-weight: 800; border-bottom: 1px solid #1e293b; padding-bottom: 12px; margin-bottom: 20px; letter-spacing: 1px; } 
        .source-badge { display: inline-block; background: #1e293b; border: 1px solid #334155; color: #94a3b8; padding: 4px 12px; border-radius: 4px; font-family: 'Rajdhani', sans-serif; font-size: 13px; font-weight: 700; margin-bottom: 18px; }
        .kpi-card { background: #111827; padding: 18px 15px; border-radius: 8px; border: 1px solid #1f2937; border-top: 3px solid #3b82f6; display: flex; flex-direction: column; justify-content: center; min-height: 100px; margin-bottom: 15px; }
        .kpi-title { font-family: 'Rajdhani', sans-serif; font-size: 13px; color: #9ca3af; font-weight: 700; text-transform: uppercase; line-height: 1.3; } 
        .kpi-val { font-family: 'Orbitron', sans-serif; font-size: 24px; color: #f3f4f6; font-weight: 800; margin-top: 6px; }
        .chart-box { background: #111827; padding: 20px; border-radius: 10px; border: 1px solid #1f2937; margin-bottom: 25px; }
        .chart-header { background-color: #1e293b; padding: 10px 15px; border-radius: 6px; margin-bottom: 15px; display: inline-block; border-left: 4px solid #eab308; }
        .chart-title { color:#eab308; font-family: 'Orbitron', sans-serif; font-size: 14px; font-weight: 800; letter-spacing: 0.5px; margin: 0; }
    </style>
    """, unsafe_allow_html=True)

def ejecutar(df_base, fuente_activa=None):
    inyectar_css()

    if df_base is None or df_base.empty:
        st.markdown("<div class='title-bar'>SISTEMA OPERATIVO OMNILOGISTICS</div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='background: #111827; border-left: 4px solid #3b82f6; padding: 40px; border-radius: 8px; margin-top: 20px; text-align: center;'>
            <h2 style='color: #f3f4f6; font-family: Orbitron; margin-bottom: 15px;'>EN ESPERA DE DATOS</h2>
            <p style='color: #9ca3af; font-family: Rajdhani; font-size: 18px; line-height: 1.6;'>
                Sube cualquier matriz (Excel/CSV). El sistema detectará las dimensiones automáticamente.
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    if "ultima_fuente" not in st.session_state or st.session_state["ultima_fuente"] != fuente_activa:
        st.session_state["ultima_fuente"] = fuente_activa
        st.cache_data.clear()

    with st.spinner("Procesando matriz universal..."):
        df_norm, origen = extractor_logico_estricto(df_base)
        if df_norm.empty:
            st.error("⚠️ El archivo quedó vacío tras la limpieza estructural.")
            st.stop()

        # SEPARACIÓN UNIVERSAL: Categóricas (Textos) vs Numéricas (Métricas)
        cols_num = [c for c in df_norm.columns if pd.api.types.is_numeric_dtype(df_norm[c].dropna())]
        cols_cat = [c for c in df_norm.columns if c not in cols_num]
        
        # Cualquier columna categórica puede ser un Eje X, pero priorizamos la primera
        opciones_eje_x = cols_cat if cols_cat else cols_num[:1]

    st.markdown("<div class='title-bar'>CENTRO DE MANDO E INTELIGENCIA</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='source-badge'>📁 ARCHIVO ACTIVO: {origen}</div>", unsafe_allow_html=True)

    tab_dash, tab_datos = st.tabs(["🚀 DASHBOARD ANALÍTICO", "🗄️ BÓVEDA DE DATOS (MATRIZ)"])

    with tab_dash:
        if not cols_num:
            st.warning("⚠️ No se detectaron columnas con valores numéricos para graficar.")
        else:
            st.markdown("<h4 style='color: #38bdf8; font-family: Orbitron; font-size: 16px;'>⚙️ CONSTRUCTOR DEL LIENZO</h4>", unsafe_allow_html=True)
            
            # FILA DE CONTROLES UNIVERSALES
            c1, c2 = st.columns([1, 2])
            
            # Eje X (Dimensión)
            eje_x = c1.selectbox("1. Agrupar datos por (Eje X):", options=opciones_eje_x, format_func=ui_nombre_limpio)
            
            # Eje Y (Múltiples Métricas)
            metricas_sel = c2.multiselect("2. Seleccionar Métricas a Visualizar (Eje Y):", options=cols_num, default=[], format_func=ui_nombre_limpio)

            st.markdown("<hr style='border-color: #1f2937;'>", unsafe_allow_html=True)

            if not metricas_sel:
                st.info("📌 El lienzo está en blanco. Seleccione una o más métricas en el paso 2 para generar los gráficos y KPIs.")
            else:
                # ---------------------------------------------------------
                # RENDERIZADO DE KPIs DINÁMICOS
                # ---------------------------------------------------------
                kpi_cols = st.columns(min(len(metricas_sel), 4))
                for i, m_col in enumerate(metricas_sel[:4]): # Máximo 4 KPIs en la primera fila
                    total_val = df_norm[m_col].sum()
                    nombre_kpi = ui_nombre_limpio(m_col)
                    formato_val = format_kpi(total_val)
                    with kpi_cols[i]:
                        st.markdown(f"""
                        <div class='kpi-card'>
                            <div class='kpi-title'>{nombre_kpi}</div>
                            <div class='kpi-val'>{formato_val}</div>
                        </div>
                        """, unsafe_allow_html=True)

                # ---------------------------------------------------------
                # RENDERIZADO DE GRÁFICOS DINÁMICOS
                # ---------------------------------------------------------
                for i in range(0, len(metricas_sel), 2):
                    grid = st.columns(2)
                    for j in range(2):
                        if i + j < len(metricas_sel):
                            m_col = metricas_sel[i+j]
                            alias = ui_nombre_limpio(m_col)
                            
                            with grid[j]:
                                st.markdown("<div class='chart-box'>", unsafe_allow_html=True)
                                c_hdr, c_tipo = st.columns([1.5, 1.0])
                                c_hdr.markdown(f"<div class='chart-header'><p class='chart-title'>{alias.upper()}</p></div>", unsafe_allow_html=True)
                                
                                tipo_grafico = c_tipo.selectbox("Tipo:", ["Barras", "Líneas", "Área", "Dona"], key=f"g_{m_col}", label_visibility="collapsed")
                                
                                # Agrupación universal de datos
                                df_g = df_norm.groupby(eje_x)[m_col].sum().reset_index(name='Valor')
                                # Asegurar que el Eje X se ordene lógicamente si son números camuflados de texto (Ej. Semanas 1, 2, 3...)
                                df_g['Orden'] = df_g[eje_x].apply(lambda x: float(x) if str(x).replace('.','').isdigit() else str(x))
                                df_g = df_g.sort_values('Orden').drop(columns=['Orden'])

                                if tipo_grafico == "Dona":
                                    fig = px.pie(df_g, names=eje_x, values='Valor', hole=0.45, template="plotly_dark", color_discrete_sequence=PALETA_CORP)
                                    fig.update_traces(textinfo="label+percent")
                                elif tipo_grafico == "Líneas":
                                    fig = px.line(df_g, x=eje_x, y='Valor', text='Valor', markers=True, template="plotly_dark")
                                    fig.update_traces(texttemplate="%{text:,.2s}", textposition="top center", line=dict(width=3, color="#3b82f6"), marker=dict(size=8, color="#eab308"))
                                elif tipo_grafico == "Área":
                                    fig = px.area(df_g, x=eje_x, y='Valor', text='Valor', template="plotly_dark")
                                    fig.update_traces(texttemplate="%{text:,.2s}", textposition="top center", fillcolor="rgba(59, 130, 246, 0.2)", line=dict(width=2, color="#3b82f6"))
                                else:
                                    fig = px.bar(df_g, x=eje_x, y='Valor', text='Valor', template="plotly_dark", color_discrete_sequence=[PALETA_CORP[0]])
                                    fig.update_traces(texttemplate="%{text:,.2s}", textposition="outside", cliponaxis=False, marker_line_color="#1e293b", marker_line_width=1)

                                fig.update_layout(
                                    paper_bgcolor='rgba(11, 15, 25, 0)', plot_bgcolor='rgba(11, 15, 25, 0)',
                                    xaxis=dict(title=dict(text="", font=dict(color='#94a3b8')), tickfont=dict(color='#9ca3af'), type='category'),
                                    yaxis=dict(title=dict(text="", font=dict(color='#94a3b8')), tickfont=dict(color='#9ca3af'), showgrid=True, gridcolor='#1f2937'),
                                    coloraxis_showscale=False, margin=dict(l=10, r=10, t=20, b=30), height=350
                                )

                                st.plotly_chart(fig, use_container_width=True)
                                st.markdown("</div>", unsafe_allow_html=True)

    with tab_datos:
        st.markdown("<h4 style='color: #38bdf8; font-family: Orbitron; font-size: 16px;'>⚙️ CONTROLES DE VISTA</h4>", unsafe_allow_html=True)
        c_freeze, c_num, _ = st.columns([1, 1, 2])
        activar_inmovilizacion = c_freeze.toggle("📌 Inmovilizar Columnas")
        
        columnas_a_congelar = 0
        if activar_inmovilizacion:
            columnas_a_congelar = c_num.selectbox("Cantidad a fijar:", range(1, 6), label_visibility="collapsed")
        
        st.markdown("<br>", unsafe_allow_html=True)

        tabla_html = generar_tabla_html_piramidal(df_norm, columnas_fijas=columnas_a_congelar)
        st.markdown(tabla_html, unsafe_allow_html=True)
