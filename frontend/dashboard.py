import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import glob
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# --- CARGA DE CONFIGURACIÓN ---
load_dotenv()

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Hurakán Dashboard Pro", layout="wide", page_icon="🌪️")

# --- IMPORTACIÓN DEL MOTOR ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
try:
    from services.processor.visualization import generate_combined_map
except ImportError as e:
    st.error(f"❌ Error al importar el motor: {e}")

# --- RUTAS DESDE EL .env ---
OUTPUT_DIR = os.getenv("MAP_OUTPUT_DIR", "./data/map_outputs")
STITCH_DIR = os.getenv("STITCH_DIR", "./data/nodes_stitch")


# --- LÓGICA DE BÚSQUEDA DEL MÁS RECIENTE ---
def get_latest_map_info():
    map_pattern = os.path.join(OUTPUT_DIR, 'map_*.html')
    list_of_maps = glob.glob(map_pattern)
    if not list_of_maps:
        return None, None
    list_of_maps.sort(reverse=True)
    latest_map_path = list_of_maps[0]
    timestamp = os.path.basename(latest_map_path).replace('map_', '').replace('.html', '')
    return latest_map_path, timestamp


# --- MANEJO DEL ESTADO (SESSION STATE) ---
if 'active_ts' not in st.session_state:
    _, init_ts = get_latest_map_info()
    st.session_state.active_ts = init_ts if init_ts else datetime.now().strftime("%Y%m%d_00")

# --- PANEL LATERAL ---
with st.sidebar:
    st.title("🌪️ Control Hurakán")
    st.markdown("---")

    st.subheader("📅 Selección de Ciclo")

    # 1. Separar el active_ts actual para el calendario
    try:
        curr_date_str = st.session_state.active_ts.split('_')[0]
        curr_hour_str = st.session_state.active_ts.split('_')[1]
        default_date = datetime.strptime(curr_date_str, "%Y%m%d")
    except:
        default_date = datetime.now()
        curr_hour_str = "00"

    # 2. Selector de Calendario
    sel_date = st.date_input("Selecciona Fecha:", value=default_date)

    # 3. Selector de Hora/Ciclo (Común en meteorología: 00, 06, 12, 18)
    sel_hour = st.selectbox("Ciclo (HH):", ["00", "06", "12", "18"],
                            index=["00", "06", "12", "18"].index(curr_hour_str) if curr_hour_str in ["00", "06", "12",
                                                                                                     "18"] else 0)

    # 4. Construir el nuevo timestamp desde el calendario
    new_ts = f"{sel_date.strftime('%Y%m%d')}_{sel_hour}"

    # 5. Mantener el input de texto por si quieren pegar uno manualmente
    manual_ts = st.text_input("O ingresa manualmente:", value=new_ts)

    if st.button("Buscar o Generar Análisis", type="primary", use_container_width=True):
        st.session_state.active_ts = manual_ts
        st.rerun()

    st.markdown("---")
    with st.expander("📂 Configuración de Rutas"):
        st.caption(f"Salida: `{OUTPUT_DIR}`")
        st.caption(f"Entrada: `{STITCH_DIR}`")

# --- LÓGICA DE PROCESAMIENTO / VISUALIZACIÓN ---
st.title("Sistema de Análisis de Trayectorias y Clústeres")

active_ts = st.session_state.active_ts

if active_ts:
    map_path = os.path.join(OUTPUT_DIR, f"map_{active_ts}.html")

    if not os.path.exists(map_path):
        with st.spinner(f"⚙️ Generando mapa para {active_ts}..."):
            try:
                generate_combined_map(active_ts, STITCH_DIR, OUTPUT_DIR)
            except Exception as e:
                st.error(f"❌ Error en el motor: {e}")

    if os.path.exists(map_path):
        csv_path = os.path.join(OUTPUT_DIR, f"cluster_report_{active_ts}.csv")
        pdf_path = os.path.join(OUTPUT_DIR, f"executive_report_{active_ts}.pdf")
        png_path = os.path.join(OUTPUT_DIR, f"static_map_{active_ts}.png")

        st.info(f"📍 Mostrando ciclo: **{active_ts}**")

        tab1, tab2 = st.tabs(["🗺️ Mapa Interactivo", "📊 Reportes y Descargas"])

        with tab1:
            with open(map_path, 'r', encoding='utf-8') as f:
                html_data = f.read()
            components.html(html_data, height=750, scrolling=True)

        with tab2:
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                st.dataframe(df, use_container_width=True)

            st.markdown("---")
            st.write("### ⬇️ Panel de Descargas")
            col_a, col_b, col_c = st.columns(3)

            with col_a:
                if os.path.exists(csv_path):
                    with open(csv_path, "rb") as f:
                        st.download_button("📊 CSV", f, file_name=f"rep_{active_ts}.csv", key="btn_csv")
                else:
                    st.button("📊 CSV N/A", disabled=True)

            with col_b:
                if os.path.exists(pdf_path):
                    with open(pdf_path, "rb") as f:
                        st.download_button("📄 PDF", f, file_name=f"ejec_{active_ts}.pdf", key="btn_pdf")
                else:
                    st.button("📄 PDF N/A", disabled=True)

            with col_c:
                if os.path.exists(png_path):
                    with open(png_path, "rb") as f:
                        st.download_button("🖼️ PNG", f, file_name=f"map_{active_ts}.png", key="btn_png")
                else:
                    st.button("🖼️ PNG N/A", disabled=True)
    else:
        st.warning(f"No se encontró el mapa para {active_ts}. Verifica que los datos existan.")