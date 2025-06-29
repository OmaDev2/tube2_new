import asyncio
import edge_tts
import os
from pathlib import Path
import tempfile
import logging
from typing import Optional, Dict, List, Any
import json

# Fish Audio imports
try:
    from fish_audio_sdk import Session, TTSRequest, ReferenceAudio
    import httpx
    import ormsgpack
    from pydantic import BaseModel, conint
    from typing import Annotated, Literal
    FISH_AUDIO_AVAILABLE = True
except ImportError:
    FISH_AUDIO_AVAILABLE = False
    logging.warning("Fish Audio SDK no disponible. Instala 'fish-audio-sdk' para usar Fish Audio TTS.")

logger = logging.getLogger(__name__)

# Fish Audio models (solo si las dependencias están disponibles)
if FISH_AUDIO_AVAILABLE:
    class ServeReferenceAudio(BaseModel):
        audio: bytes
        text: str

    class ServeTTSRequest(BaseModel):
        text: str
        chunk_length: Annotated[int, conint(ge=100, le=300, strict=True)] = 200
        format: Literal["wav", "pcm", "mp3"] = "mp3"
        mp3_bitrate: Literal[64, 128, 192] = 128
        references: list[ServeReferenceAudio] = []
        reference_id: str | None = None
        normalize: bool = True
        latency: Literal["normal", "balanced"] = "normal"

# ===== SISTEMA DE MONITOREO DE CRÉDITOS FISH AUDIO =====

class FishAudioUsageTracker:
    """Sistema de monitoreo de uso y costos de Fish Audio"""
    
    def __init__(self, config_file: str = "fish_audio_usage.json"):
        self.config_file = Path(config_file)
        self.usage_data = self._load_usage_data()
        self.cost_per_million_bytes = 15.00  # $15 por millón de bytes UTF-8
    
    def _load_usage_data(self) -> Dict:
        """Carga datos de uso desde archivo JSON"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error cargando datos de uso: {e}")
        
        # Datos por defecto
        return {
            "total_bytes_processed": 0,
            "total_cost_usd": 0.0,
            "daily_usage": {},
            "monthly_usage": {},
            "usage_history": [],
            "budget_limit": 50.0,  # $50 por defecto
            "alerts": {
                "budget_warning_threshold": 0.8,  # 80% del presupuesto
                "daily_limit_warning": 10.0  # $10 por día
            }
        }
    
    def _save_usage_data(self):
        """Guarda datos de uso en archivo JSON"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.usage_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error guardando datos de uso: {e}")
    
    def track_usage(self, text: str, model: str = "speech-1.6") -> Dict:
        """
        Registra el uso de bytes procesados y calcula costos
        
        Args:
            text (str): Texto procesado
            model (str): Modelo usado (para tracking específico)
        
        Returns:
            Dict: Información del uso registrado
        """
        # Calcular bytes UTF-8
        bytes_processed = len(text.encode('utf-8'))
        
        # Calcular costo
        cost_usd = (bytes_processed / 1_000_000) * self.cost_per_million_bytes
        
        # Obtener fecha actual
        from datetime import datetime, date
        current_date = date.today()
        current_month = current_date.strftime("%Y-%m")
        
        # Actualizar estadísticas totales
        self.usage_data["total_bytes_processed"] += bytes_processed
        self.usage_data["total_cost_usd"] += cost_usd
        
        # Actualizar uso diario
        date_str = current_date.isoformat()
        if date_str not in self.usage_data["daily_usage"]:
            self.usage_data["daily_usage"][date_str] = {
                "bytes_processed": 0,
                "cost_usd": 0.0,
                "requests": 0,
                "models_used": {}
            }
        
        daily = self.usage_data["daily_usage"][date_str]
        daily["bytes_processed"] += bytes_processed
        daily["cost_usd"] += cost_usd
        daily["requests"] += 1
        
        if model not in daily["models_used"]:
            daily["models_used"][model] = 0
        daily["models_used"][model] += 1
        
        # Actualizar uso mensual
        if current_month not in self.usage_data["monthly_usage"]:
            self.usage_data["monthly_usage"][current_month] = {
                "bytes_processed": 0,
                "cost_usd": 0.0,
                "requests": 0
            }
        
        monthly = self.usage_data["monthly_usage"][current_month]
        monthly["bytes_processed"] += bytes_processed
        monthly["cost_usd"] += cost_usd
        monthly["requests"] += 1
        
        # Agregar a historial
        usage_record = {
            "timestamp": datetime.now().isoformat(),
            "text_length": len(text),
            "bytes_processed": bytes_processed,
            "cost_usd": cost_usd,
            "model": model,
            "date": date_str
        }
        self.usage_data["usage_history"].append(usage_record)
        
        # Mantener solo los últimos 1000 registros
        if len(self.usage_data["usage_history"]) > 1000:
            self.usage_data["usage_history"] = self.usage_data["usage_history"][-1000:]
        
        # Guardar datos
        self._save_usage_data()
        
        # Verificar alertas
        alerts = self._check_alerts()
        
        return {
            "bytes_processed": bytes_processed,
            "cost_usd": cost_usd,
            "total_bytes": self.usage_data["total_bytes_processed"],
            "total_cost": self.usage_data["total_cost_usd"],
            "daily_cost": daily["cost_usd"],
            "alerts": alerts
        }
    
    def _check_alerts(self) -> List[str]:
        """Verifica si hay alertas que mostrar"""
        alerts = []
        
        # Alerta de presupuesto
        if self.usage_data["total_cost_usd"] >= self.usage_data["budget_limit"] * self.usage_data["alerts"]["budget_warning_threshold"]:
            alerts.append(f"⚠️ Has usado {self.usage_data['total_cost_usd']:.2f}$ de {self.usage_data['budget_limit']:.2f}$ ({self.usage_data['total_cost_usd']/self.usage_data['budget_limit']*100:.1f}%)")
        
        # Alerta de límite diario
        from datetime import date
        today = date.today().isoformat()
        if today in self.usage_data["daily_usage"]:
            daily_cost = self.usage_data["daily_usage"][today]["cost_usd"]
            if daily_cost >= self.usage_data["alerts"]["daily_limit_warning"]:
                alerts.append(f"⚠️ Uso diario alto: {daily_cost:.2f}$ hoy")
        
        return alerts
    
    def get_usage_summary(self) -> Dict:
        """Obtiene un resumen del uso actual"""
        from datetime import date, timedelta
        
        today = date.today().isoformat()
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        
        return {
            "total": {
                "bytes_processed": self.usage_data["total_bytes_processed"],
                "cost_usd": self.usage_data["total_cost_usd"],
                "budget_remaining": self.usage_data["budget_limit"] - self.usage_data["total_cost_usd"]
            },
            "today": self.usage_data["daily_usage"].get(today, {
                "bytes_processed": 0,
                "cost_usd": 0.0,
                "requests": 0
            }),
            "yesterday": self.usage_data["daily_usage"].get(yesterday, {
                "bytes_processed": 0,
                "cost_usd": 0.0,
                "requests": 0
            }),
            "budget_limit": self.usage_data["budget_limit"],
            "cost_per_million_bytes": self.cost_per_million_bytes
        }
    
    def set_budget_limit(self, limit_usd: float):
        """Establece el límite de presupuesto"""
        self.usage_data["budget_limit"] = limit_usd
        self._save_usage_data()
    
    def estimate_remaining_usage(self, text_length: int = None) -> Dict:
        """
        Estima cuánto texto más puedes procesar con el presupuesto restante
        
        Args:
            text_length (int): Longitud del texto a estimar (opcional)
        
        Returns:
            Dict: Estimaciones de uso restante
        """
        remaining_budget = self.usage_data["budget_limit"] - self.usage_data["total_cost_usd"]
        
        if remaining_budget <= 0:
            return {
                "can_process": False,
                "remaining_budget": 0,
                "estimated_characters": 0,
                "estimated_words": 0,
                "estimated_minutes": 0
            }
        
        # Calcular bytes que se pueden procesar
        bytes_available = (remaining_budget / self.cost_per_million_bytes) * 1_000_000
        
        # Estimaciones
        estimated_characters = int(bytes_available / 2)  # ~2 bytes por carácter
        estimated_words = int(estimated_characters / 6)  # ~6 caracteres por palabra
        estimated_minutes = int(estimated_words / 150)  # ~150 palabras por minuto
        
        result = {
            "can_process": True,
            "remaining_budget": remaining_budget,
            "estimated_characters": estimated_characters,
            "estimated_words": estimated_words,
            "estimated_minutes": estimated_minutes
        }
        
        # Si se proporciona texto específico, calcular si se puede procesar
        if text_length:
            text_bytes = text_length * 2  # Estimación
            text_cost = (text_bytes / 1_000_000) * self.cost_per_million_bytes
            result["text_cost"] = text_cost
            result["can_process_text"] = text_cost <= remaining_budget
        
        return result
    
    def reset_usage(self):
        """Reinicia todas las estadísticas de uso"""
        self.usage_data = {
            "total_bytes_processed": 0,
            "total_cost_usd": 0.0,
            "daily_usage": {},
            "monthly_usage": {},
            "usage_history": [],
            "budget_limit": self.usage_data["budget_limit"],
            "alerts": self.usage_data["alerts"]
        }
        self._save_usage_data()

# Instancia global del tracker
_fish_audio_tracker = None

def get_fish_audio_tracker() -> FishAudioUsageTracker:
    """Obtiene la instancia global del tracker de uso"""
    global _fish_audio_tracker
    if _fish_audio_tracker is None:
        _fish_audio_tracker = FishAudioUsageTracker()
    return _fish_audio_tracker

# ===== EDGE TTS FUNCTIONS =====

async def _generate_audio_chunk(text: str, voice: str, rate: str = "+0%", volume: str = "+0%", pitch: str = "+0Hz", output_file: str = None) -> str:
    """Genera un archivo de audio para un chunk de texto usando Edge TTS."""
    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
    if not output_file:
        output_file = tempfile.mktemp(suffix=".mp3")
    await communicate.save(output_file)
    return output_file

def generate_edge_tts_audio(text: str, voice: str = "es-ES-AlvaroNeural", rate: str = "+0%", pitch: str = "+0Hz", output_dir: str = "audio") -> str:
    """
    Genera un archivo de audio a partir de texto usando Edge TTS.
    
    Args:
        text (str): Texto a convertir en audio
        voice (str): Voz a utilizar (por defecto es-ES-AlvaroNeural)
        rate (str): Velocidad de habla (formato: +X% o -X%)
        pitch (str): Tono de voz (formato: +XHz o -XHz)
        output_dir (str): Directorio donde guardar el audio
    
    Returns:
        str: Ruta al archivo de audio generado
    """
    # Crear directorio de salida si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Dividir el texto en chunks de 4000 caracteres
    chunk_size = 4000
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    
    # Generar un nombre de archivo temporal único
    temp_files = []
    output_file = os.path.join(output_dir, f"audio_edge_{hash(text)}.mp3")
    
    try:
        # Generar audio para cada chunk
        for i, chunk in enumerate(chunks):
            temp_file = tempfile.mktemp(suffix=f"_chunk_{i}.mp3")
            asyncio.run(_generate_audio_chunk(
                chunk,
                voice,
                rate=rate,
                pitch=pitch,
                output_file=temp_file
            ))
            temp_files.append(temp_file)
        
        # Si hay más de un chunk, concatenarlos
        if len(temp_files) > 1:
            from moviepy.editor import concatenate_audioclips, AudioFileClip
            clips = [AudioFileClip(f) for f in temp_files]
            final_clip = concatenate_audioclips(clips)
            final_clip.write_audiofile(output_file)
            final_clip.close()
            for clip in clips:
                clip.close()
        else:
            # Si solo hay un chunk, simplemente renombrar el archivo
            import shutil
            shutil.move(temp_files[0], output_file)
        
        return output_file
    
    finally:
        # Limpiar archivos temporales
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

async def list_edge_voices():
    """Lista todas las voces disponibles en Edge TTS."""
    try:
        return await edge_tts.list_voices()
    except Exception as e:
        logger.error(f"Error obteniendo voces de Edge TTS: {e}")
        return [{"Name": "es-ES-AlvaroNeural", "Locale": "es-ES"}]  # Voz por defecto si falla

# ===== FISH AUDIO FUNCTIONS =====

def generate_fish_audio_audio(
    text: str, 
    api_key: str,
    reference_id: Optional[str] = None,
    model: str = "speech-1.6",
    format: str = "mp3",
    mp3_bitrate: int = 128,
    normalize: bool = True,
    latency: str = "normal",
    output_dir: str = "audio"
) -> str:
    """
    Genera un archivo de audio a partir de texto usando Fish Audio TTS.
    
    Args:
        text (str): Texto a convertir en audio
        api_key (str): API key de Fish Audio
        reference_id (str, optional): ID del modelo de referencia
        model (str): Modelo a usar (speech-1.5, speech-1.6, s1)
        format (str): Formato de salida (wav, pcm, mp3)
        mp3_bitrate (int): Bitrate para MP3 (64, 128, 192)
        normalize (bool): Normalizar texto
        latency (str): Modo de latencia (normal, balanced)
        output_dir (str): Directorio donde guardar el audio
    
    Returns:
        str: Ruta al archivo de audio generado
    """
    if not FISH_AUDIO_AVAILABLE:
        raise ImportError("Fish Audio SDK no está disponible. Instala 'fish-audio-sdk' para usar Fish Audio TTS.")
    
    # Crear directorio de salida si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Generar nombre de archivo único
    output_file = os.path.join(output_dir, f"audio_fish_{hash(text)}.{format}")
    
    try:
        # Trackear uso ANTES de generar audio
        tracker = get_fish_audio_tracker()
        usage_info = tracker.track_usage(text, model)
        
        # Mostrar información de uso
        logger.info(f"🐟 Fish Audio - Bytes procesados: {usage_info['bytes_processed']:,}, Costo: ${usage_info['cost_usd']:.4f}")
        
        # Mostrar alertas si las hay
        if usage_info['alerts']:
            for alert in usage_info['alerts']:
                logger.warning(f"🐟 Fish Audio Alert: {alert}")
        
        # Crear sesión de Fish Audio
        session = Session(api_key)
        
        # Crear request
        request = TTSRequest(
            reference_id=reference_id,
            text=text
        )
        
        # Generar audio
        with open(output_file, "wb") as f:
            for chunk in session.tts(request):
                f.write(chunk)
        
        logger.info(f"Audio Fish generado exitosamente: {output_file}")
        return output_file
        
    except Exception as e:
        logger.error(f"Error generando audio con Fish Audio: {e}")
        raise

def generate_fish_audio_raw_api(
    text: str,
    api_key: str,
    reference_id: Optional[str] = None,
    model: str = "speech-1.6",
    format: str = "mp3",
    mp3_bitrate: int = 128,
    normalize: bool = True,
    latency: str = "normal",
    output_dir: str = "audio"
) -> str:
    """
    Genera audio usando la API raw de Fish Audio (sin SDK).
    
    Args:
        text (str): Texto a convertir en audio
        api_key (str): API key de Fish Audio
        reference_id (str, optional): ID del modelo de referencia
        model (str): Modelo a usar (speech-1.5, speech-1.6, s1)
        format (str): Formato de salida (wav, pcm, mp3)
        mp3_bitrate (int): Bitrate para MP3 (64, 128, 192)
        normalize (bool): Normalizar texto
        latency (str): Modo de latencia (normal, balanced)
        output_dir (str): Directorio donde guardar el audio
    
    Returns:
        str: Ruta al archivo de audio generado
    """
    if not FISH_AUDIO_AVAILABLE:
        raise ImportError("Dependencias de Fish Audio no disponibles")
    
    # Crear directorio de salida si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Generar nombre de archivo único
    output_file = os.path.join(output_dir, f"audio_fish_raw_{hash(text)}.{format}")
    
    try:
        # Trackear uso ANTES de generar audio
        tracker = get_fish_audio_tracker()
        usage_info = tracker.track_usage(text, model)
        
        # Mostrar información de uso
        logger.info(f"🐟 Fish Audio (Raw API) - Bytes procesados: {usage_info['bytes_processed']:,}, Costo: ${usage_info['cost_usd']:.4f}")
        
        # Mostrar alertas si las hay
        if usage_info['alerts']:
            for alert in usage_info['alerts']:
                logger.warning(f"🐟 Fish Audio Alert: {alert}")
        
        # Crear request
        request = ServeTTSRequest(
            text=text,
            format=format,
            mp3_bitrate=mp3_bitrate,
            reference_id=reference_id,
            normalize=normalize,
            latency=latency
        )
        
        # Realizar request
        with httpx.Client() as client:
            with client.stream(
                "POST",
                "https://api.fish.audio/v1/tts",
                content=ormsgpack.packb(request, option=ormsgpack.OPT_SERIALIZE_PYDANTIC),
                headers={
                    "authorization": f"Bearer {api_key}",
                    "content-type": "application/msgpack",
                    "model": model,
                },
                timeout=None,
            ) as response:
                with open(output_file, "wb") as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)
        
        logger.info(f"Audio Fish (raw API) generado exitosamente: {output_file}")
        return output_file
        
    except Exception as e:
        logger.error(f"Error generando audio con Fish Audio (raw API): {e}")
        raise

def list_fish_audio_models() -> List[Dict[str, Any]]:
    """
    Lista los modelos disponibles de Fish Audio.
    Nota: Fish Audio no tiene una API para listar modelos, 
    pero podemos devolver los modelos conocidos.
    """
    return [
        {
            "name": "speech-1.5",
            "description": "Fish Audio Speech 1.5",
            "type": "speech"
        },
        {
            "name": "speech-1.6", 
            "description": "Fish Audio Speech 1.6 (Recomendado)",
            "type": "speech"
        },
        {
            "name": "s1",
            "description": "Fish Audio S1",
            "type": "speech"
        }
    ]

# ===== FUNCIÓN UNIFICADA DE TTS =====

def generate_tts_audio(
    text: str,
    tts_provider: str = "edge",
    voice: str = "es-ES-AlvaroNeural",
    rate: str = "+0%",
    pitch: str = "+0Hz",
    output_dir: str = "audio",
    # Fish Audio specific parameters
    fish_api_key: Optional[str] = None,
    fish_reference_id: Optional[str] = None,
    fish_model: str = "speech-1.6",
    fish_format: str = "mp3",
    fish_mp3_bitrate: int = 128,
    fish_normalize: bool = True,
    fish_latency: str = "normal"
) -> str:
    """
    Función unificada para generar audio TTS con diferentes proveedores.
    
    Args:
        text (str): Texto a convertir en audio
        tts_provider (str): Proveedor TTS ("edge" o "fish")
        voice (str): Voz para Edge TTS
        rate (str): Velocidad para Edge TTS
        pitch (str): Tono para Edge TTS
        output_dir (str): Directorio de salida
        fish_api_key (str): API key para Fish Audio
        fish_reference_id (str): ID de referencia para Fish Audio
        fish_model (str): Modelo de Fish Audio
        fish_format (str): Formato de salida para Fish Audio
        fish_mp3_bitrate (int): Bitrate MP3 para Fish Audio
        fish_normalize (bool): Normalizar texto para Fish Audio
        fish_latency (str): Latencia para Fish Audio
    
    Returns:
        str: Ruta al archivo de audio generado
    """
    if tts_provider.lower() == "edge":
        return generate_edge_tts_audio(text, voice, rate, pitch, output_dir)
    elif tts_provider.lower() == "fish":
        if not fish_api_key:
            raise ValueError("API key de Fish Audio es requerida")
        return generate_fish_audio_audio(
            text, fish_api_key, fish_reference_id, fish_model,
            fish_format, fish_mp3_bitrate, fish_normalize, fish_latency, output_dir
        )
    else:
        raise ValueError(f"Proveedor TTS no soportado: {tts_provider}")

async def list_voices(provider: str = "edge") -> List[Dict[str, Any]]:
    """
    Lista las voces disponibles según el proveedor.
    
    Args:
        provider (str): Proveedor TTS ("edge" o "fish")
    
    Returns:
        List[Dict]: Lista de voces disponibles
    """
    if provider.lower() == "edge":
        return await list_edge_voices()
    elif provider.lower() == "fish":
        return list_fish_audio_models()
    else:
        raise ValueError(f"Proveedor TTS no soportado: {provider}")

class AudioServices:
    def __init__(self):
        # Inicialización de servicios de audio
        pass
    
    def generate_voice(self, text):
        # Lógica para generar voz
        pass
    
    def transcribe_audio(self, audio_file):
        # Lógica para transcribir audio
        pass 