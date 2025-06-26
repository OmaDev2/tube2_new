# pages/batch_page.py
import streamlit as st
import sys
from pathlib import Path

# Añadir el directorio raíz del proyecto al sys.path
# Esto permite que el script encuentre la carpeta 'utils'
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Importar la función principal del procesador por lotes
from pages.batch_processor import show_batch_processor

def render_batch(app_config):
    """
    Función principal que renderiza la página de procesamiento por lotes
    """
    # Llamar a la función principal del procesador por lotes
    show_batch_processor()
