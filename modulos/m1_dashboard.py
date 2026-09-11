"""
MOTOR UNIVERSAL INTELIGENTE DE DATOS (ARBOLESCENCIA DE 4 NIVELES)
================================================================
Navegación Dinámica: Segmento Principal ➔ Padre ➔ Hijo (Condición) ➔ Año
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

def fmt_es(valor, decimales=2, prefijo="", sufijo=""):
    if pd.isna(valor) or valor == "": return ""
    try: v = float(valor)
    except Exception: return str(valor)
    texto = f"{v:,.{decimales}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    return f"{prefijo}{texto}{sufijo}"

def decimales_sugeridos(serie: pd.Series):
    serie_valida = serie.dropna()
    if serie_valida.empty: return 0
    if np.allclose(serie_valida % 1, 0, atol=1e-9): return 0
    return 2

def limpiar_semantica(texto):
    s = str(texto).strip()
    s = re.sub(r'\b20\d{2}(?:\s*-\s*20\d{2})+\b', '', s)
    s = s.replace('-', ' ').replace('_', ' ')
    s = " ".join(s.split())
    return s.title()

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
        
        nombre_final = " | ".join(jerarquia) if jerarquia else f"Métrica_{col_idx}"
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
            
    return {"df_norm": df, "origen": etiqueta_origen}

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

def generar_diagnostico_ia(muestra_json, stats_json, columnas):
    if _GENAI_OK:
        try:
            api_key = st.secrets.get("GEMINI_API_KEY", "")
            if api_key:
                genai.configure(api_key=api_key)
                prompt = f"""
                Eres Génesis IA, motor analítico B2B.
                Analiza esta estructura:
                Columnas: {columnas}
                Muestra: {muestra_json}
                Resumen: {stats_json}
                
                Responde en JSON:
                {{
                    "titulo_contextual": "AUDITORÍA TÁCTICA DE PRODUCCIÓN",
                    "resumen_gerencial": "Evaluación gerencial en 2 oraciones.",
                    "cuellos_de_botella": ["Alerta o variabilidad 1", "Recomendación 2"]
                }}
                """
                model = genai.GenerativeModel("gemini-1.5-flash", generation_config={"response_mime_type": "application/json"})
                respuesta = model.generate_content(prompt).text.strip()
                if "```json" in respuesta: respuesta = respuesta.split("```json")[1].split("```")[0].strip()
                return json.loads(respuesta)
        except Exception: pass
    
    return {
        "titulo_contextual": "DIAGNÓSTICO TÁCTICO DE OPERACIONES",
        "resumen_gerencial": "Estructura jerárquica procesada con éxito. Matriz consolidada por segmentos, módulos y condiciones anuales.",
        "cuellos_de_botella": [
            "Atención: Monitorear variaciones en el volumen de semanas críticas.",
            "Recomendación: Comparar rendimientos por hectárea entre ciclos históricos."
        ]
    }

def inyectar_css():
    st.markdown('''
    <style>
        @import url('[https://fonts.googleapis.com/css2?family=Orbitron:wght@500;800;900&family=Rajdhani:wght@500;600;700&display=swap](https://fonts.googleapis.com/css2?family=Orbitron:wght@500;800;900&family=Rajdhani:wght@500;600;700&display=swap)');
        .main { background-color: #0b0f19; }
        .title-bar { color: #38bdf8; font-family: 'Orbitron', sans-serif; font-size: 24px; font-weight: 800; border-bottom: 2px solid #1e293b; padding-bottom: 12px; margin-bottom: 20px; } 
        .source-badge { display: inline-block; background: rgba(15, 23, 42, 0.8); border: 1px solid #38bdf8; color: #38bdf8; padding: 4px 12px; border-radius: 20px; font-family: 'Rajdhani', sans-serif; font-size: 13px; font-weight: 700; margin-bottom: 18px; }
        .ia-card { background: linear-gradient(135deg, rgba(15, 23, 42, 0.95), rgba(30, 41, 59, 0.8)); border-left: 5px solid #10b981; padding: 22px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); } 
        .ia-title { color: #10b981; font-family: 'Orbitron', sans-serif; font-size: 14px; font-weight: 800; margin-bottom: 10px; } 
        .ia-summary { color: #e2e8f0; font-family: 'Rajdhani', sans-serif; font-size: 17px; font-weight: 500; line-height: 1.5; margin-bottom: 12px; } 
        .ia-alert { color: #fb7185; font-family: 'Rajdhani', sans-serif; font-size: 15px; font-weight: 700; margin-top: 6px; padding-left: 10px; border-left: 3px solid #fb7185; } 
        .kpi-card { background: rgba(15, 23, 42, 0.75); padding: 18px; border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.08); border-top: 3px solid #06b6d4; }
        .kpi-title { font-family: 'Rajdhani', sans-serif; font-size: 13px; color: #94a3b8; font-weight: 700; text-transform: uppercase; } 
        .kpi-val { font-family: 'Orbitron', sans-serif; font-size: 22px; color: #f8fafc; font-weight: 800; margin-top: 6px; }
    </style>
    ''', unsafe_allow_html=True)

def ejecutar(df_base, fuente_activa=None):
    inyectar_css()
    
    with st.spinner("Decodificando topografía y sincronizando Inteligencia artificial..."):
        res = normalizar_datos(df_base)
        df_norm = res["df_norm"]
        origen_etiqueta = res["origen"]
        semantica = inferir_semantica(df_norm)

    try: stats_json = df_norm.describe().to_json()
    except Exception: stats_json = "{}"
        
    diagnostico = generar_diagnostico_ia(df_norm.head(3).to_json(date_format="iso"), stats_json, list(df_norm.columns))
    
    titulo = diagnostico.get("titulo_contextual", "SISTEMA OPERATIVO DE DATOS B2B")
    st.markdown(f"<div class='title-bar'>⚡ {titulo}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='source-badge'>📄 ORIGEN DE DATOS: {origen_etiqueta}</div>", unsafe_allow_html=True)

    alerts = "".join([f"<div class='ia-alert'>⚠️ {alerta}</div>" for alerta in diagnostico.get("cuellos_de_botella", [])])
    st.markdown(
        f"""
        <div class='ia-card'>
            <div class='ia-title'>🤖 DIAGNÓSTICO TÁCTICO (GÉNESIS IA)</div>
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
            st.warning("No se detectaron variables numéricas para generar analítica.")
        else:
            # 1. TARJETAS KPI FUTURISTAS
            kpi_cols = st.columns(min(4, len(cols_num)))
            for i, col in enumerate(cols_num[:4]):
                val_total = df_norm[col].sum()
                formato = f"${fmt_es(val_total)}" if semantica[col] == "moneda" else fmt_es(val_total, decimales_sugeridos(df_norm[col]))
                
                partes = [p.strip() for p in col.split(" | ")]
                nombre_kpi = " - ".join(partes[:-1]) if len(partes) > 1 and re.match(r'^\d{4}$', partes[-1]) else col
                
                with kpi_cols[i]:
                    st.markdown(
                        f"""
                        <div class='kpi-card'>
                            <div class='kpi-title'>{nombre_kpi[:30]}</div>
                            <div class='kpi-val'>{formato}</div>
                        </div>
                        """, 
                        unsafe_allow_html=True
                    )
            
            st.markdown("<br><hr style='border-color: #1e293b;'><br>", unsafe_allow_html=True)

            # ==============================================================================
            # 2. CONSTRUCCIÓN DE ARBOLESCENCIA COMPLETA DE 4 NIVELES
            # ==============================================================================
            arbol_4_niveles = {}
            for col in cols_num:
                partes = [p.strip() for p in col.split(" | ")]
                
                if len(partes) >= 4:
                    segmento = partes[0]                           # Ej: PLANTAS
                    padre = partes[1]                              # Ej: EMBOLSE
                    hijo = partes[-2]                              # Ej: ACUMULADO EMBOLSE / POR HECTAREA
                    anio = partes[-1] if re.match(r'^\d{4}$', partes[-1]) else "General"
                elif len(partes) == 3:
                    segmento = partes[0]
                    padre = partes[0]
                    hijo = partes[1]
                    anio = partes[2] if re.match(r'^\d{4}$', partes[2]) else "General"
                elif len(partes) == 2:
                    segmento = "General"
                    padre = partes[0]
                    hijo = partes[0] if re.match(r'^\d{4}$', partes[1]) else partes[1]
                    anio = partes[1] if re.match(r'^\d{4}$', partes[1]) else "General"
                else:
                    segmento = "General"
                    padre = "General"
                    hijo = col
                    anio = "General"
                
                if segmento not in arbol_4_niveles: arbol_4_niveles[segmento] = {}
                if padre not in arbol_4_niveles[segmento]: arbol_4_niveles[segmento][padre] = {}
                if hijo not in arbol_4_niveles[segmento][padre]: arbol_4_niveles[segmento][padre][hijo] = {}
                arbol_4_niveles[segmento][padre][hijo][anio] = col

            # 3. SELECTORES EN CASCADA COMPLETA (SEGMENTO ➔ PADRE ➔ HIJO ➔ AÑO)
            cols_categoricas = [c for c, t in semantica.items() if t in ("categoria", "texto")]
            c_eje_x, c_seg, c_padre, c_hijo, c_anio = st.columns([1.1, 1.1, 1.1, 1.3, 0.8])
            
            eje_x = c_eje_x.selectbox("Eje Principal:", cols_categoricas if cols_categoricas else df_norm.columns)
            
            # Selector 1: Segmento Principal (PLANTAS, HECTAREAS, General)
            segmentos_disp = list(arbol_4_niveles.keys())
            seg_sel = c_seg.selectbox("1. Segmento:", segmentos_disp)
            
            # Selector 2: Padre Maestro (EMBOLSE, CAJAS PRODUCCION, MERMA, etc.)
            padres_disp = list(arbol_4_niveles[seg_sel].keys())
            padre_sel = c_padre.selectbox("2. Padre:", padres_disp)
            
            # Selector 3: Condición / Hijo Penúltimo (EMBOLSE AÑOS, POR HECTAREA, CORTADA, etc.)
            hijos_disp = list(arbol_4_niveles[seg_sel][padre_sel].keys())
            hijo_sel = c_hijo.selectbox("3. Condición / Hijo:", hijos_disp)
            
            # Selector 4: Filtro Temporal (2022, 2023, 2024, 2025, 2026)
            anios_disp = list(arbol_4_niveles[seg_sel][padre_sel][hijo_sel].keys())
            anio_sel = c_anio.selectbox("4. Año:", anios_disp)

            # Columna final seleccionada
            col_target = arbol_4_niveles[seg_sel][padre_sel][hijo_sel][anio_sel]

            # 4. RENDERIZADO DEL GRÁFICO (PLOTLY CYBERPUNK)
            df_g = df_norm.groupby(eje_x)[col_target].sum().reset_index(name='Valor').sort_values('Valor', ascending=False).head(15)

            fig = px.bar(
                df_g, 
                x=eje_x, 
                y='Valor',
                text='Valor',
                template="plotly_dark",
                color='Valor',
                color_continuous_scale="Electric"
            )

            unidad_fmt = "$" if semantica.get(col_target) == "moneda" else ""
            fig.update_traces(
                texttemplate=f'{unidad_fmt}%{{text:,.1f}}', 
                textposition='outside',
                marker_line_color='#06b6d4',
                marker_line_width=1.5,
                opacity=0.9
            )
            
            titulo_grafico = f"{padre_sel.upper()} ➔ {hijo_sel.upper()} ({anio_sel})" if seg_sel != "General" else col_target.upper()
            fig.update_layout(
                title=dict(
                    text=f"COMPARATIVA: {titulo_grafico}",
                    font=dict(family='Orbitron', size=15, color='#38bdf8')
                ),
                paper_bgcolor='rgba(11, 15, 25, 0)',
                plot_bgcolor='rgba(15, 23, 42, 0.5)',
                xaxis=dict(title=dict(text=eje_x, font=dict(color='#94a3b8')), tickfont=dict(color='#cbd5e1')),
                yaxis=dict(title=dict(text="Volumen / Unidad", font=dict(color='#94a3b8')), tickfont=dict(color='#cbd5e1')),
                coloraxis_showscale=False,
                margin=dict(l=20, r=20, t=60, b=40),
                height=460
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
