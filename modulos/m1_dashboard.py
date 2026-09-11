"""
MOTOR B2B (PRUEBA DE CIMIENTOS ESTRICTA - 12 COLUMNAS)
========================================================================
- Objetivo: Validar la extracción lógica estricta sin margen de error.
- Corte: Se fuerza el dataframe a exactamente 12 columnas.
"""
import re
import pandas as pd
import numpy as np
import streamlit as st
from typing import Tuple

VALORES_NULOS = {"none", "nan", "nat", "null", "n/a", "#n/a", "-", "--", ""}

def extractor_logico_universal(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    origen = "Archivo Base"
    if "_Origen_Archivo" in df_raw.columns:
        origen = str(df_raw["_Origen_Archivo"].dropna().iloc[0]) if not df_raw["_Origen_Archivo"].dropna().empty else origen
        df_raw = df_raw.drop(columns=["_Origen_Archivo"])

    # =========================================================
    # CORTE ESTRICTO Y ABSOLUTO A LAS PRIMERAS 12 COLUMNAS
    # =========================================================
    df_raw = df_raw.iloc[:, :12].copy()

    # Paso 1: Buscar la fila Ecuador (Línea de flotación operativa)
    fila_eje = 0
    for i in range(min(20, len(df_raw))):
        text_row = " ".join([str(x).lower() for x in df_raw.iloc[i] if pd.notna(x)])
        if any(w in text_row for w in ['semana', 'cinta', 'categoría', 'producto', 'fecha', 'código']):
            fila_eje = i
            break

    # Paso 2: Determinar fin de encabezados (buscando años en la fila de abajo)
    fin_encabezados = fila_eje
    if fila_eje + 1 < len(df_raw):
        vals = [str(x).replace('.0','') for x in df_raw.iloc[fila_eje + 1] if pd.notna(x)]
        years = sum(1 for x in vals if x.isdigit() and len(x) == 4)
        if years >= 2:
            fin_encabezados = fila_eje + 1

    ecuador_datos = fin_encabezados + 1

    # Paso 3: Herencia Horizontal (Celdas combinadas)
    inicio_encabezados = max(0, fila_eje - 2)
    df_headers = df_raw.iloc[inicio_encabezados:fin_encabezados + 1].copy()
    df_headers = df_headers.ffill(axis=1)

    # Paso 4: Linaje Vertical (Construcción del nombre real)
    nuevas_cols = []
    for col_idx in range(len(df_headers.columns)):
        jerarquia = []
        for f_idx in range(len(df_headers)):
            val = df_headers.iloc[f_idx, col_idx]
            if pd.notna(val) and str(val).strip() != "" and str(val).lower() != 'nan':
                texto = str(val).replace('.0', '').strip()
                
                # Ignorar basura
                if len(texto) > 40: continue 
                texto = re.sub(r'\b20\d{2}(?:\s*-\s*20\d{2})+\b', '', texto).strip('- ')
                texto = " ".join(texto.split())
                
                texto_format = texto.title() if not texto.isdigit() else texto
                if texto_format and (not jerarquia or jerarquia[-1].lower() != texto_format.lower()):
                    jerarquia.append(texto_format)
                    
        nombre_final = " ➔ ".join(jerarquia) if jerarquia else f"Columna_{col_idx}"
        nuevas_cols.append(nombre_final)

    # Asignar Linaje al DataFrame de Datos
    df_datos = df_raw.iloc[ecuador_datos:].copy()
    
    cols_unicas, conteo = [], {}
    for col in nuevas_cols:
        if col in conteo:
            conteo[col] += 1
            cols_unicas.append(f"{col} ({conteo[col]})")
        else:
            conteo[col] = 0
            cols_unicas.append(col)
            
    df_datos.columns = cols_unicas
    
    # Paso 5: El Exterminador de Basura (Totales y Resúmenes en ejes X)
    mask = pd.Series([True] * len(df_datos), index=df_datos.index)
    for col in df_datos.columns[:3]:
        if df_datos[col].dtype == 'object':
            filtro = df_datos[col].astype(str).str.lower().str.contains(r'total|promedio|acumulado|año\b|ano\b|sem\b|sem\d', regex=True, na=False)
            mask = mask & (~filtro)
            
    df_datos = df_datos[mask].reset_index(drop=True)
    df_datos = df_datos.dropna(how='all', axis=0)

    # Autotipado numérico
    for col in df_datos.columns:
        df_datos[col] = df_datos[col].map(lambda v: np.nan if str(v).lower().strip() in VALORES_NULOS else v)
        serie_str = df_datos[col].dropna().astype(str).str.replace(r"[$\s%]", "", regex=True).str.replace(",", ".")
        num = pd.to_numeric(serie_str, errors="coerce")
        if num.notna().sum() / max(len(serie_str), 1) > 0.5:
            df_datos[col] = num

    return df_datos, origen

def inyectar_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@500;800;900&family=Rajdhani:wght@500;600;700&display=swap');
        .main { background-color: #0b1120; }
        .title-bar { color: #eab308; font-family: 'Orbitron', sans-serif; font-size: 22px; font-weight: 800; border-bottom: 1px solid #1e293b; padding-bottom: 12px; margin-bottom: 20px; letter-spacing: 1px; } 
        .source-badge { display: inline-block; background: #1e293b; border: 1px solid #334155; color: #94a3b8; padding: 4px 12px; border-radius: 4px; font-family: 'Rajdhani', sans-serif; font-size: 13px; font-weight: 700; margin-bottom: 18px; }
    </style>
    """, unsafe_allow_html=True)

def ejecutar(df_base, fuente_activa=None):
    inyectar_css()

    if df_base is None or df_base.empty:
        st.markdown("<div class='title-bar'>MODO ESTRICTO: 12 COLUMNAS</div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='background: #111827; border-left: 4px solid #f43f5e; padding: 40px; border-radius: 8px; margin-top: 20px; text-align: center;'>
            <h2 style='color: #f3f4f6; font-family: Orbitron; margin-bottom: 15px;'>ESPERANDO ARCHIVO</h2>
            <p style='color: #9ca3af; font-family: Rajdhani; font-size: 18px; line-height: 1.6;'>
                Sube tu matriz. El sistema bloqueará todo lo que pase de la columna 12.
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    if "ultima_fuente" not in st.session_state or st.session_state["ultima_fuente"] != fuente_activa:
        st.session_state["ultima_fuente"] = fuente_activa
        st.cache_data.clear()

    with st.spinner("Procesando Cimientos..."):
        df_norm, origen = extractor_logico_universal(df_base)
        
        if df_norm.empty:
            st.error("⚠️ El archivo quedó vacío tras la extracción.")
            st.stop()

    st.markdown("<div class='title-bar'>MATRIZ DE DATOS PURA (12 COLUMNAS EXACTAS)</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='source-badge'>📁 ARCHIVO: {origen}</div>", unsafe_allow_html=True)
    
    st.info("📌 Revisa detenidamente: ¿Están bien armados los encabezados por herencia? ¿Están limpias las filas de las cintas?")

    st.dataframe(
        df_norm, 
        use_container_width=True, 
        hide_index=True, 
        height=650
    )
