import streamlit as st
from pathlib import Path
import yaml
import sys

# Añadir el directorio raíz del proyecto al sys.path
# Esto permite que el script encuentre la carpeta 'utils'
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from utils.config import load_config

def render_settings(app_config):
    """Renderiza la página de configuración"""
    st.title("⚙️ Configuración del Proyecto")
    st.markdown("Ver y editar configuración actual")
    
    tab1, tab2 = st.tabs(["Configuración actual", "Configuración por defecto"])
    
    # --- Pestaña 1: Configuración Actual ---
    with tab1:
        try:
            voidrules_path = Path(__file__).parent.parent / ".voidrules"
            if voidrules_path.exists():
                with open(voidrules_path, "r") as f:
                    void_conf = yaml.safe_load(f)
                st.code(yaml.dump(void_conf, allow_unicode=True, default_flow_style=False), language="yaml")
            else:
                st.warning("Archivo .voidrules no encontrado")
        except Exception as e:
            st.error(f"No se pudo cargar .voidrules: {e}")
    
    # --- Pestaña 2: Configuración por defecto ---
    with tab2:
        st.markdown("### 📁 Configuración cargada del proyecto")
        try:
            if app_config:
                st.code(yaml.dump(app_config, allow_unicode=True, default_flow_style=False), language="yaml")
            else:
                st.info("Ninguna configuración cargada")
        except Exception:
            st.info("No hay configuración para mostrar")
    
    st.markdown("---")
    
    # --- Editar archivo .voidrules ---
    if st.checkbox("🛠️ Editar configuración manualmente"):
        try:
            with open(".voidrules", "r") as f:
                void_data = f.read()
            edited_config = st.text_area("Editar .voidrules", void_data, height=300)
            
            if st.button("Guardar Configuración"):
                with open(".voidrules", "w") as f:
                    f.write(edited_config)
                st.success("Configuración guardada exitosamente")
                st.rerun()
                
        except Exception as e:
            st.error(f"No se pudo cargar el archivo: {e}")

    if st.checkbox("📊 Ver información del proyecto"):
        if "loaded_project" in st.session_state:
            st.json(st.session_state.loaded_project)
        else:
            st.warning("No hay proyecto cargado")