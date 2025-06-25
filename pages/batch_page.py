# pages/batch_page.py
import streamlit as st
import sys
from pathlib import Path

# Añadir el directorio raíz del proyecto al sys.path
# Esto permite que el script encuentre la carpeta 'utils'
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Aquí puedes empezar a importar módulos de utils/
# Ejemplo: from utils.config import load_config
# Ejemplo: from utils.ai_services import AIServices

def render_batch(app_config):
    st.title("⚙️ Procesamiento por Lotes (Batch)")
    st.write("Esta página permitirá configurar y ejecutar el procesamiento de múltiples videos.")
    # Aquí irá la lógica de la interfaz para el procesamiento batch
    pass
