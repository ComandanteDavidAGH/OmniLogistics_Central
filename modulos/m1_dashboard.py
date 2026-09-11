"""
MOTOR UNIVERSAL INTELIGENTE DE DATOS B2B (ARQUITECTURA ESTABLE DEFINITIVA)
========================================================================
- Eje X: Exclusivamente variables categóricas (CINTA / SEMANA).
- KPIs: Títulos directos con Módulo + Métrica + Año.
- Filtro por Módulo: Aísla las métricas de la categoría activa para mantener nombres cortos en el Multiselect.
- Multi-Panel: Gráficos independientes por cuadrícula.
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
PALABRAS_MONEDA = ("precio", "costo", "valor", "ingreso", "venta", "presupuesto", "salario", "pago", "gasto", "monto", "usd", "cop")
PALABRAS_PORCENTAJE = ("%", "porcentaje", "pct", "cumplim", "participac", "tasa", "avance")
PALABRAS_CODIGO = ("id", "código", "codigo", "cod_", "nit", "documento", "referencia", "ref_")

PALETA_NEON = ["#06b6d4", "#38bdf8", "#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ec4899"]

def fmt_es(valor, decimales=0, prefijo="", sufijo=""):
    if pd.isna(valor) or valor == "":
        return "0"
    try:
        v = float(valor)
    except Exception:
        return str(valor)
    texto = f"{v:,.{decimales}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return f"{prefijo}{texto}{sufijo}"

def limpiar_semantica(texto):
    s = str(texto).strip()
    s = re.sub(r'\b20\d{2}(?:\s*-\s*20\d{2})+\b', '', s)
    s = s.replace('-', ' ').replace('_', ' ')
    s = " ".join(s.split())
    return s.title()

def obtener_nombre_limpio(col_completa):
    """Extrae un título legible y garantizado para KPIs y selectores."""
    if not col_completa or pd.isna(col_completa):
        return "Métrica Operativa"
    partes = [p.strip() for p in str(col_completa).split(" | ") if p.strip()]
    if not partes:
        return str(col_completa)
    if len(partes) >= 2:
        anio = partes[-1] if re.match(r'^\d{4}$', partes[-1]) else ""
        métrica = partes[-2] if anio and len(partes) >= 2 else partes[-1]
        modulo = partes[0] if len(partes) >= 3 else ""
        prefijo = f"{modulo} - " if modulo and modulo != métrica else ""
        return f"{prefijo}{métrica} ({anio})" if anio else f"{prefijo}{métrica}"
    return partes[0]

def cazador_de_encabezados(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    origen_etiqueta = "Archivo General"
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
        
        nombre_final = " | ".join(jerarquia) if jerarquia else f"Col_{col_idx}"
        nuevas_cols.append(nombre_final)

    df_final = df_search.iloc[data_idx:].copy()
    
    cols_unicas = []
    conteo = {}
    for col in nuevas_cols:
        col_str = str(col)
        if col_str in conteo:
            conteo[col_str] += 1
            cols_unicas.append(f"{col_str} ({conteo[col_str]})")
        else:
            conteo[col_str] = 0
            cols_unicas.append(col_str)
            
    df_final.columns = cols_unicas
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

def generar_diagnostico_ia(muestra_json, stats_json, columnas):
    if _GENAI_OK:
        try:
            api_key = st.secrets.get("GEMINI_API_KEY", "")
            if api_key:
                genai.configure(api_key=api_key)
                prompt = f"""
                Eres Genesis IA, analista logistico y agricola B2B.
                Columnas: {columnas}
                Muestra: {muestra_json}
                Resumen: {stats_json}
                Responde JSON:
                {{
                    "titulo_contextual": "PANEL GERENCIAL DE PRODUCCION BANANERA",
                    "resumen_gerencial": "Analisis tactico multivariable por Cinta y Semana de empaque.",
                    "cuellos_de_botella": ["Trazabilidad de racimos embolsados", "Rendimiento por hectarea y control de merma"]
                }}
                """
                model = genai.GenerativeModel("gemini-1.5-flash", generation_config={"response_mime_type": "application/json"})
                respuesta = model.generate_content(prompt).text.strip()
                if "```json" in respuesta:
                    respuesta = respuesta.split("```json")[1].split("```")[0].strip()
                return json.loads(respuesta)
        except Exception:
            pass
    
    return {
        "titulo_contextual": "PANEL GERENCIAL DE PRODUCCION Y EMPAQUE",
        "resumen_gerencial": "Trazabilidad operativa por Cinta y Semana consolidada exitosamente.",
        "cuellos_de_botella": [
            "Atencion: Monitorear el volumen de cajas por hectarea segun la cinta seleccionada.",
            "Recomendacion: Contrastar merma procesada en semanas criticas."
        ]
    }

def inyectar_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;800;900&family=Rajdhani:wght@500;600;700&display=swap');
        .main { background-color: #0b0f19; }
        .title-bar { color: #38bdf8; font-family: 'Orbitron', sans-serif; font-size: 24px; font-weight: 800; border-bottom: 2px solid #1e293b; padding-bottom: 12px; margin-bottom: 20px; } 
        .source-badge { display: inline-block; background: rgba(15, 23, 42, 0.8); border: 1px solid #38bdf8; color: #38bdf8; padding: 4px 12px; border-radius: 20px; font-family: 'Rajdhani', sans-serif; font-size: 13px; font-weight: 700; margin-bottom: 18px; }
        .ia-card { background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.8)); border-left: 5px solid #10b981; padding: 22px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); } 
        .ia-title { color: #10b981; font-family: 'Orbitron', sans-serif; font-size: 14px; font-weight: 800; margin-bottom: 10px; } 
        .ia-summary { color: #e2e8f0; font-family: 'Rajdhani', sans-serif; font-size: 17px; font-weight: 500; line-height: 1.5; margin-bottom: 12px; } 
        .ia-alert { color: #fb7185; font-family: 'Rajdhani', sans-serif; font-size: 15px; font-weight: 700; margin-top: 6px; padding-left: 10px; border-left: 3px solid #fb7185; } 
        .kpi-card { background: rgba(15, 23, 42, 0.85); padding: 16px; border-radius: 10px; border: 1px solid rgba(56, 189, 248, 0.2); border-top: 4px solid #38bdf8; min-height: 110px; }
        .kpi-title { font-family: 'Rajdhani', sans-serif; font-size: 13px; color: #38bdf8; font-weight: 700; text-transform: uppercase; line-height: 1.3; } 
        .kpi-val { font-family: 'Orbitron', sans-serif; font-size: 22px; color: #ffffff; font-weight: 800; margin-top: 8px; text-shadow: 0 0 10px rgba(56, 189, 248, 0.3); }
        .chart-box { background: rgba(15, 23, 42, 0.6); padding: 15px; border-radius: 12px; border: 1px solid #1e293b; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

def ejecutar(df_base, fuente_activa=None):
    inyectar_css()
    
    if "ultima_fuente" not in st.session_state or st.session_state["ultima_fuente"] != fuente_activa:
        st.session_state["ultima_fuente"] = fuente_activa
        st.cache_data.clear()

    with st.spinner("Construyendo Dashboard Multivariable..."):
        res = normalizar_datos(df_base)
        df_norm = res["df_norm"]
        origen_etiqueta = res["origen"]
        semantica = inferir_semantica(df_norm)

    try:
        stats_json = df_norm.describe().to_json()
    except Exception:
        stats_json = "{}"
        
    diagnostico = generar_diagnostico_ia(df_norm.head(3).to_json(date_format="iso"), stats_json, list(df_norm.columns))
    
    titulo = diagnostico.get("titulo_contextual", "SISTEMA OPERATIVO DE DATOS B2B")
    st.markdown(f"<div class='title-bar'>⚡ {titulo}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='source-badge'>📄 ORIGEN DE DATOS: {origen_etiqueta}</div>", unsafe_allow_html=True)

    alerts = "".join([f"<div class='ia-alert'>⚠️ {alerta}</div>" for alerta in diagnostico.get("cuellos_de_botella", [])])
    st.markdown(
        f"""
        <div class='ia-card'>
            <div class='ia-title'>🤖 DIAGNOSTICO TACTICO (GENESIS IA)</div>
            <div class='ia-summary'>{diagnostico.get('resumen_gerencial', '')}</div>
            <div>{alerts}</div>
        </div>
        """, 
        unsafe_allow_html=True
    )

    tab_dash, tab_datos = st.tabs(["🚀 COMMAND CENTER (DASHBOARD)", "🗄️ BOVEDA DE DATOS NORMALIZADA"])

    with tab_dash:
        # Validación de seguridad contra DataFrames vacíos o sin columnas
        if df_norm.empty or len(df_norm.columns) == 0:
            st.warning("⚠️ No se detectaron columnas con información procesable en el archivo cargado. Verifica el formato del Excel.")
            st.stop()

        cols_num = [c for c, t in semantica.items() if t in ("cantidad", "moneda", "porcentaje")]
        
        # EJE X RESTREÑIDO EXCLUSIVAMENTE A VARIABLES CATEGÓRICAS / DIMENSIONES
        cols_eje_x = [c for c in df_norm.columns if any(p in c.lower() for p in ("semana", "cinta")) or semantica.get(c) in ("categoria", "texto")]
        if not cols_eje_x:
            cols_eje_x = [c for c in df_norm.columns if c not in cols_num]
        if not cols_eje_x:
            cols_eje_x = list(df_norm.columns[:1])  # Asignación segura de lista sin IndexError

        # TARJETAS KPIS: EXCLUIR COLUMNAS DE SEMANA/CINTA
        kpi_metrics = [c for c in cols_num if not any(p in c.lower() for p in ("semana", "cinta", "codigo", "id", "nit"))]
        if not kpi_metrics:
            kpi_metrics = cols_num

        if not cols_num:
            st.warning("No se detectaron variables numéricas para generar analítica.")
        else:
            # 1. TARJETAS KPI SUPERIORES CON TÍTULOS BLINDADOS Y VISIBLES
            kpi_cols = st.columns(min(4, len(kpi_metrics)))
            for i, col in enumerate(kpi_metrics[:4]):
                val_total = df_norm[col].sum()
                formato = f"${fmt_es(val_total)}" if semantica[col] == "moneda" else fmt_es(val_total, 0)
                nombre_kpi = obtener_nombre_limpio(col)
                
                with kpi_cols[i]:
                    st.markdown(
                        f"""
                        <div class='kpi-card'>
                            <div class='kpi-title'>{nombre_kpi}</div>
                            <div class='kpi-val'>{formato}</div>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
            
            st.markdown("<br><hr style='border-color: #1e293b;'><br>", unsafe_allow_html=True)

            # 2. CONTROLES DEL DASHBOARD (FILTROS NO BLOQUEANTES CON OPCIÓN 'TODOS')
            col_semana = next((c for c in df_norm.columns if "semana" in c.lower()), None)
            semanas_validas = []
            if col_semana:
                for v in df_norm[col_semana].dropna().unique():
                    try:
                        val_num = int(float(str(v).strip()))
                        semanas_validas.append(val_num)
                    except ValueError:
                        pass
            
            semanas_validas = sorted(list(set(semanas_validas)))
            if not semanas_validas:
                semanas_validas = [1, 52]

            anios_detectados = sorted(list(set(re.findall(r'\b20\d{2}\b', " ".join(df_norm.columns)))))

            c_eje, c_anio, c_s_ini, c_s_fin = st.columns([1.2, 0.8, 1.0, 1.0])
            
            def formato_nombre_eje(c):
                partes = str(c).split(" | ")
                return partes[-1] if partes else str(c)

            eje_seleccionado = c_eje.selectbox("1. Agrupar Eje X:", cols_eje_x, format_func=formato_nombre_eje)
            anio_sel = c_anio.selectbox("2. Año Operativo:", ["TODOS"] + anios_detectados if anios_detectados else ["TODOS"])
            sem_inicial = c_s_ini.selectbox("3. Semana Inicial:", semanas_validas, index=0)
            sem_final = c_s_fin.selectbox("4. Semana Final:", semanas_validas, index=len(semanas_validas)-1)

            # FILTRADO DE DATOS POR RANGO DE SEMANAS
            df_filtrado = df_norm.copy()
            if col_semana and col_semana in df_filtrado.columns:
                def dentro_rango(val):
                    try:
                        num = int(float(str(val).strip()))
                        return sem_inicial <= num <= sem_final
                    except ValueError:
                        return True
                df_filtrado = df_filtrado[df_filtrado[col_semana].apply(dentro_rango)]

            # 3. FILTRADO LIBRE DE MÉTRICAS (SIN BLOQUEOS RIGIDOS)
            arbol_modulos = {"TODAS LAS SECCIONES": cols_num}
            for col in cols_num:
                partes = [p.strip() for p in col.split(" | ")]
                modulo = partes[0] if len(partes) > 1 else "General"
                if modulo not in arbol_modulos:
                    arbol_modulos[modulo] = []
                arbol_modulos[modulo].append(col)

            c_mod, c_multi = st.columns([1.0, 2.0])
            modulo_activo = c_mod.selectbox("5. Sección / Módulo:", list(arbol_modulos.keys()))
            
            opciones_disponibles = arbol_modulos.get(modulo_activo, cols_num)
            if anio_sel != "TODOS":
                opciones_filtradas_anio = [c for c in opciones_disponibles if anio_sel in c]
                if opciones_filtradas_anio:
                    opciones_disponibles = opciones_filtradas_anio

            metricas_seleccionadas = c_multi.multiselect(
                "6. Métricas activas a graficar:",
                options=opciones_disponibles,
                default=opciones_disponibles[:min(4, len(opciones_disponibles))],
                format_func=obtener_nombre_limpio
            )

            st.markdown("<br>", unsafe_allow_html=True)

            # 4. RENDERIZADO DEL DASHBOARD MULTI-PANEL
            if not metricas_seleccionadas:
                st.info("Selecciona al menos una métrica para proyectar el panel.")
            else:
                for i in range(0, len(metricas_seleccionadas), 2):
                    cols_grid = st.columns(2)
                    
                    for j in range(2):
                        if i + j < len(metricas_seleccionadas):
                            metric_col = metricas_seleccionadas[i+j]
                            nombre_limpio = obtener_nombre_limpio(metric_col)
                            
                            with cols_grid[j]:
                                st.markdown("<div class='chart-box'>", unsafe_allow_html=True)
                                
                                c_hdr, c_sel_tipo = st.columns([1.4, 1.0])
                                c_hdr.markdown(f"<span style='color:#38bdf8; font-family:Orbitron; font-size:12px; font-weight:800;'>{nombre_limpio.upper()}</span>", unsafe_allow_html=True)
                                
                                default_estilo = "Dona (Distribución)" if "cinta" in eje_seleccionado.lower() else "Barras (Comparación)"
                                estilo_chart = c_sel_tipo.selectbox(
                                    "Tipo de Gráfico:",
                                    ["Barras (Comparación)", "Líneas (Tendencia)", "Área (Acumulado)", "Dona (Distribución)"],
                                    index=["Barras (Comparación)", "Líneas (Tendencia)", "Área (Acumulado)", "Dona (Distribución)"].index(default_estilo),
                                    key=f"chart_type_{i}_{j}_{metric_col}",
                                    label_visibility="collapsed"
                                )
                                
                                df_g = df_filtrado.groupby(eje_seleccionado)[metric_col].sum().reset_index(name='Valor')
                                
                                df_g[eje_seleccionado] = df_g[eje_seleccionado].apply(
                                    lambda x: str(int(float(x))) if pd.notna(x) and str(x).replace('.','',1).isdigit() else str(x) if pd.notna(x) else ""
                                )
                                
                                def clave_orden(x):
                                    try: return int(x)
                                    except Exception: return str(x)
                                        
                                df_g['Orden'] = df_g[eje_seleccionado].apply(clave_orden)
                                df_g = df_g.sort_values('Orden').drop(columns=['Orden'])

                                unidad_fmt = "$" if semantica.get(metric_col) == "moneda" else ""
                                label_eje = eje_seleccionado.split(" | ")[-1] if " | " in eje_seleccionado else eje_seleccionado

                                if "Dona" in estilo_chart:
                                    fig = px.pie(df_g, names=eje_seleccionado, values='Valor', hole=0.45, template="plotly_dark", color_discrete_sequence=PALETA_NEON)
                                    fig.update_traces(textinfo="label+percent", hovertemplate=f"<b>%{{label}}:</b> {unidad_fmt}%{{value:,.0f}}<extra></extra>")
                                elif "Líneas" in estilo_chart:
                                    fig = px.line(df_g, x=eje_seleccionado, y='Valor', text='Valor', markers=True, template="plotly_dark")
                                    fig.update_traces(texttemplate=f"{unidad_fmt}%{{text:,.0f}}", textposition="top center", line=dict(width=3, color="#06b6d4"), marker=dict(size=8, color="#38bdf8"), hovertemplate=f"<b>{eje_seleccionado}:</b> %{{x}}<br><b>Valor:</b> {unidad_fmt}%{{y:,.0f}}<extra></extra>")
                                elif "Área" in estilo_chart:
                                    fig = px.area(df_g, x=eje_seleccionado, y='Valor', text='Valor', template="plotly_dark")
                                    fig.update_traces(texttemplate=f"{unidad_fmt}%{{text:,.0f}}", textposition="top center", fillcolor="rgba(6, 182, 212, 0.3)", line=dict(width=2, color="#06b6d4"), hovertemplate=f"<b>{eje_seleccionado}:</b> %{{x}}<br><b>Valor:</b> {unidad_fmt}%{{y:,.0f}}<extra></extra>")
                                else:
                                    fig = px.bar(df_g, x=eje_seleccionado, y='Valor', text='Valor', template="plotly_dark", color='Valor', color_continuous_scale="Electric")
                                    fig.update_traces(texttemplate=f"{unidad_fmt}%{{text:,.0f}}", textposition="outside", cliponaxis=False, hovertemplate=f"<b>{eje_seleccionado}:</b> %{{x}}<br><b>Valor:</b> {unidad_fmt}%{{y:,.0f}}<extra></extra>", marker_line_color="#06b6d4", marker_line_width=1.5, opacity=0.9)

                                fig.update_layout(
                                    paper_bgcolor='rgba(11, 15, 25, 0)',
                                    plot_bgcolor='rgba(15, 23, 42, 0.5)',
                                    xaxis=dict(title=dict(text=label_eje, font=dict(color='#94a3b8')), tickfont=dict(color='#cbd5e1'), type='category'),
                                    yaxis=dict(title=dict(text="Volumen", font=dict(color='#94a3b8')), tickfont=dict(color='#cbd5e1')),
                                    coloraxis_showscale=False,
                                    margin=dict(l=10, r=10, t=20, b=30),
                                    height=340
                                )

                                st.plotly_chart(fig, use_container_width=True)
                                st.markdown("</div>", unsafe_allow_html=True)

    with tab_datos:
        st.markdown("<h4 style='color: #38bdf8; font-family: Orbitron;'>🗄️ BOVEDA DE DATOS NORMALIZADA</h4>", unsafe_allow_html=True)
        df_mostrar = df_norm.copy()
        
        for col in df_mostrar.columns:
            if "semana" in col.lower() or "cinta" in col.lower():
                df_mostrar[col] = df_mostrar[col].apply(
                    lambda x: str(int(float(x))) if pd.notna(x) and str(x).replace('.','',1).isdigit() else str(x) if pd.notna(x) else ""
                )
            elif df_mostrar[col].dtype == 'object':
                df_mostrar[col] = df_mostrar[col].fillna("")
        
        config = {}
        for col in df_mostrar.columns:
            if semantica.get(col) == "moneda":
                config[col] = st.column_config.NumberColumn(col, format="$ %.2f")
            elif semantica.get(col) == "porcentaje":
                config[col] = st.column_config.NumberColumn(col, format="%.2f%%")
            elif semantica.get(col) == "cantidad":
                config[col] = st.column_config.NumberColumn(col, format="%.0f")
        
        st.dataframe(df_mostrar, column_config=config, use_container_width=True, hide_index=True, height=550)
