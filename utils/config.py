# utils/config.py
import streamlit as st
import yaml
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Ruta al config.yaml en el directorio RAÍZ
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"

# --- ÚNICA FUENTE DE VERDAD PARA LA CONFIGURACIÓN POR DEFECTO ---
DEFAULT_CONFIG = {
    "ai": {
        "openai_api_key": "TU_CLAVE_OPENAI_AQUI",
        "gemini_api_key": "TU_CLAVE_GEMINI_AQUI",
        "replicate_api_key": "TU_CLAVE_REPLICATE_AQUI",
        "ollama_base_url": "http://localhost:11434",
        "default_models": {
            "openai": "gpt-4o-mini",
            "gemini": "models/gemini-1.5-flash-latest",
            "ollama": "llama3",
            "image_generation": "black-forest-labs/flux-schnell",
            "image_prompt_generation": "models/gemini-1.5-flash-latest",
            "default_voice": "es-ES-AlvaroNeural"
        }
    },
    "tts": {
        "default_provider": "edge",
        "edge": {
            "default_voice": "es-ES-AlvaroNeural",
            "default_rate": "+0%",
            "default_pitch": "+0Hz"
        },
        "fish_audio": {
            "api_key": "TU_CLAVE_FISH_AUDIO_AQUI",
            "default_model": "speech-1.6",
            "default_format": "mp3",
            "default_mp3_bitrate": 128,
            "default_normalize": True,
            "default_latency": "normal",
            "reference_id": None
        }
    },
    "video_generation": {
        "quality": {
            "resolution": "1920x1080",
            "fps": 24,
            "bitrate": "5000k",
            "audio_bitrate": "192k"
        },
        "paths": {
            "projects_dir": "projects",
            "assets_dir": "overlays",
            "output_dir": "output",
            "background_music_dir": "background_music"
        },
        "subtitles": {
            "enable": True,
            "font": "Arial",
            "font_size": 24,
            "font_color": "#FFFFFF",
            "stroke_color": "#000000",
            "stroke_width": 1.5,
            "position": "bottom",
            "max_words": 7
        },
        "transitions": {
            "default_type": "dissolve",
            "default_duration": 1.0
        },
        "audio": {
            "default_music_volume": 0.08,
            "normalize_audio": True
        }
    },
    "transcription": {
        "service_type": "local",  # "local" o "replicate"
        "local": {
            "model_size": "medium",
            "device": "cpu",
            "compute_type": "int8",
            "default_language": "es",
            "beam_size": 5
        },
        "replicate": {
            "default_language": "es",
            "task": "transcribe",
            "timestamp": "chunk",
            "batch_size": 24,
            "diarise_audio": False,
            "hf_token": None
        }
    },
    "output_dir": "output",
    "projects_dir": "projects",
    "temp_dir": "temp",
    "background_music_dir": "background_music"
}

# --- Funciones ---

@st.cache_data(ttl=60) # Cachear por 1 minuto para reflejar cambios recientes
def load_config() -> dict:
    """
    Carga config.yaml. Si no existe, lo crea con los valores de DEFAULT_CONFIG.
    Si existe pero le faltan claves, las añade desde DEFAULT_CONFIG.
    """
    if not CONFIG_PATH.exists():
        logger.warning(f"No se encontró {CONFIG_PATH}. Creando archivo de configuración por defecto.")
        try:
            with open(CONFIG_PATH, "w", encoding='utf-8') as f:
                yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            logger.info(f"Archivo config.yaml creado en {CONFIG_PATH}. Por favor, edita tus claves de API.")
            return DEFAULT_CONFIG
        except Exception as e:
            logger.error(f"No se pudo crear config.yaml: {e}")
            return DEFAULT_CONFIG

    try:
        with open(CONFIG_PATH, "r", encoding='utf-8') as f:
            user_config = yaml.safe_load(f)
            if not isinstance(user_config, dict):
                logger.error(f"El archivo {CONFIG_PATH} está corrupto o no es un diccionario. Usando configuración por defecto.")
                return DEFAULT_CONFIG

        # Fusionar la configuración del usuario con la por defecto para asegurar que todas las claves existan
        config = _merge_configs(DEFAULT_CONFIG, user_config)
        
        logger.info(f"Configuración cargada y validada desde {CONFIG_PATH}")
        return config

    except (yaml.YAMLError, IOError) as e:
        logger.error(f"Error al leer o parsear {CONFIG_PATH}: {e}. Usando configuración por defecto.")
        return DEFAULT_CONFIG

def save_config(config_data: dict) -> bool:
    """Guarda el diccionario de configuración en config.yaml."""
    try:
        # Crear directorios necesarios antes de guardar
        _create_project_dirs(config_data)

        with open(CONFIG_PATH, "w", encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        # Limpiar la caché para que la próxima lectura obtenga los datos nuevos
        load_config.clear()
        logger.info(f"Configuración guardada exitosamente en {CONFIG_PATH}")
        st.success("¡Configuración guardada exitosamente!")
        return True
    except Exception as e:
        logger.error(f"Error al guardar la configuración en {CONFIG_PATH}: {e}")
        st.error(f"Error al guardar la configuración: {e}")
        return False

def _merge_configs(default: dict, user: dict) -> dict:
    """
    Combina recursivamente la configuración del usuario con la por defecto.
    Las claves del usuario tienen prioridad.
    """
    merged = default.copy()
    for key, value in user.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_configs(merged[key], value)
        else:
            merged[key] = value
    return merged

def _create_project_dirs(config: dict):
    """Crea los directorios definidos en la configuración si no existen."""
    paths = config.get("video_generation", {}).get("paths", {})
    for key, path_str in paths.items():
        try:
            Path(path_str).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"No se pudo crear el directorio '{path_str}' definido en la configuración: {e}")

def get_config() -> dict:
    """Función de conveniencia para obtener la configuración actual."""
    return load_config()
