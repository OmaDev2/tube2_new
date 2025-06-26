# app.py
import streamlit as st
import sys
from pathlib import Path

# Añadir el directorio raíz al sys.path para asegurar que los módulos locales se encuentren
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from pages.batch_page import render_batch
from pages.video_generator import show_video_generator
from pages.video_generator_page import render_video_generator
from pages.prompts_manager_page import render_prompts_manager
from pages.settings_page import render_settings

import logging # Importar logging

# Configurar logging básico para app.py
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# --- Configuración de la Página ---
st.set_page_config(
    page_title="Video Generator", 
    page_icon="🎥", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Inicialización de Session State ---
if "batch_projects" not in st.session_state:
    st.session_state.batch_projects = []

if "batch_cfg_vid_dur_manual_ui" not in st.session_state:
    st.session_state.batch_cfg_vid_dur_manual_ui = 10.0  # Valor por defecto

# --- Función Principal de la App ---
def main():
    try:
        from utils.config import load_config
        app_config = load_config()
        if not app_config:
            raise ValueError("Configuración vacía o inválida.")
    except Exception as load_err:
        st.error(f"Error cargando configuración: {load_err}")
        return

    st.sidebar.title("Navegación")
    page = st.sidebar.radio("Selecciona una página", [
        "🚀 Procesador por Lotes", 
        "🎥 Generador Individual", 
        "📝 Generador de Videos", 
        "📋 Gestor de Prompts", 
        "⚙️ Configuración de APIs", 
        "📊 Historial"
    ])
    
    # --- Navegación ---
    try:
        if page == "🚀 Procesador por Lotes":
            render_batch(app_config)
        elif page == "🎥 Generador Individual":
            show_video_generator()
        elif page == "📝 Generador de Videos":
            render_video_generator(app_config)
        elif page == "📋 Gestor de Prompts":
            render_prompts_manager(app_config)
        elif page == "⚙️ Configuración de APIs":
            render_settings(app_config)
        elif page == "📊 Historial":
            st.warning("Historial aún no implementado")
    except Exception as e:
        st.error(f"Error en la aplicación: {e}")

if __name__ == "__main__":
    main()