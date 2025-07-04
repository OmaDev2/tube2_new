# utils/config.py
import streamlit as st
import yaml
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Ruta al config.yaml en el directorio RAÍZ
CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

# --- CONFIGURACIÓN POR DEFECTO SIN CLAVES SENSIBLES ---
DEFAULT_CONFIG = {
    "ai": {
        "openai_api_key": "",  # Se cargará desde variable de entorno
        "gemini_api_key": "",  # Se cargará desde variable de entorno
        "replicate_api_key": "",  # Se cargará desde variable de entorno
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
        "default_provider": "fish",
        "edge": {
            "default_voice": "es-ES-AlvaroNeural",
            "default_rate": "+0%",
            "default_pitch": "+0Hz"
        },
        "fish_audio": {
            "api_key": "",  # Se cargará desde variable de entorno
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

def _load_environment_variables():
    """Carga las claves de API desde variables de entorno"""
    env_config = {}
    
    # Mapeo de variables de entorno a config
    env_mapping = {
        "OPENAI_API_KEY": ["ai", "openai_api_key"],
        "GEMINI_API_KEY": ["ai", "gemini_api_key"],
        "REPLICATE_API_KEY": ["ai", "replicate_api_key"],
        "FISH_AUDIO_API_KEY": ["tts", "fish_audio", "api_key"],
        "OLLAMA_BASE_URL": ["ai", "ollama_base_url"]
    }
    
    for env_var, config_path in env_mapping.items():
        value = os.getenv(env_var)
        if value:
            # Navegar y establecer el valor en la configuración
            current = env_config
            for key in config_path[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            current[config_path[-1]] = value
            logger.info(f"Clave cargada desde variable de entorno: {env_var}")
    
    return env_config

def load_env_file():
    """Carga el archivo .env y retorna un diccionario con las variables"""
    env_vars = {}
    if ENV_PATH.exists():
        try:
            with open(ENV_PATH, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
            logger.info(f"Archivo .env cargado desde {ENV_PATH}")
        except Exception as e:
            logger.error(f"Error al cargar archivo .env: {e}")
    return env_vars

def save_env_file(env_vars):
    """Guarda las variables de entorno en el archivo .env"""
    try:
        # Crear contenido del archivo .env
        env_content = "# Claves de API - NO SUBIR AL REPOSITORIO\n"
        env_content += "# Copia este archivo como .env y edita con tus claves reales\n\n"
        
        # Mapeo de claves de configuración a variables de entorno
        env_mapping = {
            "ai.openai_api_key": "OPENAI_API_KEY",
            "ai.gemini_api_key": "GEMINI_API_KEY", 
            "ai.replicate_api_key": "REPLICATE_API_KEY",
            "tts.fish_audio.api_key": "FISH_AUDIO_API_KEY",
            "ai.ollama_base_url": "OLLAMA_BASE_URL"
        }
        
        for config_path, env_var in env_mapping.items():
            value = _get_nested_value(env_vars, config_path.split('.'))
            if value:
                env_content += f"{env_var}={value}\n"
        
        # Guardar archivo
        with open(ENV_PATH, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        logger.info(f"Archivo .env guardado en {ENV_PATH}")
        return True
    except Exception as e:
        logger.error(f"Error al guardar archivo .env: {e}")
        return False

def _get_nested_value(data, keys):
    """Obtiene un valor anidado de un diccionario usando una lista de claves"""
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return None
    return current

def _set_nested_value(data, keys, value):
    """Establece un valor anidado en un diccionario usando una lista de claves"""
    current = data
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value

# --- Funciones ---

@st.cache_data(ttl=5) # Cachear por 5 segundos para reflejar cambios más rápido
def load_config() -> dict:
    """
    Carga config.yaml y variables de entorno.
    Si no existe config.yaml, lo crea con los valores de DEFAULT_CONFIG.
    Las claves de API se cargan desde variables de entorno.
    """
    # Cargar variables de entorno primero
    env_config = _load_environment_variables()
    
    if not CONFIG_PATH.exists():
        logger.warning(f"No se encontró {CONFIG_PATH}. Creando archivo de configuración por defecto.")
        try:
            # Fusionar configuración por defecto con variables de entorno
            merged_config = _merge_configs(DEFAULT_CONFIG, env_config)
            
            with open(CONFIG_PATH, "w", encoding='utf-8') as f:
                yaml.dump(merged_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            logger.info(f"Archivo config.yaml creado en {CONFIG_PATH}")
            logger.info("IMPORTANTE: Crea un archivo .env con tus claves de API")
            return merged_config
        except Exception as e:
            logger.error(f"No se pudo crear config.yaml: {e}")
            return _merge_configs(DEFAULT_CONFIG, env_config)

    try:
        with open(CONFIG_PATH, "r", encoding='utf-8') as f:
            user_config = yaml.safe_load(f)
            if not isinstance(user_config, dict):
                logger.error(f"El archivo {CONFIG_PATH} está corrupto o no es un diccionario. Usando configuración por defecto.")
                return _merge_configs(DEFAULT_CONFIG, env_config)

        # Fusionar: DEFAULT_CONFIG + user_config + env_config (prioridad: env > user > default)
        config = _merge_configs(DEFAULT_CONFIG, user_config)
        config = _merge_configs(config, env_config)
        
        logger.info(f"Configuración cargada desde {CONFIG_PATH} y variables de entorno")
        return config

    except (yaml.YAMLError, IOError) as e:
        logger.error(f"Error al leer o parsear {CONFIG_PATH}: {e}. Usando configuración por defecto.")
        return _merge_configs(DEFAULT_CONFIG, env_config)

def save_config(config_data: dict) -> bool:
    """Guarda el diccionario de configuración en config.yaml (sin claves sensibles)"""
    try:
        # Crear directorios necesarios antes de guardar
        _create_project_dirs(config_data)
        
        # Remover claves sensibles antes de guardar en config.yaml
        safe_config = _remove_sensitive_keys(config_data.copy())

        with open(CONFIG_PATH, "w", encoding='utf-8') as f:
            yaml.dump(safe_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        # Limpiar la caché para que la próxima lectura obtenga los datos nuevos
        load_config.clear()
        logger.info(f"Configuración guardada exitosamente en {CONFIG_PATH}")
        st.success("¡Configuración guardada exitosamente!")
        return True
    except Exception as e:
        logger.error(f"Error al guardar la configuración en {CONFIG_PATH}: {e}")
        st.error(f"Error al guardar la configuración: {e}")
        return False

def save_config_with_api_keys(config_data: dict) -> bool:
    """Guarda la configuración incluyendo claves de API en .env"""
    try:
        # Guardar configuración general en config.yaml
        success_config = save_config(config_data)
        
        # Guardar claves de API en .env
        success_env = save_env_file(config_data)
        
        if success_config and success_env:
            st.success("¡Configuración y claves de API guardadas exitosamente!")
            return True
        else:
            st.warning("Configuración guardada parcialmente. Revisa los logs.")
            return False
    except Exception as e:
        logger.error(f"Error al guardar configuración con claves: {e}")
        st.error(f"Error al guardar la configuración: {e}")
        return False

def _remove_sensitive_keys(config: dict) -> dict:
    """Remueve claves sensibles del diccionario de configuración"""
    sensitive_keys = [
        ["ai", "openai_api_key"],
        ["ai", "gemini_api_key"],
        ["ai", "replicate_api_key"],
        ["tts", "fish_audio", "api_key"]
    ]
    
    for key_path in sensitive_keys:
        current = config
        for key in key_path[:-1]:
            if key in current and isinstance(current[key], dict):
                current = current[key]
            else:
                break
        else:
            if key_path[-1] in current:
                current[key_path[-1]] = ""  # Vaciar en lugar de eliminar para mantener estructura
    
    return config

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

def get_api_key(service: str) -> str:
    """Obtiene la clave de API para un servicio específico desde variables de entorno"""
    env_mapping = {
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY", 
        "replicate": "REPLICATE_API_KEY",
        "fish_audio": "FISH_AUDIO_API_KEY"
    }
    
    env_var = env_mapping.get(service.lower())
    if env_var:
        return os.getenv(env_var, "")
    return ""
