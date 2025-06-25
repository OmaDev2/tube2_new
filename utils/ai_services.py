# utils/ai_services.py
import os
import requests
import google.generativeai as genai
import openai
import ollama
import yaml
from pathlib import Path
import replicate
import time
import logging
from typing import Union, Optional, Dict, List # Mover imports de typing al principio

# Configuración logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Cargar Configuración --- 
_config = {}
def _load_config():
    global _config
    # Siempre recargar la configuración para evitar problemas de caché
    try:
        config_path = Path(__file__).resolve().parent.parent / "config.yaml"
        if config_path.exists():
            with open(config_path, "r", encoding='utf-8') as f:
                _config = yaml.safe_load(f)
                logger.info(f"Configuración cargada desde {config_path}")
        else:
             logger.warning(f"Archivo de configuración no encontrado en {config_path}, usando valores por defecto/env vars.")
             _config = {"ai": {}}
    except Exception as e:
        logger.error(f"Error cargando config.yaml: {e}")
        _config = {"ai": {}}
    return _config

_load_config()

# --- Claves de API y Endpoints --- 
AI_CONFIG = _config.get("ai", {})
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or AI_CONFIG.get("gemini_api_key")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or AI_CONFIG.get("openai_api_key")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL") or AI_CONFIG.get("ollama_base_url")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_KEY") or AI_CONFIG.get("replicate_api_key")

# --- Clase AIServices --- 
class AIServices:
    def __init__(self):
        """Inicializa los clientes de los servicios de IA."""
        # Recargar configuración en cada inicialización
        config = _load_config()
        ai_config = config.get("ai", {})
        
        self.gemini_key = os.getenv("GEMINI_API_KEY") or ai_config.get("gemini_api_key")
        self.openai_key = os.getenv("OPENAI_API_KEY") or ai_config.get("openai_api_key")
        self.ollama_host = os.getenv("OLLAMA_BASE_URL") or ai_config.get("ollama_base_url")
        # Forzar el token correcto
        self.replicate_token = "r8_G1uMx5pxBkF3jmkTxewqHCtuW70dmyc2pA9cg"
        
        self.openai_client = None
        self.ollama_client = None
        self.replicate_client = None
        
        if self.gemini_key:
            try:
                genai.configure(api_key=self.gemini_key)
                logger.info("Cliente Gemini configurado.")
            except Exception as e:
                logger.warning(f"No se pudo configurar Gemini: {e}")
        else:
             logger.warning("GEMINI_API_KEY no encontrada.")
        
        if self.openai_key:
            try:
                self.openai_client = openai.OpenAI(api_key=self.openai_key)
                logger.info("Cliente OpenAI inicializado.")
            except Exception as e:
                logger.warning(f"No se pudo inicializar OpenAI: {e}")
        else:
             logger.warning("OPENAI_API_KEY no encontrada.")
        
        if self.ollama_host:
            try:
                 self.ollama_client = ollama.Client(host=self.ollama_host)
                 self.ollama_client.list()
                 logger.info(f"Cliente Ollama conectado en {self.ollama_host}")
            except Exception as e:
                 logger.warning(f"No se pudo conectar o configurar Ollama en {self.ollama_host}: {e}")
                 self.ollama_client = None
        else:
             logger.info("OLLAMA_BASE_URL no configurado, cliente Ollama no inicializado.")
             
        if self.replicate_token:
             try:
                  logger.info(f"Inicializando Replicate con token: {self.replicate_token[:10]}...")
                  self.replicate_client = replicate.Client(api_token=self.replicate_token)
                  logger.info("Cliente Replicate inicializado correctamente.")
             except Exception as e:
                  logger.warning(f"No se pudo inicializar Replicate: {e}")
        else:
             logger.warning("REPLICATE_API_KEY no encontrada.")

    # --- Método Principal para Generar Contenido (Texto) ---
    def generate_content(self, provider: str, model: str, system_prompt: str, user_prompt: str, **kwargs) -> str:
        """Genera contenido de texto usando el proveedor y modelo especificados."""
        provider = provider.lower()
        logger.info(f"Generando contenido con {provider} (Modelo: {model})...")
        
        if provider == "gemini":
            return self._generate_gemini_script(system_prompt, user_prompt, model)
        elif provider == "openai":
            return self._generate_openai_script(system_prompt, user_prompt, model)
        elif provider == "ollama":
            return self._generate_ollama_script(system_prompt, user_prompt, model)
        else:
            error_msg = f"[ERROR] Proveedor de contenido '{provider}' no soportado."
            logger.error(error_msg)
            return error_msg

    # --- Método Principal para Generar Imágenes ---
    def generate_image(self, prompt: str, model: str, provider: str = "replicate", **kwargs) -> Union[str, bytes]:
        """
        Genera una imagen usando el proveedor y modelo especificados.
        Actualmente enfocado en Replicate.
        """
        provider = provider.lower()
        logger.info(f"Generando imagen con {provider} (Modelo: {model})...")
        
        if provider == "replicate":
            return self._generate_image_with_replicate(prompt=prompt, model_id=model, **kwargs)
        else:
            error_msg = f"[ERROR] Proveedor de imágenes '{provider}' no soportado."
            logger.error(error_msg)
            raise ValueError(error_msg)

    # --- Métodos Privados de Generación (por proveedor) ---

    def _generate_gemini_script(self, system_prompt: str, user_prompt: str, model: str) -> str:
        # ... (resto de métodos privados sin cambios) ...
        if not self.gemini_key:
            return "[ERROR] Clave API Gemini no configurada."
        try:
            modelo = genai.GenerativeModel(model_name=model)
            full_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}" if system_prompt else user_prompt
            response = modelo.generate_content(full_prompt)
            if not response.parts:
                feedback = getattr(response, 'prompt_feedback', None)
                block_reason = getattr(feedback, 'block_reason', 'Desconocido') if feedback else 'Desconocido'
                return f"[ERROR] Respuesta Gemini vacía o bloqueada. Razón: {block_reason}."
            return response.text
        except Exception as e:
            logger.error(f"Error llamando a Gemini ({model}): {e}", exc_info=True)
            return f"[ERROR] Error al llamar a Gemini ({model}): {e}"

    def _generate_openai_script(self, system_prompt: str, user_prompt: str, model: str) -> str:
        if not self.openai_client:
            return "[ERROR] Cliente OpenAI no inicializado."
        try:
            messages = []
            if system_prompt: messages.append({"role": "system", "content": system_prompt})
            if user_prompt: messages.append({"role": "user", "content": user_prompt})
            if not messages: return "[ERROR] Se necesita system_prompt o user_prompt."

            response = self.openai_client.chat.completions.create(
                model=model,
                messages=messages
            )
            if response.choices:
                return response.choices[0].message.content.strip()
            else:
                logger.warning(f"Respuesta de OpenAI sin choices para modelo {model}. Respuesta: {response}")
                return "[ERROR] OpenAI no devolvió ninguna opción (posible filtro de contenido)."
                
        except openai.AuthenticationError:
            logger.error("Error de autenticación con OpenAI. Verifica la API Key.")
            return "[ERROR] Clave de API de OpenAI inválida."
        except openai.NotFoundError:
             logger.error(f"Modelo OpenAI no encontrado: {model}")
             return f"[ERROR] Modelo de OpenAI no encontrado: {model}"
        except openai.RateLimitError:
             logger.warning("Límite de tasa de OpenAI excedido.")
             return "[ERROR] Límite de tasa de OpenAI excedido. Espera y vuelve a intentarlo."
        except Exception as e:
             logger.error(f"Error llamando a OpenAI ({model}): {e}", exc_info=True)
             return f"[ERROR] Error al llamar a OpenAI ({model}): {e}"

    def _generate_ollama_script(self, system_prompt: str, user_prompt: str, model: str) -> str:
        if not self.ollama_client:
            return f"[ERROR] Cliente Ollama no disponible o no conectado a {self.ollama_host}."
        try:
            messages = []
            if system_prompt: messages.append({'role': 'system', 'content': system_prompt})
            if user_prompt: messages.append({'role': 'user', 'content': user_prompt})
            if not messages: return "[ERROR] Se necesita system_prompt o user_prompt."

            response = self.ollama_client.chat(model=model, messages=messages)
            return response['message']['content'].strip()

        except requests.exceptions.ConnectionError:
            logger.error(f"No se pudo conectar a Ollama en {self.ollama_host}. ¿Servicio en ejecución?")
            return f"[ERROR] No se pudo conectar a Ollama en {self.ollama_host}."
        except ollama.ResponseError as e:
             if "model not found" in str(e).lower():
                  logger.error(f"Modelo Ollama no encontrado: {model}. Ejecuta 'ollama pull {model}'")
                  return f"[ERROR] Modelo Ollama no encontrado: {model}."
             logger.error(f"Error en respuesta de Ollama ({model}): {e.error} (Status: {e.status_code})", exc_info=True)
             return f"[ERROR] Error en la respuesta de Ollama ({model})."
        except Exception as e:
             logger.error(f"Error llamando a Ollama ({model}): {e}", exc_info=True)
             return f"[ERROR] Error al llamar a Ollama ({model}): {e}"

    def _generate_image_with_replicate(self, prompt: str, model_id: str, aspect_ratio: str ="16:9", output_format: str="webp", output_quality: int=85, megapixels: str="1", num_outputs: int=1, output_path: Optional[str]=None, **kwargs) -> Union[str, bytes]:
        """Genera una imagen usando Replicate y el modelo especificado."""
        if not self.replicate_client:
             raise ValueError("Cliente Replicate no inicializado (falta API Token?).")
        
        logger.debug(f"Iniciando Replicate para modelo: {model_id}")
        
        input_params = {
            "prompt": prompt,
            "aspect_ratio": aspect_ratio,
            "output_format": output_format,
            "output_quality": output_quality,
            "num_outputs": num_outputs,
            "megapixels": megapixels,
            "go_fast": kwargs.get("go_fast", True), 
            "num_inference_steps": kwargs.get("num_inference_steps", 4), 
        }
        input_params = {k: v for k, v in input_params.items() if v is not None}

        logger.debug(f"Input para Replicate ({model_id}): {input_params}")
        try:
            output = self.replicate_client.run(model_id, input=input_params)
            if not output:
                raise ValueError("Salida vacía de Replicate.")
            
            # Replicate retorna una lista de URLs si num_outputs > 1, o una URL si num_outputs = 1
            if isinstance(output, list) and len(output) > 0:
                image_url = output[0]
            elif isinstance(output, str):
                image_url = output
            else:
                raise ValueError(f"Formato de salida inesperado de Replicate: {type(output)}")

            logger.debug(f"URL de imagen generada: {image_url}")
            
            # Descargar la imagen
            response = requests.get(image_url, timeout=60)
            response.raise_for_status()
            
            if output_path:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Imagen guardada en: {output_path}")
                return output_path
            else:
                return response.content

        except Exception as e:
            logger.error(f"Error en Replicate ({model_id}): {e}", exc_info=True)
            raise

# --- Funciones de Listado de Modelos --- 

def list_gemini_models(api_key=None):
    resolved_key = api_key or GEMINI_API_KEY
    if not resolved_key: return [("[ERROR] Clave API Gemini no proporcionada.", [])]
    try:
        genai.configure(api_key=resolved_key)
        models = genai.list_models()
        return [(m.name, m.supported_generation_methods) for m in models if 'generateContent' in m.supported_generation_methods]
    except Exception as e:
        logger.warning(f"Error listando modelos Gemini: {e}")
        return [(f"[ERROR] {e}", [])]

def list_openai_models(api_key=None):
    resolved_key = api_key or OPENAI_API_KEY
    if not resolved_key: return [("[ERROR] Clave API OpenAI no proporcionada.", [])]
    try:
        client = openai.OpenAI(api_key=resolved_key)
        models = client.models.list()
        return [(m.id, ["chat.completions"]) for m in models.data]
    except openai.AuthenticationError:
        logger.warning("Clave API OpenAI inválida al listar modelos.")
        return [("[ERROR] Clave API OpenAI inválida.", [])]
    except Exception as e:
        logger.warning(f"Error listando modelos OpenAI: {e}")
        return [(f"[ERROR] {e}", [])]

def list_ollama_models(ollama_host=None):
    resolved_host = ollama_host or OLLAMA_BASE_URL
    if not resolved_host: return [("[ERROR] Host Ollama no configurado.", [])]
    try:
        client = ollama.Client(host=resolved_host)
        response = client.list()
        models_list = response.get('models', [])
        if not models_list: return [("[WARN] No se encontraron modelos Ollama.", [])]
        return [(m['name'], ['chat']) for m in models_list if 'name' in m]
    except Exception as e:
        logger.warning(f"Error listando modelos Ollama en {resolved_host}: {e}")
        return [(f"[ERROR] No se pudo conectar a Ollama en {resolved_host}.", [])]

# --- Funciones públicas para compatibilidad con imports existentes ---

def generate_openai_script(system_prompt: str, user_prompt: str, model: str = "gpt-3.5-turbo", api_key: Optional[str] = None) -> str:
    """Función pública para generar contenido con OpenAI."""
    ai_service = AIServices()
    if api_key:
        ai_service.openai_key = api_key
        ai_service.openai_client = OpenAI(api_key=api_key)
    return ai_service._generate_openai_script(system_prompt, user_prompt, model)

def generate_gemini_script(system_prompt: str, user_prompt: str, model: str = "models/gemini-2.5-flash-lite-preview-06-17", api_key: Optional[str] = None) -> str:
    """Función pública para generar contenido con Gemini."""
    ai_service = AIServices()
    if api_key:
        ai_service.gemini_key = api_key
        genai.configure(api_key=api_key)
    return ai_service._generate_gemini_script(system_prompt, user_prompt, model)

def generate_ollama_script(system_prompt: str, user_prompt: str, model: str = "llama3.2", base_url: Optional[str] = None) -> str:
    """Función pública para generar contenido con Ollama."""
    ai_service = AIServices()
    if base_url:
        ai_service.ollama_base_url = base_url
        ai_service.ollama_client = ollama.Client(host=base_url)
    return ai_service._generate_ollama_script(system_prompt, user_prompt, model)

def generate_image_with_replicate(prompt: str, model_id: str = "black-forest-labs/flux-schnell", **kwargs) -> Union[str, bytes]:
    """Función pública para generar imágenes con Replicate."""
    ai_service = AIServices()
    return ai_service._generate_image_with_replicate(prompt, model_id, **kwargs)
