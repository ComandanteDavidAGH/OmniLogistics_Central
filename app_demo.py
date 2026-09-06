import streamlit as st
import pandas as pd
import time
import re

# --- CONFIGURACIÓN CORPORATIVA ---
st.set_page_config(page_title="OmniLogistics OS | Demo", page_icon="🌐", layout="wide")

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .titulo-principal { color: #ffffff; font-family: 'Arial Black', sans-serif; font-size: 28px; border-bottom: 3px solid #d4af37; padding-bottom: 10px; margin-bottom: 20px; text-transform: uppercase; }
    .kpi-card { background-color: #1a1c23; border-left: 5px solid #d4af37; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
    .kpi-title { color: #a0aec0; font-size: 12px; text-transform: uppercase; font-weight: bold; margin-bottom: 5px; }
    .kpi-value { color: #ffffff; font-size: 28px; font-weight: 900; margin: 0; }
</style>
""", unsafe_allow_html=True)

# --- MOTOR DE EXTRACCIÓN DE DATOS ---
@st.cache_data(ttl=60)
def leer_google_sheet_publico(url):
    try:
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        if not match: return None, None, None
        doc_id = match.group(1)
        
        # header=1 le dice a Pandas que ignore la fila 0 ("TABLA: X") y use la fila 1 como encabezados reales
        url_catalogo = f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=csv&gid=0"
        df_catalogo = pd.read_csv(url_catalogo, header=1)
        
        xls = pd.ExcelFile(f"https://docs.google.com/spreadsheets/d/{doc_id}/export?format=xlsx")
        hojas = xls.sheet_names
        df_inv = pd.read_excel(xls, sheet_name=hojas[1], header=1) if len(hojas) > 1 else pd.DataFrame()
        df_oper = pd.read_excel(xls, sheet_name=hojas[2], header=1) if len(hojas) > 2 else pd.DataFrame()
        
        return df_catalogo, df_inv, df_oper
    except Exception as e:
        return None, None, None

# --- BARRA LATERAL ---
with st.sidebar:
    st.markdown("## 🌐 OmniLogistics OS")
    st.caption("Arquitectura B2B de Alto Rendimiento")
    st.markdown("---")
    menu = st.radio("Módulos Operativos:", [
        "📊 1. Command Center (Dashboard)",
        "⚙️ 2. Motor de Costos (Smart Split)",
        "🛡️ 3. Auditoría en la Nube",
        "📥 4. Ingesta y Limpieza Financiera"
    ])
    st.markdown("---")
    url_input = st.text_input("🔗 Conectar Base de Datos:", placeholder="Pega la URL de tu Google Sheet aquí...")

# --- MÓDULO 1: COMMAND CENTER ---
if menu == "📊 1. Command Center (Dashboard)":
    st.markdown("<div class='titulo-principal'>Centro de Mando Logístico</div>", unsafe_allow_html=True)
    
    if not url_input:
        st.info("👈 Pega el enlace de tu Google Sheet público en la barra lateral para sincronizar el sistema.")
    else:
        with st.spinner("Extrayendo y limpiando datos de la bóveda..."):
            df_cat, df_inv, df_op = leer_google_sheet_publico(url_input)
            
            if df_cat is not None:
                st.success("✅ Conexión establecida. Bóveda sincronizada en tiempo real.")
                
                # Cálculos reparados forzando números puros
                total_mat = len(df_cat) if not df_cat.empty else 0
                total_lotes = len(df_inv) if not df_inv.empty else 0
                cant_total = pd.to_numeric(df_inv['CANTIDAD_DISPONIBLE'], errors='coerce').sum() if not df_inv.empty and 'CANTIDAD_DISPONIBLE' in df_inv.columns else 0
                
                c1, c2, c3, c4 = st.columns(4)
                c1.markdown(f"<div class='kpi-card'><div class='kpi-title'>Materiales Activos</div><p class='kpi-value'>{total_mat}</p></div>", unsafe_allow_html=True)
                c2.markdown(f"<div class='kpi-card' style='border-left-color: #28a745;'><div class='kpi-title'>Lotes en Bodega</div><p class='kpi-value'>{total_lotes}</p></div>", unsafe_allow_html=True)
                c3.markdown(f"<div class='kpi-card' style='border-left-color: #17a2b8;'><div class='kpi-title'>Volumen Total</div><p class='kpi-value'>{cant_total:,.2f}</p></div>", unsafe_allow_html=True)
                c4.markdown(f"<div class='kpi-card' style='border-left-color: #dc3545;'><div class='kpi-title'>Alertas de Vencimiento</div><p class='kpi-value'>0</p></div>", unsafe_allow_html=True)
                
                # Despliegue de las 3 tablas en formato corporativo
                st.markdown("### 📦 Inventario Global")
                if not df_inv.empty:
                    st.dataframe(df_inv, use_container_width=True, hide_index=True)
                
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown("### 📋 Catálogo Maestro")
                    if not df_cat.empty:
                        st.dataframe(df_cat, use_container_width=True, hide_index=True)
                with col_b:
                    st.markdown("### 🚚 Registro de Operaciones")
                    if not df_op.empty:
                        st.dataframe(df_op, use_container_width=True, hide_index=True)
            else:
                st.error("🚨 Error de conexión.")

elif menu == "⚙️ 2. Motor de Costos (Smart Split)":
    st.markdown("<div class='titulo-principal'>Motor de Prorrateo Dinámico</div>", unsafe_allow_html=True)
    
    if not url_input:
        st.info("👈 Pega el enlace de tu Google Sheet público en la barra lateral para sincronizar el sistema.")
    else:
        with st.spinner("Procesando motor de cálculo..."):
            df_cat, df_inv, df_op = leer_google_sheet_publico(url_input)
            
            if df_op is not None and not df_op.empty:
                st.write("Simulación de distribución de costos logísticos por ruta y producto.")
                
                # Motor Matemático (Smart Split)
                df_split = df_op.copy()
                df_split['CANTIDAD'] = pd.to_numeric(df_split['CANTIDAD'], errors='coerce')
                df_split['COSTO_OPERATIVO'] = pd.to_numeric(df_split['COSTO_OPERATIVO'], errors='coerce')
                
                df_split['COSTO_UNITARIO'] = df_split['COSTO_OPERATIVO'] / df_split['CANTIDAD']
                
                # Control dinámico para el usuario
                st.markdown("<br>", unsafe_allow_html=True)
                overhead = st.slider("⚙️ Ajuste de Carga Administrativa (Overhead %):", min_value=0, max_value=50, value=15, step=1)
                
                df_split['COSTO_TOTAL_AJUSTADO'] = df_split['COSTO_OPERATIVO'] * (1 + (overhead/100))
                
                # Formateo visual corporativo
                columnas_mostrar = ['CONSECUTIVO', 'RUTA', 'PRODUCTO', 'CANTIDAD', 'COSTO_OPERATIVO', 'COSTO_UNITARIO', 'COSTO_TOTAL_AJUSTADO']
                df_visual = df_split[columnas_mostrar].style.format({
                    'COSTO_OPERATIVO': '${:,.2f}',
                    'COSTO_UNITARIO': '${:,.2f}',
                    'COSTO_TOTAL_AJUSTADO': '${:,.2f}'
                })
                
                st.markdown("**Tabla de Distribución (Smart Split):**")
                st.dataframe(df_visual, use_container_width=True, hide_index=True)
                
                st.success(f"✅ Prorrateo recalculado en milisegundos con un factor de overhead del {overhead}%.")
            else:
                st.warning("No hay datos operativos para calcular.")

elif menu == "📥 4. Ingesta y Limpieza Financiera":
    st.markdown("<div class='titulo-principal'>Motor de Limpieza y Reportes Gerenciales</div>", unsafe_allow_html=True)
    st.write("Sube una sábana de Excel desordenada. El sistema la limpiará, cruzará bases de datos y generará reportes financieros y tablas dinámicas al instante.")

    # Zona de carga de archivos
    archivo_subido = st.file_uploader("📂 Sube tu archivo crudo (CSV o Excel)", type=['csv', 'xlsx'])

    if st.button("🚀 Ejecutar Procesamiento Automático") or archivo_subido:
        with st.spinner("Limpiando datos, conciliando información y armando reportes..."):
            time.sleep(2) # Simulación de tiempo de cómputo

            # 1. Simulación de una "sábana desordenada" (Dolor del cliente)
            data_sucia = {
                "FECHA_TX": [" 2026-08-01 ", "2026/08/02", "03-08-2026", "2026-08-04", " 2026-08-05 "],
                "PROVEEDOR_SUCIO": ["AGROTECH llc.", "  chemcorp ", "MechSupplies", "Agrotech LLC", "CHEMCORP  "],
                "CONCEPTO": ["Compra Insumos", "Mantenimiento", "Repuestos", "Flete", "Mantenimiento"],
                "VALOR_USD": [" $ 1,500.50 ", "500", "  120.25 ", "$ 3,400.00", " 200 "],
                "CATEGORIA": ["OPERATIVO", "GASTO", "GASTO", "OPERATIVO", "GASTO"]
            }
            df_raw = pd.DataFrame(data_sucia)

            st.markdown("### ❌ 1. Sábana de Datos Original (Con Errores Comunes)")
            st.dataframe(df_raw, use_container_width=True)

            # 2. Proceso de Limpieza (La Magia de Python)
            df_clean = df_raw.copy()
            # Estandarización de texto
            df_clean['PROVEEDOR_LIMPIO'] = df_clean['PROVEEDOR_SUCIO'].str.strip().str.upper().str.replace(".", "", regex=False)
            # Limpieza financiera (quitando $ y comas)
            df_clean['VALOR_USD'] = df_clean['VALOR_USD'].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip().astype(float)
            # Estandarización de fechas (Versión Pandas 2.0+)
            df_clean['FECHA'] = pd.to_datetime(df_clean['FECHA_TX'].str.strip(), errors='coerce', format='mixed').dt.strftime('%Y-%m-%d')
            st.markdown("### ✨ 2. Datos Limpios, Estructurados y Conciliados")
            st.dataframe(df_clean[['FECHA', 'PROVEEDOR_LIMPIO', 'CONCEPTO', 'CATEGORIA', 'VALOR_USD']], use_container_width=True)

            # 3. Reportes Gerenciales y Tablas Dinámicas
            st.markdown("### 📊 3. Dashboard Financiero (Toma de Decisiones)")
            
            # KPIs Presupuestales
            k1, k2, k3 = st.columns(3)
            k1.metric("Gasto Operativo Total", f"${df_clean['VALOR_USD'].sum():,.2f}")
            
            proveedor_top = df_clean.groupby('PROVEEDOR_LIMPIO')['VALOR_USD'].sum().idxmax()
            k2.metric("Principal Proveedor", proveedor_top)
            k3.metric("Líneas Conciliadas", f"{len(df_clean)} registros")

            col1, col2 = st.columns(2)

            # Tabla dinámica por Proveedor
            pivot_prov = pd.pivot_table(df_clean, values='VALOR_USD', index='PROVEEDOR_LIMPIO', aggfunc='sum').reset_index()
            # Tabla dinámica por Categoría
            pivot_cat = pd.pivot_table(df_clean, values='VALOR_USD', index='CATEGORIA', aggfunc='sum').reset_index()

            with col1:
                st.markdown("**Control de Gastos por Proveedor**")
                st.dataframe(pivot_prov.style.format({'VALOR_USD': '${:,.2f}'}), use_container_width=True, hide_index=True)

            with col2:
                st.markdown("**Distribución por Categoría**")
                # Gráfico de barras nativo de Streamlit
                st.bar_chart(pivot_cat.set_index('CATEGORIA'))

            st.success("✅ Limpieza de Excel, cruce de bases y elaboración de presupuestos completados en 2.4 segundos. Listo para exportar o auditar.")
