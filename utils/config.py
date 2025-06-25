# utils/config.py
import streamlit as st
import yaml
from pathlib import Path
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ruta al config.yaml en el directorio RAÍZ (donde está app.py)
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

# --- Valores por Defecto ---
# Define aquí una estructura completa por si hay que crear el archivo
DEFAULT_CONFIG = {
    "ai": {
        "openai_api_key": "TU_CLAVE_OPENAI_AQUI",
        "gemini_api_key": "TU_CLAVE_GEMINI_AQUI",
        "replicate_api_key": "TU_CLAVE_REPLICATE_AQUI",
        "ollama_base_url": "http://localhost:11434",
        "default_models": {
            "openai": "gpt-3.5-turbo",
            "openai_list": ["gpt-3.5-turbo", "gpt-4"],
            "gemini": "models/gemini-1.5-pro-latest",
            "gemini_list": ["models/gemini-1.5-pro-latest", "models/gemini-pro"],
            "ollama": "llama3",
            "ollama_list": ["llama3", "mistral"],
            "image": "flux-schnell",
            "voice": "es-MX-JorgeNeural"
        }
    },
    "storage": {
        "type": "local",
        "local_path": "./videos_generados" # Carpeta de proyectos
    },
    "video": {
        "default_resolution": "1080p",
        "default_fps": 30
    }
}

# --- Funciones ---

@st.cache_data(ttl=300) # Cachear por 5 minutos
def load_config() -> dict:
    """Carga config.yaml. Crea uno básico si no existe."""
    if not CONFIG_PATH.exists():
        logger.warning(f"No se encontró {CONFIG_PATH}. Creando archivo básico.")
        # Crear directamente el archivo default
        try:
             with open(CONFIG_PATH, "w", encoding='utf-8') as f:
                  yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
             logger.info(f"Archivo config.yaml básico creado en {CONFIG_PATH}. Por favor, edítalo.")
             # No mostrar st.warning aquí para evitar errores de Streamlit
        except Exception as e:
             # Mostrar error solo si estamos en un contexto de Streamlit activo
             try: st.error(f"No se pudo crear config.yaml: {e}")
             except: logger.error(f"No se pudo crear config.yaml: {e}")
             return DEFAULT_CONFIG # Devolver default aunque no se guardara
        return DEFAULT_CONFIG

    try:
        with open(CONFIG_PATH, "r", encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
            if config_data is None:
                 logger.warning(f"{CONFIG_PATH} está vacío. Usando configuración por defecto.")
                 return DEFAULT_CONFIG # Devolver default si está vacío

            # Validaciones mínimas (opcional pero útil)
            config_data.setdefault("storage", {}).setdefault("local_path", "./videos_generados")

            logger.info(f"Configuración cargada desde {CONFIG_PATH}")
            return config_data
    except yaml.YAMLError as e:
         logger.error(f"Error de sintaxis YAML en {CONFIG_PATH}: {e}")
         try: st.error(f"Error de sintaxis YAML en {CONFIG_PATH}: {e}. Revisa el archivo.")
         except: pass
         return DEFAULT_CONFIG # Fallback
    except Exception as e:
        logger.error(f"Error inesperado al leer {CONFIG_PATH}: {e}")
        try: st.error(f"Error inesperado al leer {CONFIG_PATH}: {e}")
        except: pass
        return DEFAULT_CONFIG # Fallback


def save_config(config_data: dict) -> bool:
    """Guarda el diccionario de configuración en config.yaml."""
    try:
        projects_dir_str = config_data.get("storage",{}).get("local_path", "./videos_generados")
        Path(projects_dir_str).mkdir(parents=True, exist_ok=True)

        with open(CONFIG_PATH, "w", encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        # Limpiar cachés relevantes
        load_config.clear()
        get_projects_dir.clear()

        logger.info(f"Configuración guardada en {CONFIG_PATH}")
        # El mensaje de éxito es mejor mostrarlo en la UI que llama a esta función
        return True
    except Exception as e:
        logger.error(f"Error al guardar la configuración en {CONFIG_PATH}: {e}")
        try: st.error(f"Error al guardar la configuración: {e}")
        except: pass
        return False

@st.cache_data(ttl=300) # Cachear la ruta
def get_projects_dir() -> Path:
     """Obtiene la ruta Path configurada para guardar proyectos. La crea si no existe."""
     cfg = load_config()
     projects_path_str = cfg.get("storage", {}).get("local_path", "./projects")
     projects_dir = Path(projects_path_str).resolve()
     try:
        projects_dir.mkdir(parents=True, exist_ok=True)
        # logger.info(f"Directorio de proyectos: {projects_dir}") # Opcional: puede ser mucho log
     except Exception as e:
          logger.error(f"No se pudo crear/acceder al directorio de proyectos: {projects_dir}. Error: {e}")
          try: st.error(f"Error con el directorio de proyectos {projects_dir}: {e}")
          except: pass
     return projects_dir