"""
MOTOR DE NEGOCIO (LECTURA PLANA UNIVERSAL)
===========================================
- Ya NO asume encabezados piramidales/jerárquicos de varias filas.
- Toma la fila 1 del archivo como encabezado (como cualquier Excel normal
  de un hotel, restaurante o negocio pequeño) y limpia la matriz.
- Elimina filas/columnas vacías, homogeniza texto, detecta columnas
  numéricas (soporta $, %, comas) y elimina duplicados automáticamente.
- Permite crear "Campos Calculados" (fórmulas) entre columnas.
"""
import re
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

VALORES_NULOS = {"none", "nan", "nat", "null", "n/a", "#n/a", "-", "--", ""}
PALETA_CORP = ["#eab308", "#3b82f6", "#10b981", "#6366f1", "#f43f5e", "#8b5cf6"]


def format_latam(valor):
    if pd.isna(valor) or valor == "":
        return ""
    try:
        v = float(valor)
        if v.is_integer():
            return f"{int(v):,}".replace(",", ".")
        else:
            return f"{v:,.2f}".replace(",", "§").replace(".", ",").replace("§", ".")
    except Exception:
        return str(valor)


def format_kpi(val):
    if pd.isna(val) or val == "":
        return "0"
    try:
        v = float(val)
    except Exception:
        return str(val)

    if abs(v) >= 1_000_000_000:
        return f"{v/1_000_000_000:,.2f} B".replace(",", "§").replace(".", ",").replace("§", ".")
    elif abs(v) >= 1_000_000:
        return f"{v/1_000_000:,.2f} M".replace(",", "§").replace(".", ",").replace("§", ".")
    else:
        return f"{v:,.0f}".replace(",", "§").replace(".", ",").replace("§", ".")


def limpiar_datos_planos(df_raw: pd.DataFrame, eliminar_duplicados: bool = True):
    """Lectura y limpieza PLANA (sin jerarquías). Devuelve (df_limpio, origen, stats)."""
    df = df_raw.copy()
    origen = "Archivo Base"
    if "_Origen_Archivo" in df.columns:
        no_nulos = df["_Origen_Archivo"].dropna()
        origen = str(no_nulos.iloc[0]) if not no_nulos.empty else origen
        df = df.drop(columns=["_Origen_Archivo"])

    filas_originales = len(df)

    # 1. Quitar filas/columnas 100% vacías
    df = df.dropna(how="all", axis=0).dropna(how="all", axis=1)

    # 2. Limpiar nombres de columnas (encabezado = fila 1, formato plano)
    nuevas_cols = []
    conteo = {}
    for i, col in enumerate(df.columns):
        nombre = str(col).strip()
        if nombre == "" or nombre.lower().startswith("unnamed"):
            nombre = f"Columna_{i + 1}"
        nombre = " ".join(nombre.split())
        if nombre in conteo:
            conteo[nombre] += 1
            nombre = f"{nombre} ({conteo[nombre]})"
        else:
            conteo[nombre] = 0
        nuevas_cols.append(nombre)
    df.columns = nuevas_cols

    # 3. Limpiar texto y valores nulos disfrazados ("N/A", "-", etc.)
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].map(lambda v: v.strip() if isinstance(v, str) else v)
            df[col] = df[col].map(lambda v: np.nan if str(v).strip().lower() in VALORES_NULOS else v)

    # 4. Detectar y convertir columnas numéricas (soporta $, %, espacios y comas)
    for col in df.columns:
        if df[col].dtype == "object":
            serie_str = df[col].dropna().astype(str).str.replace(r"[$\s%]", "", regex=True).str.replace(",", ".")
            num = pd.to_numeric(serie_str, errors="coerce")
            if len(serie_str) > 0 and num.notna().sum() / len(serie_str) > 0.5:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(r"[$\s%]", "", regex=True).str.replace(",", "."), errors="coerce")

    # 5. Deduplicar
    duplicados_eliminados = 0
    if eliminar_duplicados:
        filas_pre = len(df)
        df = df.drop_duplicates()
        duplicados_eliminados = filas_pre - len(df)

    df = df.reset_index(drop=True)
    stats = {
        "filas_originales": filas_originales,
        "filas_finales": len(df),
        "duplicados_eliminados": duplicados_eliminados,
    }
    return df, origen, stats


def generar_tabla_html(df: pd.DataFrame) -> str:
    html = """
    <div style="overflow: auto; max-height: 60vh; border: 1px solid #1f2937; border-radius: 8px; margin-bottom: 20px;">
        <table style="width: 100%; border-collapse: collapse; font-family: 'Rajdhani', sans-serif; background-color: #0b1120; color: #f3f4f6; text-align: center; font-size: 14px;">
            <thead style="background-color: #1e293b; position: sticky; top: 0; z-index: 10;">
                <tr>
    """
    for col in df.columns:
        html += f"<th style='padding: 12px 15px; border: 1px solid #334155; color: #eab308; font-weight: 700; white-space: nowrap;'>{col}</th>"
    html += "</tr></thead><tbody>"
    for _, row in df.iterrows():
        html += "<tr style='border-bottom: 1px solid #1f2937;'>"
        for col in df.columns:
            val = row[col]
            val_str = "" if pd.isna(val) or val == "" else (format_latam(val) if isinstance(val, (int, float)) else str(val))
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
        .source-badge { display: inline-block; background: #1e293b; border: 1px solid #334155; color: #94a3b8; padding: 4px 12px; border-radius: 4px; font-family: 'Rajdhani', sans-serif; font-size: 13px; font-weight: 700; margin-bottom: 10px; }
        .stat-badge { display: inline-block; background: #111827; border: 1px solid #1f2937; color: #34d399; padding: 4px 12px; border-radius: 4px; font-family: 'Rajdhani', sans-serif; font-size: 13px; font-weight: 700; margin-bottom: 18px; margin-left: 8px; }
        .kpi-card { background: #111827; padding: 18px 15px; border-radius: 8px; border: 1px solid #1f2937; border-top: 3px solid #3b82f6; display: flex; flex-direction: column; justify-content: center; min-height: 100px; margin-bottom: 15px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.5); }
        .kpi-title { font-family: 'Rajdhani', sans-serif; font-size: 13px; color: #9ca3af; font-weight: 700; text-transform: uppercase; line-height: 1.3; }
        .kpi-val { font-family: 'Orbitron', sans-serif; font-size: 24px; color: #f3f4f6; font-weight: 800; margin-top: 6px; }
        .chart-box { background: #111827; padding: 20px; border-radius: 10px; border: 1px solid #1f2937; margin-bottom: 25px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        .chart-header { background-color: #1e293b; padding: 10px 15px; border-radius: 6px; margin-bottom: 15px; display: inline-block; border-left: 4px solid #eab308; }
        .chart-title { color:#eab308; font-family: 'Orbitron', sans-serif; font-size: 14px; font-weight: 800; letter-spacing: 0.5px; margin: 0; }
    </style>
    """, unsafe_allow_html=True)


def _aplicar_campos_calculados(df: pd.DataFrame, formulas: list) -> pd.DataFrame:
    df = df.copy()
    for f in formulas:
        try:
            col1 = df[f["col1"]].astype(float)
            if f["modo"] == "columna":
                col2 = df[f["col2"]].astype(float)
            else:
                col2 = float(f["valor"])

            if f["op"] == "+":
                df[f["nombre"]] = col1 + col2
            elif f["op"] == "-":
                df[f["nombre"]] = col1 - col2
            elif f["op"] == "×":
                df[f["nombre"]] = col1 * col2
            elif f["op"] == "÷":
                df[f["nombre"]] = col1 / col2.replace(0, np.nan) if hasattr(col2, "replace") else (col1 / col2 if col2 != 0 else np.nan)
            elif f["op"] == "% de":
                df[f["nombre"]] = col1 * (col2 / 100.0)
        except Exception:
            pass
    return df


def ejecutar(df_base, fuente_activa=None):
    inyectar_css()

    if df_base is None or df_base.empty:
        st.markdown("<div class='title-bar'>CENTRO DE MANDO</div>", unsafe_allow_html=True)
        st.markdown("""
        <div style='background: #111827; border-left: 4px solid #3b82f6; padding: 40px; border-radius: 8px; margin-top: 20px; text-align: center;'>
            <h2 style='color: #f3f4f6; font-family: Orbitron; margin-bottom: 15px;'>EN ESPERA DE DATOS</h2>
            <p style='color: #9ca3af; font-family: Rajdhani; font-size: 18px; line-height: 1.6;'>
                Sube tu Excel o CSV (ventas de un restaurante, reservas de un hotel, inventario, etc.)
                y el sistema construirá los selectores automáticamente.
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    clave_fuente = f"{fuente_activa}_{len(df_base)}"
    if "ultima_fuente_dash" not in st.session_state or st.session_state["ultima_fuente_dash"] != clave_fuente:
        st.session_state["ultima_fuente_dash"] = clave_fuente
        st.session_state.setdefault("formulas_por_fuente", {})

    c_opt1, c_opt2 = st.columns([1, 3])
    eliminar_dup = c_opt1.toggle("🧹 Auto-eliminar duplicados", value=True)

    with st.spinner("Procesando datos..."):
        df_norm, origen, stats = limpiar_datos_planos(df_base, eliminar_duplicados=eliminar_dup)
        if df_norm.empty:
            st.error("⚠️ El archivo quedó vacío tras la limpieza. Revisa que tenga encabezados en la primera fila.")
            st.stop()

    # --- Campos calculados (fórmulas) persistentes por fuente ---
    formulas_dict = st.session_state.setdefault("formulas_por_fuente", {})
    formulas = formulas_dict.setdefault(origen, [])
    df_norm = _aplicar_campos_calculados(df_norm, formulas)

    cols_num = [c for c in df_norm.columns if pd.api.types.is_numeric_dtype(df_norm[c])]
    cols_cat = [c for c in df_norm.columns if c not in cols_num]
    opciones_eje_x = cols_cat if cols_cat else cols_num[:1]

    st.markdown("<div class='title-bar'>CENTRO DE MANDO E INTELIGENCIA</div>", unsafe_allow_html=True)
    st.markdown(
        f"<div class='source-badge'>📁 ARCHIVO ACTIVO: {origen}</div>"
        f"<div class='stat-badge'>🗑️ {stats['duplicados_eliminados']} duplicados eliminados · {stats['filas_finales']} filas finales</div>",
        unsafe_allow_html=True,
    )

    tab_dash, tab_formulas, tab_datos = st.tabs(["🚀 DASHBOARD", "➕ CAMPOS CALCULADOS", "🗄️ MATRIZ DE DATOS"])

    with tab_dash:
        if not cols_num:
            st.warning("⚠️ No se detectaron columnas numéricas para graficar. Ve a '➕ Campos Calculados' o revisa tu archivo.")
        else:
            st.markdown("<h4 style='color: #38bdf8; font-family: Orbitron; font-size: 16px;'>⚙️ CONSTRUCTOR DEL LIENZO</h4>", unsafe_allow_html=True)

            c1, c2 = st.columns([1, 1.4])
            eje_x = c1.selectbox("📌 1. Analizar por (Eje X):", options=opciones_eje_x)

            df_filtrado = df_norm.copy()
            col_tiempo = next((c for c in df_norm.columns if any(w in c.lower() for w in ['fecha', 'date', 'mes', 'periodo', 'semana', 'dia', 'día'])), None)

            if col_tiempo is not None:
                serie_fecha = pd.to_datetime(df_filtrado[col_tiempo], errors="coerce")
                if serie_fecha.notna().sum() / max(len(serie_fecha), 1) > 0.5:
                    min_f, max_f = serie_fecha.min(), serie_fecha.max()
                    if pd.notna(min_f) and pd.notna(max_f) and min_f < max_f:
                        rango = c2.date_input("📅 Rango de fechas:", value=(min_f.date(), max_f.date()))
                        if isinstance(rango, tuple) and len(rango) == 2:
                            mask = (serie_fecha.dt.date >= rango[0]) & (serie_fecha.dt.date <= rango[1])
                            df_filtrado = df_filtrado[mask.fillna(False)]
                elif pd.api.types.is_numeric_dtype(df_filtrado[col_tiempo]):
                    valores = df_filtrado[col_tiempo].dropna()
                    if not valores.empty and valores.min() < valores.max():
                        rango = c2.slider("📅 Rango de análisis:", float(valores.min()), float(valores.max()), (float(valores.min()), float(valores.max())))
                        df_filtrado = df_filtrado[df_filtrado[col_tiempo].between(rango[0], rango[1])]

            metricas_sel = st.multiselect("📊 2. Selecciona las métricas a visualizar:", options=cols_num, default=cols_num[:2])

            st.markdown("<hr style='border-color: #1f2937;'>", unsafe_allow_html=True)

            if not metricas_sel:
                st.info("📌 Selecciona una o más métricas para desplegar el análisis.")
            else:
                kpi_cols = st.columns(min(len(metricas_sel), 4))
                for i, m_col in enumerate(metricas_sel[:4]):
                    total_val = df_filtrado[m_col].sum()
                    with kpi_cols[i]:
                        st.markdown(f"""
                        <div class='kpi-card'>
                            <div class='kpi-title'>{m_col}</div>
                            <div class='kpi-val'>{format_kpi(total_val)}</div>
                        </div>
                        """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                for i in range(0, len(metricas_sel), 2):
                    grid = st.columns(2)
                    for j in range(2):
                        if i + j < len(metricas_sel):
                            m_col = metricas_sel[i + j]

                            with grid[j]:
                                st.markdown("<div class='chart-box'>", unsafe_allow_html=True)
                                c_hdr, c_tipo = st.columns([1.5, 1.0])
                                c_hdr.markdown(f"<div class='chart-header'><p class='chart-title'>{m_col.upper()}</p></div>", unsafe_allow_html=True)
                                tipo_grafico = c_tipo.selectbox("Tipo:", ["Barras", "Líneas", "Área", "Dona"], key=f"g_{m_col}", label_visibility="collapsed")

                                df_g = df_filtrado.groupby(eje_x)[m_col].sum().reset_index(name='Valor')
                                df_g['Orden'] = df_g[eje_x].apply(lambda x: float(x) if str(x).replace('.', '', 1).isdigit() else str(x))
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

    with tab_formulas:
        st.markdown("<h4 style='color: #38bdf8; font-family: Orbitron; font-size: 16px;'>➕ CREAR CAMPO CALCULADO</h4>", unsafe_allow_html=True)
        st.caption("Ejemplos: Utilidad = Ingreso - Costo · Precio con IVA = Precio × 1.19 · Comisión = Venta × 0.10")

        if not cols_num:
            st.info("No hay columnas numéricas todavía para crear fórmulas.")
        else:
            fc1, fc2, fc3, fc4 = st.columns([1.2, 0.8, 1.2, 1])
            col1_sel = fc1.selectbox("Columna A:", options=cols_num, key="f_col1")
            op_sel = fc2.selectbox("Operación:", ["+", "-", "×", "÷", "% de"], key="f_op")
            modo = fc3.radio("Con:", ["Columna", "Valor fijo"], horizontal=True, key="f_modo")

            if modo == "Columna":
                col2_sel = fc3.selectbox("Columna B:", options=[c for c in cols_num if c != col1_sel] or cols_num, key="f_col2")
                valor_fijo = None
            else:
                valor_fijo = fc3.number_input("Valor:", value=1.0, key="f_valor")
                col2_sel = None

            nombre_sugerido = f"{col1_sel} {op_sel} {col2_sel if col2_sel else valor_fijo}"
            nombre_campo = fc4.text_input("Nombre del campo:", value=nombre_sugerido, key="f_nombre")

            if st.button("✅ Agregar campo calculado", type="primary"):
                nueva_formula = {
                    "nombre": nombre_campo.strip() or nombre_sugerido,
                    "col1": col1_sel,
                    "op": op_sel,
                    "modo": "columna" if modo == "Columna" else "valor",
                    "col2": col2_sel,
                    "valor": valor_fijo,
                }
                formulas.append(nueva_formula)
                st.success(f"Campo '{nueva_formula['nombre']}' agregado.")
                st.rerun()

        if formulas:
            st.markdown("<hr style='border-color: #1f2937;'>", unsafe_allow_html=True)
            st.markdown("**Campos calculados activos:**")
            for idx, f in enumerate(formulas):
                detalle = f"{f['col1']} {f['op']} {f['col2'] if f['modo'] == 'columna' else f['valor']}"
                c_a, c_b = st.columns([4, 1])
                c_a.write(f"🔹 **{f['nombre']}** = {detalle}")
                if c_b.button("🗑️ Quitar", key=f"del_form_{idx}"):
                    formulas.pop(idx)
                    st.rerun()

    with tab_datos:
        st.markdown("<h4 style='color: #38bdf8; font-family: Orbitron; font-size: 16px;'>🗄️ MATRIZ PLANA</h4>", unsafe_allow_html=True)
        st.markdown(generar_tabla_html(df_norm), unsafe_allow_html=True)
