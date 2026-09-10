"""
MOTOR UNIVERSAL INTELIGENTE DE DATOS
=====================================
Aplicación Streamlit que acepta prácticamente cualquier tabla (CSV / Excel),
infiere su estructura y tipos, la limpia sin destruir información, la
normaliza, la formatea al estilo colombiano, genera filtros, KPIs y gráficos
de forma completamente dinámica, y permite exportar tanto los datos
originales como los normalizados.

No hay NINGUNA lógica atada a nombres de columnas específicos: todo se
infiere en tiempo de ejecución a partir de la tabla que el usuario cargue.
"""

import io
import re
import json
import traceback
from datetime import datetime

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


# ==============================================================================
# 0. UTILIDADES DE FORMATO (ESTILO COLOMBIANO)
# ==============================================================================
def fmt_es(valor, decimales=2, prefijo="", sufijo=""):
    """Formatea un número al estilo colombiano: punto para miles, coma para decimales."""
    if valor is None or (isinstance(valor, float) and (np.isnan(valor) or np.isinf(valor))):
        return ""
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return str(valor)
    texto = f"{v:,.{decimales}f}"
    texto = texto.replace(",", "§").replace(".", ",").replace("§", ".")
    return f"{prefijo}{texto}{sufijo}"


def decimales_sugeridos(serie, config_decimales):
    """Determina cuántos decimales mostrar, respetando la config del usuario si no es AUTO."""
    if config_decimales != "AUTO":
        return int(config_decimales)
    serie_valida = serie.dropna()
    if serie_valida.empty:
        return 0
    # Si todos los valores son enteros "de facto", 0 decimales.
    es_entero = np.allclose(serie_valida % 1, 0, atol=1e-9)
    if es_entero:
        return 0
    # Si los valores tienen mucha cola decimal (ruido de punto flotante), limitar a 2.
    return 2


# ==============================================================================
# 1. INGESTA UNIVERSAL
# ==============================================================================
def cargar_archivo(archivo):
    """Lee CSV o Excel devolviendo la grilla CRUDA (sin asumir fila de encabezado),
    para que el motor de detección de encabezados multinivel decida cuántas filas
    son realmente título/encabezado antes de construir las columnas."""
    nombre = archivo.name.lower()
    if nombre.endswith(".csv") or nombre.endswith(".tsv") or nombre.endswith(".txt"):
        sep = "\t" if nombre.endswith(".tsv") else None
        for enc in ("utf-8", "latin-1", "utf-8-sig"):
            try:
                archivo.seek(0)
                return pd.read_csv(archivo, sep=sep, engine="python", encoding=enc, header=None)
            except Exception:
                continue
        archivo.seek(0)
        return pd.read_csv(archivo, sep=sep, engine="python", encoding="latin-1", header=None)
    else:
        archivo.seek(0)
        xls = pd.ExcelFile(archivo)
        hoja = xls.sheet_names[0]
        if len(xls.sheet_names) > 1:
            hoja = st.selectbox("📄 Selecciona la hoja a analizar:", xls.sheet_names, key="selector_hoja")
        return pd.read_excel(xls, sheet_name=hoja, header=None)


def limpiar_nulos_crudo(df):
    """Convierte cualquier representación de 'vacío' (None, 'None', 'NaN', celdas en
    blanco de merges de Excel, encabezados automáticos 'Unnamed: N' de pandas, etc.)
    a un np.nan real, ANTES de tocar encabezados."""
    patron_unnamed = re.compile(r"^unnamed:\s*\d+$")

    def _limpiar(v):
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return np.nan
        if isinstance(v, str):
            s = v.strip()
            if s == "" or s.lower() in VALORES_NULOS or patron_unnamed.match(s.lower()):
                return np.nan
            return s
        return v
    return df.apply(lambda serie: serie.map(_limpiar))


def reconstruir_grilla_cruda(df_crudo):
    """Convierte lo que llegue (ya sea la grilla realmente cruda de cargar_archivo(),
    o un DataFrame que un cargador externo ya interpretó con pandas por defecto —como
    hace el app.py maestro con pd.read_excel/pd.read_csv sin header=None—) a una
    única representación cruda y homogénea: la fila que pandas consumió como
    encabezado se reinserta como fila de datos, para que el motor de detección de
    encabezados multinivel pueda analizarla igual que cualquier otra fila."""
    columnas_son_posicionales = all(isinstance(c, (int, np.integer)) for c in df_crudo.columns)
    if columnas_son_posicionales:
        df_raw = df_crudo.copy()
        df_raw.columns = range(df_raw.shape[1])
        return df_raw

    fila_encabezado = pd.DataFrame([[str(c) for c in df_crudo.columns]])
    cuerpo = df_crudo.copy()
    cuerpo.columns = range(cuerpo.shape[1])
    fila_encabezado.columns = cuerpo.columns
    return pd.concat([fila_encabezado, cuerpo], ignore_index=True)


# ==============================================================================
# 1.1 DETECCIÓN Y CONSOLIDACIÓN DE ENCABEZADOS MULTINIVEL
# ==============================================================================
def _densidad_y_variedad(fila):
    """Para una fila: (proporción de celdas numéricas, proporción de valores únicos)."""
    vals = fila.dropna()
    if len(vals) == 0:
        return 0.0, 0.0
    numericos = 0
    for v in vals:
        if isinstance(v, (int, float, np.integer, np.floating)) and not isinstance(v, bool):
            numericos += 1
        elif isinstance(v, str):
            vs = v.strip().replace(".", "", 1).replace(",", "", 1).replace("-", "", 1).replace("%", "")
            if vs.isdigit():
                numericos += 1
    densidad = numericos / len(vals)
    variedad = vals.nunique() / len(vals)
    return densidad, variedad


def detectar_filas_encabezado(df_raw, max_filas_header=8):
    """Sugiere cuántas filas iniciales son encabezado/título (no datos), buscando el
    primer punto donde varias filas consecutivas son simultáneamente densas en
    números Y variadas en sus valores (patrón típico de filas de datos reales,
    a diferencia de una fila de años/categorías que se repite poco)."""
    tope = min(len(df_raw), max_filas_header + 4)
    metrica = [_densidad_y_variedad(df_raw.iloc[i]) for i in range(tope)]
    for i in range(tope):
        ventana = metrica[i:i + 3]
        if len(ventana) < 2:
            break
        if all(d > 0.5 and v > 0.55 for d, v in ventana):
            return max(i, 1)
    return 1  # por defecto: tabla estándar con una sola fila de encabezado


def construir_columnas_multinivel(df_raw, n_header):
    """Convierte las primeras n_header filas (que pueden representar encabezados
    combinados en varios niveles, como en Excel) en un único nombre de columna por
    posición, propagando celdas combinadas (forward-fill horizontal) y uniendo los
    niveles distintos con ' - '. Las filas restantes se convierten en los datos."""
    n_header = max(int(n_header), 0)
    if n_header == 0 or len(df_raw) <= n_header:
        nombres = [f"Columna_{i + 1}" for i in range(df_raw.shape[1])]
        datos = df_raw.copy()
        datos.columns = nombres
        return datos.reset_index(drop=True), nombres

    bloque = df_raw.iloc[:n_header].apply(lambda fila: fila.ffill(), axis=1)
    datos = df_raw.iloc[n_header:].copy().reset_index(drop=True)

    nombres_finales = []
    for col_idx in range(bloque.shape[1]):
        niveles, anterior = [], None
        for fila_idx in range(bloque.shape[0]):
            val = bloque.iat[fila_idx, col_idx]
            if pd.isna(val):
                continue
            val_str = str(val).strip()
            if val_str == "" or val_str.lower() in VALORES_NULOS or val_str == anterior:
                continue
            niveles.append(val_str)
            anterior = val_str
        nombre = " - ".join(dict.fromkeys(niveles)) if niveles else f"Columna_{col_idx + 1}"
        nombres_finales.append(nombre)

    vistos, nombres_unicos = {}, []
    for n in nombres_finales:
        if n in vistos:
            vistos[n] += 1
            nombres_unicos.append(f"{n} ({vistos[n]})")
        else:
            vistos[n] = 0
            nombres_unicos.append(n)

    datos.columns = nombres_unicos
    return datos, nombres_unicos


def panel_estructura(df_raw):
    """Muestra al usuario cómo se interpretó el encabezado y le permite corregirlo,
    igual que el paso de 'Usar la primera fila como encabezado' de Power Query/Power BI."""
    sugerido = detectar_filas_encabezado(df_raw)
    firma = f"estructura_{df_raw.shape}_{hash(tuple(df_raw.iloc[0].astype(str).tolist()))}"

    with st.expander("🧩 Estructura del archivo (encabezados detectados)", expanded=True):
        st.caption(
            "El sistema detecta automáticamente cuántas filas son título/encabezado. "
            "Si una tabla tiene encabezados combinados o poco comunes, ajusta el número "
            "aquí — es el mismo control que usarías en Power BI/Power Query para "
            "'promover encabezados'."
        )
        vista_previa = df_raw.head(min(len(df_raw), sugerido + 4)).copy()
        vista_previa.columns = [f"Col {i+1}" for i in range(vista_previa.shape[1])]
        st.dataframe(vista_previa, use_container_width=True, hide_index=True, height=220)
        n_header = st.number_input(
            "Filas de encabezado a combinar:", min_value=0, max_value=min(len(df_raw), 12),
            value=sugerido, step=1, key=firma,
        )
    return int(n_header)


# ==============================================================================
# 2. NORMALIZACIÓN PROFUNDA (mantiene una capa "original" intacta)
# ==============================================================================
@st.cache_data(show_spinner=False)
def normalizar_datos(df_con_encabezado):
    """Recibe una tabla que YA tiene nombres de columna definitivos (construidos por
    construir_columnas_multinivel) y aplica limpieza + inferencia de tipos, sin tocar
    de nuevo la estructura de encabezados."""
    advertencias = []
    df = df_con_encabezado.copy()

    # A. NOMBRES DE COLUMNA VACÍOS O DUPLICADOS (red de seguridad)
    nombres_originales = list(df.columns)
    nuevas_cols, vistos = [], {}
    for i, c in enumerate(df.columns):
        c_str = str(c).strip()
        if c_str == "" or c_str.lower() == "nan":
            c_str = f"Columna_{i + 1}"
        base = c_str
        if base in vistos:
            vistos[base] += 1
            c_str = f"{base} ({vistos[base]})"
        else:
            vistos[base] = 0
        nuevas_cols.append(c_str)
    if len(set(nombres_originales)) < len(nombres_originales):
        advertencias.append("Se detectaron encabezados duplicados y fueron renombrados automáticamente.")
    df.columns = nuevas_cols
    mapa_original = dict(zip(nuevas_cols, nombres_originales))

    # B. FILAS Y COLUMNAS COMPLETAMENTE VACÍAS
    filas_vacias = df.isna().all(axis=1).sum()
    cols_vacias = [c for c in df.columns if df[c].isna().all()]
    if filas_vacias:
        advertencias.append(f"Se encontraron {filas_vacias} filas completamente vacías.")
    if cols_vacias:
        advertencias.append(f"Se encontraron {len(cols_vacias)} columnas completamente vacías: {', '.join(cols_vacias[:5])}.")
    df = df.dropna(how="all")

    # C. LIMPIEZA DE "BASURA TEXTUAL" A NULOS REALES (preservando el 0)
    def limpiar_celda(v):
        if pd.isna(v):
            return np.nan
        if isinstance(v, str):
            s = v.strip()
            if s.lower() in VALORES_NULOS:
                return np.nan
            return s
        return v

    df = df.apply(lambda serie: serie.map(limpiar_celda))

    # D. DUPLICADOS
    n_duplicados = df.duplicated().sum()
    if n_duplicados:
        advertencias.append(f"Se detectaron {n_duplicados} filas duplicadas.")

    # E. INFERENCIA DE TIPOS (rescate de números/fechas atrapados en texto)
    conteo_faltantes_antes = {}
    for col in df.columns:
        conteo_faltantes_antes[col] = int(df[col].isna().sum())
        if pd.api.types.is_numeric_dtype(df[col]) or pd.api.types.is_datetime64_any_dtype(df[col]):
            continue
        serie = df[col].dropna().astype(str).str.strip()
        if serie.empty:
            continue

        # ¿Fecha?
        patron_fecha = r"^\d{1,4}[-/]\d{1,2}[-/]\d{1,4}$"
        if serie.str.match(patron_fecha).mean() > 0.6:
            # Si el año va primero (ISO: AAAA-MM-DD), el orden día/mes ya es inequívoco.
            # Si el año va al final, se asume convención colombiana DD/MM/AAAA.
            anio_primero = serie.str.match(r"^\d{4}[-/]").mean() > 0.5
            convertido = pd.to_datetime(df[col], errors="coerce", dayfirst=not anio_primero)
            if convertido.notna().sum() / max(len(serie), 1) > 0.6:
                n_invalidas = df[col].notna().sum() - convertido.notna().sum()
                if n_invalidas > 0:
                    advertencias.append(f"'{col}': {n_invalidas} valores con formato de fecha inconsistente.")
                df[col] = convertido
                continue

        # ¿Número (posiblemente moneda o porcentaje en texto)?
        limpio = serie.str.replace(r"[$\s]", "", regex=True).str.replace("%", "", regex=False)
        limpio = limpio.str.replace(r"\.(?=\d{3}(?:\D|$))", "", regex=True)  # puntos de miles
        limpio = limpio.str.replace(",", ".", regex=False)
        numerico = pd.to_numeric(limpio, errors="coerce")
        if numerico.notna().sum() / max(len(serie), 1) > 0.6:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(r"[$\s]", "", regex=True).str.replace("%", "", regex=False)
                .str.replace(r"\.(?=\d{3}(?:\D|$))", "", regex=True).str.replace(",", ".", regex=False),
                errors="coerce",
            )

    return df, mapa_original, advertencias, conteo_faltantes_antes


# ==============================================================================
# 3. INFERENCIA SEMÁNTICA DE COLUMNAS
# ==============================================================================
PALABRAS_MONEDA = ("precio", "costo", "valor", "ingreso", "venta", "presupuesto",
                    "salario", "nomina", "nómina", "pago", "gasto", "tarifa", "monto")
PALABRAS_PORCENTAJE = ("%", "porcentaje", "pct", "cumplim", "participac", "tasa", "avance")
PALABRAS_CODIGO = ("id", "código", "codigo", "cod_", "nit", "documento", "referencia", "ref_")
PALABRAS_CANTIDAD = ("cantidad", "total", "hectarea", "hectárea", "produccion", "producción",
                      "unidades", "stock", "inventario", "peso", "volumen")


def inferir_semantica(df):
    """Devuelve {columna: 'moneda'|'porcentaje'|'codigo'|'cantidad'|'fecha'|'categoria'|'texto'}"""
    semantica = {}
    n = len(df)
    for col in df.columns:
        nombre = col.lower()
        serie = df[col]
        if pd.api.types.is_datetime64_any_dtype(serie):
            semantica[col] = "fecha"
        elif pd.api.types.is_numeric_dtype(serie):
            if any(p in nombre for p in PALABRAS_CODIGO) and serie.dropna().apply(
                lambda x: float(x).is_integer()).all():
                semantica[col] = "codigo"
            elif any(p in nombre for p in PALABRAS_PORCENTAJE):
                semantica[col] = "porcentaje"
            elif any(p in nombre for p in PALABRAS_MONEDA):
                semantica[col] = "moneda"
            else:
                semantica[col] = "cantidad"
        else:
            nunicos = serie.nunique(dropna=True)
            if n > 0 and (nunicos / n) < 0.5 and nunicos <= 50:
                semantica[col] = "categoria"
            else:
                semantica[col] = "texto"
    return semantica


# ==============================================================================
# 4. DIAGNÓSTICO / SALUD DE DATOS (IA opcional, segura)
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
        Eres un motor analítico universal B2B. Analiza esta estructura de datos:
        Columnas: {columnas}
        Muestra: {muestra_json}
        Resumen: {stats_json}
        Responde ÚNICAMENTE en JSON con: "titulo_contextual", "resumen_gerencial", "cuellos_de_botella" (lista).
        """
        modelo = genai.GenerativeModel("gemini-1.5-flash", generation_config={"response_mime_type": "application/json"})
        respuesta = modelo.generate_content(prompt).text.strip()
        if "```json" in respuesta:
            respuesta = respuesta.split("```json")[1].split("```")[0].strip()
        return json.loads(respuesta)
    except Exception:
        return None


def calcular_salud(df):
    total_celdas = df.size
    faltantes = int(df.isna().sum().sum())
    completos = 100 - (faltantes / max(total_celdas, 1)) * 100
    return round(completos, 1), faltantes


# ==============================================================================
# 5. CONFIGURACIÓN VISUAL DE COLUMNAS PARA st.dataframe
# ==============================================================================
def construir_column_config(df, semantica, nombres_visibles, decimales_cfg, formato_fecha):
    config = {}
    for col in df.columns:
        etiqueta = nombres_visibles.get(col, col)
        tipo = semantica.get(col, "texto")
        if tipo == "moneda":
            dec = decimales_sugeridos(df[col], decimales_cfg) if decimales_cfg == "AUTO" else int(decimales_cfg)
            config[col] = st.column_config.NumberColumn(etiqueta, format=f"$ %.{dec}f")
        elif tipo == "porcentaje":
            dec = 1 if decimales_cfg == "AUTO" else int(decimales_cfg)
            config[col] = st.column_config.NumberColumn(etiqueta, format=f"%.{dec}f%%")
        elif tipo == "cantidad":
            dec = decimales_sugeridos(df[col], decimales_cfg)
            config[col] = st.column_config.NumberColumn(etiqueta, format="localized" if dec == 0 else f"%.{dec}f")
        elif tipo == "codigo":
            config[col] = st.column_config.TextColumn(etiqueta)
        elif tipo == "fecha":
            config[col] = st.column_config.DateColumn(etiqueta, format=formato_fecha)
        else:
            config[col] = st.column_config.TextColumn(etiqueta)
    return config


# ==============================================================================
# 6. RENDER PRINCIPAL
# ==============================================================================
def inyectar_css():
    st.markdown("""
    <style>
        .title-bar { color:#1e293b; font-family:'Inter',sans-serif; font-size:24px; font-weight:800;
            border-bottom:2px solid #e2e8f0; padding-bottom:10px; margin-bottom:18px; }
        .metric-card { background:#fff; border-left:4px solid #3b82f6; padding:14px 16px; border-radius:8px;
            box-shadow:0 1px 3px rgba(0,0,0,.08); border:1px solid #e2e8f0; }
        .metric-title { color:#64748b; font-size:11px; text-transform:uppercase; font-weight:700;
            margin-bottom:4px; letter-spacing:.4px; }
        .metric-value { color:#0f172a; font-size:21px; font-weight:800; margin:0; }
        .ia-box { background:#f8fafc; border:1px solid #e2e8f0; padding:12px 18px; border-radius:8px;
            margin-bottom:16px; border-left:4px solid #8b5cf6; font-size:13.5px; }
        .ia-box strong { color:#4f46e5; font-size:12px; text-transform:uppercase; }
        .warn-box { background:#fffbeb; border:1px solid #fde68a; padding:10px 14px; border-radius:8px;
            margin-bottom:6px; font-size:13px; color:#92400e; }
        .health-badge { display:inline-block; padding:4px 12px; border-radius:20px; font-size:12.5px;
            font-weight:700; }
        div[data-testid="stExpander"] { border:1px solid #e2e8f0 !important; border-radius:8px !important; }
        .stSelectbox, .stMultiSelect { max-width: 260px; }
        button[data-baseweb="tab"] { font-size:14px !important; font-weight:600 !important; }
    </style>
    """, unsafe_allow_html=True)


def panel_configuracion():
    with st.sidebar:
        st.markdown("### ⚙️ Configuración de visualización")
        decimales = st.selectbox("Decimales numéricos", ["AUTO", "0", "1", "2", "3"], index=0)
        formato_fecha = st.selectbox("Formato de fecha", ["YYYY-MM-DD", "DD/MM/YYYY", "MM/DD/YYYY"], index=0)
        tam_pagina = st.selectbox("Registros por página", [25, 50, 100, 250, 500], index=1)
        densidad = st.radio("Densidad de tabla", ["Estándar", "Compacta"], horizontal=True)
    return decimales, formato_fecha, tam_pagina, densidad


def construir_kpis(df, semantica):
    st.markdown(f"""<div class='metric-card' style='border-color:#64748b;display:inline-block;min-width:150px'>
    <div class='metric-title'>Registros totales</div><div class='metric-value'>{fmt_es(len(df), 0)}</div></div>""",
                unsafe_allow_html=True)

    candidatas = [c for c, t in semantica.items() if t in ("moneda", "cantidad", "porcentaje")][:4]
    if not candidatas:
        return
    cols = st.columns(len(candidatas) + 1)
    with cols[0]:
        st.markdown(f"""<div class='metric-card' style='border-color:#64748b'>
        <div class='metric-title'>Registros totales</div><div class='metric-value'>{fmt_es(len(df), 0)}</div></div>""",
                    unsafe_allow_html=True)
    for i, col in enumerate(candidatas):
        tipo = semantica[col]
        serie = df[col].dropna()
        if serie.empty:
            continue
        if tipo == "porcentaje":
            valor, etiqueta_kpi, texto = serie.mean(), "Promedio de", fmt_es(serie.mean(), 1, sufijo=" %")
        elif tipo == "moneda":
            valor, etiqueta_kpi, texto = serie.sum(), "Suma de", fmt_es(serie.sum(), 0, prefijo="$ ")
        else:
            valor, etiqueta_kpi, texto = serie.sum(), "Suma de", fmt_es(serie.sum(), decimales_sugeridos(serie, "AUTO"))
        with cols[i + 1]:
            st.markdown(f"""<div class='metric-card'>
            <div class='metric-title'>{etiqueta_kpi} {col[:16]}</div>
            <div class='metric-value'>{texto}</div></div>""", unsafe_allow_html=True)


def construir_filtros(df, semantica):
    """Filtros dinámicos, compactos y bajo demanda."""
    columnas_filtrables = st.multiselect(
        "Agregar filtro por columna:", df.columns, placeholder="Selecciona columnas para segmentar...",
        key="cols_filtro",
    )
    df_filtrado = df.copy()
    if not columnas_filtrables:
        return df_filtrado

    with st.container(border=True):
        bloques = st.columns(min(len(columnas_filtrables), 4)) if len(columnas_filtrables) <= 4 else None
        for i, col in enumerate(columnas_filtrables):
            contenedor = bloques[i] if bloques else st
            tipo = semantica.get(col)
            with contenedor:
                if tipo == "fecha":
                    validos = df[col].dropna()
                    if validos.empty:
                        continue
                    d_min, d_max = validos.min().date(), validos.max().date()
                    rango = st.date_input(col, value=(d_min, d_max), min_value=d_min, max_value=d_max, key=f"f_{col}")
                    if isinstance(rango, tuple) and len(rango) == 2:
                        df_filtrado = df_filtrado[
                            (df_filtrado[col].dt.date >= rango[0]) & (df_filtrado[col].dt.date <= rango[1])
                        ]
                elif tipo in ("cantidad", "moneda", "porcentaje"):
                    validos = df[col].dropna()
                    if validos.empty:
                        continue
                    v_min, v_max = float(validos.min()), float(validos.max())
                    if v_min == v_max:
                        continue
                    rango = st.slider(col, min_value=v_min, max_value=v_max, value=(v_min, v_max), key=f"f_{col}")
                    df_filtrado = df_filtrado[df_filtrado[col].between(rango[0], rango[1]) | df_filtrado[col].isna()]
                else:
                    opciones = sorted(df[col].dropna().unique().tolist(), key=str)
                    seleccion = st.multiselect(col, opciones, placeholder="Seleccionar...", key=f"f_{col}")
                    if seleccion:
                        df_filtrado = df_filtrado[df_filtrado[col].isin(seleccion)]
    return df_filtrado


def paginar(df, tam_pagina, key):
    total = len(df)
    total_paginas = max(1, -(-total // tam_pagina))
    c1, c2 = st.columns([3, 1])
    with c2:
        pagina = st.number_input("Página", min_value=1, max_value=total_paginas, value=1, step=1, key=key)
    inicio, fin = (pagina - 1) * tam_pagina, min(pagina * tam_pagina, total)
    with c1:
        st.caption(f"Mostrando **{inicio + 1 if total else 0}–{fin}** de **{fmt_es(total, 0)}** registros "
                    f"(página {pagina} de {total_paginas}).")
    return df.iloc[inicio:fin]


def graficos_automaticos(df, semantica, key_prefix):
    cols_num = [c for c, t in semantica.items() if t in ("cantidad", "moneda", "porcentaje")]
    cols_fecha = [c for c, t in semantica.items() if t == "fecha"]
    cols_cat = [c for c, t in semantica.items() if t == "categoria"]

    if not cols_num:
        st.warning("Se requieren columnas numéricas para generar analítica visual.")
        return

    c_x, c_y = st.columns(2)
    opciones_x = cols_fecha + cols_cat + [c for c, t in semantica.items() if t == "codigo"]
    eje_x = c_x.selectbox("Dimensión (Eje X):", opciones_x, key=f"{key_prefix}_x") if opciones_x else None
    eje_y = c_y.selectbox("Métrica (Eje Y):", cols_num, key=f"{key_prefix}_y") if cols_num else None

    if eje_x and eje_y:
        df_g = df.groupby(eje_x)[eje_y].sum(numeric_only=True).reset_index().dropna()
        if eje_x in cols_fecha:
            df_g = df_g.sort_values(eje_x)
            fig = px.line(df_g, x=eje_x, y=eje_y, template="plotly_white", markers=True)
            fig.update_traces(line_color="#10b981", line_width=3)
        else:
            df_g = df_g.sort_values(eje_y, ascending=False).head(30)
            fig = px.bar(df_g, x=eje_x, y=eje_y, template="plotly_white")
            fig.update_traces(marker_color="#3b82f6")
        fig.update_layout(margin=dict(l=10, r=10, t=20, b=10), font=dict(family="Inter"))
        st.plotly_chart(fig, use_container_width=True, key=f"{key_prefix}_chart1")

    if len(cols_num) >= 2:
        st.markdown("**🔬 Relación entre dos variables numéricas**")
        c_a, c_b = st.columns(2)
        var_a = c_a.selectbox("Variable A:", cols_num, key=f"{key_prefix}_a")
        var_b = c_b.selectbox("Variable B:", [c for c in cols_num if c != var_a], key=f"{key_prefix}_b")
        fig2 = px.scatter(df, x=var_a, y=var_b, template="plotly_white", opacity=0.7)
        fig2.update_traces(marker_color="#8b5cf6")
        fig2.update_layout(margin=dict(l=10, r=10, t=20, b=10), font=dict(family="Inter"))
        st.plotly_chart(fig2, use_container_width=True, key=f"{key_prefix}_chart2")


def exportar(df_original, df_normalizado):
    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("📥 CSV (normalizado)", df_normalizado.to_csv(index=False).encode("utf-8"),
                            "datos_normalizados.csv", "text/csv", use_container_width=True)
    with c2:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df_normalizado.to_excel(writer, index=False, sheet_name="Normalizado")
        st.download_button("📥 Excel (normalizado)", buffer.getvalue(), "datos_normalizados.xlsx",
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True)
    with c3:
        st.download_button("📥 CSV (original)", df_original.to_csv(index=False).encode("utf-8"),
                            "datos_originales.csv", "text/csv", use_container_width=True)


# ==============================================================================
# 7. NÚCLEO
# ==============================================================================
def ejecutar(df_crudo, fuente_activa=None):
    """fuente_activa se acepta por compatibilidad con integraciones existentes
    (p. ej. un app.py externo que haga `m1.ejecutar(df_base, fuente_activa)`);
    no es obligatorio y no afecta la lógica del motor."""
    try:
        inyectar_css()

        if df_crudo is None or df_crudo.empty:
            st.info("💡 Bóveda vacía. Carga un dataset para iniciar la arquitectura de datos.")
            return

        decimales_cfg, formato_fecha, tam_pagina, densidad = panel_configuracion()

        # 1) Reconstruir la grilla realmente cruda (por si el df ya llegó pre-procesado
        #    por un cargador externo, como el app.py maestro) y limpiar tokens de nulos
        #    ANTES de tocar encabezados, para que "None"/"NaN"/"Unnamed: N" nunca se
        #    muestren literalmente ni contaminen el nombre de una columna.
        df_raw = limpiar_nulos_crudo(reconstruir_grilla_cruda(df_crudo))

        # 2) Detectar y construir el encabezado (posiblemente multinivel), con
        #    control manual disponible para el usuario (estilo Power Query).
        n_header = panel_estructura(df_raw)
        df_con_encabezado, _ = construir_columnas_multinivel(df_raw, n_header)

        # 3) Limpiar y tipificar a partir del encabezado ya resuelto.
        df_norm, mapa_original, advertencias, faltantes_por_col = normalizar_datos(df_con_encabezado)
        semantica = inferir_semantica(df_norm)
        nombres_visibles = {c: c for c in df_norm.columns}

        diagnostico = generar_diagnostico_ia(
            df_norm.head(3).to_json(date_format="iso"),
            df_norm.describe(include="all").to_json(),
            list(df_norm.columns),
        )
        titulo = diagnostico.get("titulo_contextual") if diagnostico else "MOTOR UNIVERSAL DE DATOS"
        st.markdown(f"<div class='title-bar'>💠 {titulo}</div>", unsafe_allow_html=True)
        if fuente_activa:
            st.caption(f"Fuente: {fuente_activa}")

        if diagnostico:
            st.markdown(f"<div class='ia-box'><strong>🤖 Análisis IA</strong><br>{diagnostico.get('resumen_gerencial', '')}</div>",
                        unsafe_allow_html=True)

        salud, n_faltantes = calcular_salud(df_norm)
        color = "#16a34a" if salud >= 95 else "#d97706" if salud >= 80 else "#dc2626"
        st.markdown(
            f"<span class='health-badge' style='background:{color}22;color:{color}'>"
            f"🩺 Salud de datos: {fmt_es(salud, 1)} %</span>&nbsp;&nbsp;"
            f"<span style='color:#64748b;font-size:13px'>{fmt_es(n_faltantes, 0)} valores faltantes · "
            f"{len(df_norm.columns)} columnas · {fmt_es(len(df_norm), 0)} registros</span>",
            unsafe_allow_html=True,
        )

        if advertencias:
            with st.expander(f"⚠️ {len(advertencias)} advertencia(s) detectada(s)"):
                for a in advertencias:
                    st.markdown(f"<div class='warn-box'>{a}</div>", unsafe_allow_html=True)

        construir_kpis(df_norm, semantica)
        st.markdown("<br>", unsafe_allow_html=True)

        tab_datos, tab_dash = st.tabs(["🗄️ EXPLORADOR DE DATOS", "📊 DASHBOARD INTELIGENTE"])

        # ------------------------------------------------------------------
        with tab_datos:
            vista = st.radio("Vista de datos:", ["Normalizada", "Original"], horizontal=True, key="vista_datos")
            df_base = df_norm if vista == "Normalizada" else df_con_encabezado

            st.markdown("**🔍 Filtros inteligentes (bajo demanda)**")
            df_filtrado = construir_filtros(df_base, semantica) if vista == "Normalizada" else df_base.copy()

            buscar = st.text_input("🔎 Búsqueda global", placeholder="Escribe para buscar en todas las columnas...")
            if buscar:
                mascara = df_filtrado.astype(str).apply(
                    lambda fila: fila.str.contains(buscar, case=False, na=False)
                ).any(axis=1)
                df_filtrado = df_filtrado[mascara]
                st.caption(f"🔎 {fmt_es(len(df_filtrado), 0)} coincidencias para «{buscar}»")

            # Visibilidad de columnas (para tablas anchas)
            if len(df_filtrado.columns) > 10:
                with st.expander("👁️ Columnas visibles"):
                    cc1, cc2, _ = st.columns([1, 1, 4])
                    opciones_actuales = list(df_filtrado.columns)
                    
                    if cc1.button("Mostrar todas"):
                        st.session_state["cols_visibles"] = opciones_actuales
                    if cc2.button("Ocultar todas"):
                        st.session_state["cols_visibles"] = []
                        
                    # PARCHE DE SEGURIDAD: Solo aplicar predeterminados que existan en la tabla actual
                    defaults_guardados = st.session_state.get("cols_visibles", opciones_actuales)
                    defaults_seguros = [c for c in defaults_guardados if c in opciones_actuales]

                    cols_visibles = st.multiselect(
                        "Columnas a mostrar:", 
                        options=opciones_actuales,
                        default=defaults_seguros,
                        key="cols_visibles",
                    )
            else:
                cols_visibles = list(df_filtrado.columns)

            exportar(df_con_encabezado, df_norm)

            df_pagina = paginar(df_filtrado[cols_visibles] if cols_visibles else df_filtrado.iloc[:, 0:0],
                                 tam_pagina, key="pag_tabla")

            config_cols = construir_column_config(df_pagina, semantica, nombres_visibles, decimales_cfg, formato_fecha) \
                if vista == "Normalizada" else None
            st.dataframe(
                df_pagina,
                column_config=config_cols,
                use_container_width=True,
                hide_index=True,
                height=560 if densidad == "Estándar" else 420,
            )

        # ------------------------------------------------------------------
        with tab_dash:
            st.markdown("**📈 Analítica automatizada**")
            graficos_automaticos(df_norm, semantica, key_prefix="dash")

    except Exception as e:
        st.error("🚨 COLAPSO DEL SISTEMA DETECTADO")
        st.error(f"Falla: {e}")
        st.code(traceback.format_exc(), language="python")


# ==============================================================================
# Este módulo NO define un punto de entrada main() ni llama a st.set_page_config().
# Está pensado para ser importado como modulos.m1_dashboard desde tu app.py maestro,
# que ya se encarga del login, la carga multi-archivo y la configuración global de
# la página. El único punto de entrada público es:
#
#     ejecutar(df_crudo, fuente_activa=None)
# ==============================================================================
