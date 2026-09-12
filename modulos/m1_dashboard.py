"""
MOTOR B2B (MATRIZ PURA - BASE ESTRICTA DEFINITIVA)
========================================================================
- Truco de Espacios Invisibles: Elimina el "1" en las columnas fantasma.
- Contenedor Responsivo: Barra de desplazamiento siempre visible (60vh).
- Respeto de Datos: No se eliminan columnas vacías del Excel original.
"""
import re
import pandas as pd
import numpy as np
import streamlit as st
from typing import Tuple

VALORES_NULOS = {"none", "nan", "nat", "null", "n/a", "#n/a", "-", "--", ""}

def format_latam(valor):
    """Convierte número a formato LATAM visual (1.234,56)."""
    if pd.isna(valor) or valor == "": return ""
    try:
        v = float(valor)
        if v.is_integer(): return f"{int(v):,}".replace(",", ".")
        else: return f"{v:,.2f}".replace(",", "§").replace(".", ",").replace("§", ".")
    except Exception:
        return str(valor)

def extractor_logico_universal(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, str]:
    origen = "Archivo Base"
    if "_Origen_Archivo" in df_raw.columns:
        origen = str(df_raw["_Origen_Archivo"].dropna().iloc[0]) if not df_raw["_Origen_Archivo"].dropna().empty else origen
        df_raw = df_raw.drop(columns=["_Origen_Archivo"])

    # 1. Búsqueda del Ecuador
    fila_eje = 0
    for i in range(min(20, len(df_raw))):
        text_row = " ".join([str(x).lower() for x in df_raw.iloc[i] if pd.notna(x)])
        if any(w in text_row for w in ['semana', 'cinta', 'categoría', 'producto', 'fecha', 'código']):
            fila_eje = i
            break

    # 2. Búsqueda de Años
    fin_encabezados = fila_eje
    if fila_eje + 1 < len(df_raw):
        vals = [str(x).replace('.0','') for x in df_raw.iloc[fila_eje + 1] if pd.notna(x)]
        if sum(1 for x in vals if x.isdigit() and len(x) == 4) >= 2:
            fin_encabezados = fila_eje + 1

    ecuador_datos = fin_encabezados + 1

    # 3. Herencia
    inicio_encabezados = max(0, fila_eje - 2)
    df_headers = df_raw.iloc[inicio_encabezados:fin_encabezados + 1].copy().ffill(axis=1)

    # 4. Linaje Vertical
    nuevas_cols = []
    for col_idx in range(len(df_headers.columns)):
        jerarquia = []
        for f_idx in range(len(df_headers)):
            val = df_headers.iloc[f_idx, col_idx]
            if pd.notna(val) and str(val).strip() != "" and str(val).lower() != 'nan':
                texto = str(val).replace('.0', '').strip()
                if len(texto) > 40: continue 
                texto = re.sub(r'\b20\d{2}(?:\s*-\s*20\d{2})+\b', '', texto).strip('- ')
                texto_format = " ".join(texto.split()).title() if not texto.isdigit() else " ".join(texto.split())
                
                if texto_format:
                    if not jerarquia or jerarquia[-1].lower() != texto_format.lower():
                        jerarquia.append(texto_format)
        
        nombre_final = "<br>".join(jerarquia) if jerarquia else f"Col_{col_idx}"
        nuevas_cols.append(nombre_final)

    # 5. Aplicar a Datos y Manejar Duplicados Invisibles (Columnas Fantasma)
    df_datos = df_raw.iloc[ecuador_datos:].copy()
    
    cols_unicas, conteo = [], {}
    for col in nuevas_cols:
        if col in conteo:
            conteo[col] += 1
            # TRUCO B2B: Agregamos espacios en blanco invisibles al final para que Pandas 
            # las detecte como únicas, pero en la pantalla se vean exactamente igual.
            cols_unicas.append(f"{col}{'&nbsp;' * conteo[col]}")
        else:
            conteo[col] = 0
            cols_unicas.append(col)
            
    df_datos.columns = cols_unicas
    
    # Exterminador de filas basura en el eje
    mask = pd.Series([True] * len(df_datos), index=df_datos.index)
    for col in df_datos.columns[:3]:
        if df_datos[col].dtype == 'object':
            filtro = df_datos[col].astype(str).str.lower().str.contains(r'total|promedio|acumulado|año\b|ano\b|sem\b|sem\d', regex=True, na=False)
            mask = mask & (~filtro)
            
    df_datos = df_datos[mask].reset_index(drop=True).dropna(how='all', axis=0)

    # Autotipado
    for col in df_datos.columns:
        df_datos[col] = df_datos[col].map(lambda v: np.nan if str(v).lower().strip() in VALORES_NULOS else v)
        serie_str = df_datos[col].dropna().astype(str).str.replace(r"[$\s%]", "", regex=True).str.replace(",", ".")
        num = pd.to_numeric(serie_str, errors="coerce")
        if num.notna().sum() / max(len(serie_str), 1) > 0.5: df_datos[col] = num

    return df_datos, origen

def generar_tabla_html_piramidal(df: pd.DataFrame) -> str:
    """Tabla HTML con scrollbar anclado siempre a la pantalla."""
    html = """
    <div style="overflow: auto; max-height: 60vh; border: 1px solid #1f2937; border-radius: 8px; margin-bottom: 20px;">
        <table style="width: 100%; border-collapse: collapse; font-family: 'Rajdhani', sans-serif; background-color: #0b1120; color: #f3f4f6; text-align: center; font-size: 14px;">
            <thead style="background-color: #1e293b; position: sticky; top: 0; z-index: 1;">
                <tr>
    """
    for col in df.columns:
        html += f"<th style='padding: 12px 15px; border: 1px solid #334155; color: #eab308; font-weight: 700; white-space: nowrap; vertical-align: bottom;'>{col}</th>"
    
    html += "</tr></thead><tbody>"
    
    for _, row in df.iterrows():
        html += "<tr style='border-bottom: 1px solid #1f2937;'>"
        for col in df.columns:
            val = row[col]
            if pd.isna(val) or val == "": val_str = ""
            elif isinstance(val, (int, float)): val_str = format_latam(val)
            else: val_str = str(val)
            html += f"<td style='padding: 10px 15px; border-right: 1px solid #1f2937; white-space: nowrap;'>{val_str}</td>"
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
    </style>
    """, unsafe_allow_html=True)

def ejecutar(df_base, fuente_activa=None):
    inyectar_css()

    if df_base is None or df_base.empty:
        st.markdown("<div class='title-bar'>SISTEMA DE ESTRUCTURACIÓN MATRICIAL</div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='background: #111827; border-left: 4px solid #3b82f6; padding: 40px; border-radius: 8px; margin-top: 20px; text-align: center;'>
            <h2 style='color: #f3f4f6; font-family: Orbitron; margin-bottom: 15px;'>EN ESPERA DE DATOS</h2>
            <p style='color: #9ca3af; font-family: Rajdhani; font-size: 18px; line-height: 1.6;'>
                Sube tu matriz de Excel. Los duplicados se gestionarán de manera invisible.
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    if "ultima_fuente" not in st.session_state or st.session_state["ultima_fuente"] != fuente_activa:
        st.session_state["ultima_fuente"] = fuente_activa
        st.cache_data.clear()

    with st.spinner("Procesando estructura base y consolidando columnas fantasma..."):
        df_norm, origen = extractor_logico_universal(df_base)
        if df_norm.empty:
            st.error("⚠️ El archivo quedó vacío tras la extracción.")
            st.stop()

    st.markdown("<div class='title-bar'>BÓVEDA DE DATOS (ESTRUCTURA DEFINITIVA)</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='source-badge'>📁 ARCHIVO: {origen}</div>", unsafe_allow_html=True)

    tabla_html = generar_tabla_html_piramidal(df_norm)
    st.markdown(tabla_html, unsafe_allow_html=True)
