from faster_whisper import WhisperModel
import time
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import logging
import replicate
import os
import requests

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self, model_size: str = "medium", device: str = "cpu", compute_type: str = "int8"):
        """
        Inicializa el servicio de transcripción.
        
        Args:
            model_size: Tamaño del modelo ('tiny', 'base', 'small', 'medium', 'large-v2', 'large-v3')
            device: Dispositivo de cómputo ('cpu' o 'cuda')
            compute_type: Tipo de cómputo ('int8', 'float16', 'int8_float16', 'float32')
        """
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None
        logger.info(f"Inicializando TranscriptionService con modelo {model_size} en {device}")
    
    @property
    def model(self) -> WhisperModel:
        """Carga el modelo de manera lazy cuando se necesita por primera vez."""
        if self._model is None:
            logger.info("Cargando modelo Whisper...")
            self._model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type
            )
            logger.info("Modelo Whisper cargado exitosamente")
        return self._model
    
    def transcribe_audio(
        self,
        audio_path: str,
        beam_size: int = 5,
        language: str = "es",
        progress_callback: Optional[callable] = None
    ) -> Tuple[List[Dict], Dict]:
        """
        Transcribe un archivo de audio y devuelve los segmentos con timestamps.
        
        Args:
            audio_path: Ruta al archivo de audio
            beam_size: Tamaño del beam search
            language: Código del idioma (es, en, etc.)
            progress_callback: Función para reportar el progreso
            
        Returns:
            Tuple[List[Dict], Dict]: Lista de palabras con timestamps y metadata
        """
        if not Path(audio_path).exists():
            raise FileNotFoundError(f"No se encontró el archivo de audio: {audio_path}")
        
        try:
            logger.info(f"Iniciando transcripción de {audio_path}")
            start_time = time.time()
            
            if progress_callback:
                progress_callback(0.1, "🎯 Iniciando transcripción...")
            
            # Realizar la transcripción
            segments, info = self.model.transcribe(
                audio_path,
                beam_size=beam_size,
                language=language,
                word_timestamps=True
            )
            
            if progress_callback:
                progress_callback(0.5, "📝 Procesando resultados...")
            
            # Procesar los segmentos
            all_words = []
            all_segments = []
            
            for segment in segments:
                # Guardar información del segmento
                segment_info = {
                    "text": segment.text,
                    "start": round(segment.start, 2),
                    "end": round(segment.end, 2),
                    "words": []
                }
                
                # Procesar palabras del segmento
                for word in segment.words:
                    word_info = {
                        "text": word.word,
                        "start": round(word.start, 2),
                        "end": round(word.end, 2)
                    }
                    all_words.append(word_info)
                    segment_info["words"].append(word_info)
                
                all_segments.append(segment_info)
            
            end_time = time.time()
            duration = end_time - start_time
            
            metadata = {
                "duration": duration,
                "language": info.language,
                "language_probability": info.language_probability,
                "num_words": len(all_words),
                "num_segments": len(all_segments)
            }
            
            if progress_callback:
                progress_callback(1.0, "✅ Transcripción completada")
            
            logger.info(f"Transcripción completada en {duration:.2f} segundos")
            return all_segments, metadata
            
        except Exception as e:
            logger.error(f"Error durante la transcripción: {str(e)}")
            raise
    
    def save_transcription(
        self,
        segments: List[Dict],
        metadata: Dict,
        output_path: str,
        format: str = "json"
    ) -> str:
        """
        Guarda la transcripción en un archivo.
        
        Args:
            segments: Lista de segmentos con timestamps
            metadata: Metadata de la transcripción
            output_path: Ruta donde guardar el archivo
            format: Formato de salida ('json' o 'txt')
            
        Returns:
            str: Ruta al archivo guardado
        """
        import json
        
        output_path = Path(output_path)
        if format == "json":
            data = {
                "metadata": metadata,
                "segments": segments
            }
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            # Formato de texto simple con timestamps
            with open(output_path, "w", encoding="utf-8") as f:
                for segment in segments:
                    f.write(f"[{segment['start']:.2f} - {segment['end']:.2f}] {segment['text']}\n")
        
        logger.info(f"Transcripción guardada en {output_path}")
        return str(output_path)

class ReplicateTranscriptionService:
    """
    Servicio de transcripción usando Replicate con el modelo "Incredibly Fast Whisper".
    Mucho más rápido que el Whisper tradicional y con excelente soporte multiidioma.
    """
    
    def __init__(self, api_token: Optional[str] = None):
        """
        Inicializa el servicio de transcripción de Replicate.
        
        Args:
            api_token: Token de API de Replicate (opcional, se puede usar variable de entorno)
        """
        self.api_token = api_token or os.getenv("REPLICATE_API_TOKEN")
        if not self.api_token:
            raise ValueError("Se requiere REPLICATE_API_TOKEN para usar ReplicateTranscriptionService")
        
        # Configurar Replicate
        os.environ["REPLICATE_API_TOKEN"] = self.api_token
        
        # Modelo específico de Incredibly Fast Whisper
        self.model_id = "vaibhavs10/incredibly-fast-whisper:3ab86df6c8f54c11309d4d1f930ac292bad43ace52d10c80d87eb258b3c9f79c"
        
        # Idiomas soportados
        self.supported_languages = {
            "es": "spanish",
            "en": "english", 
            "fr": "french",
            "pt": "portuguese",
            "pt-BR": "portuguese",  # Portugués brasileño
            "it": "italian"
        }
        
        logger.info("ReplicateTranscriptionService inicializado")
    
    def transcribe_audio(
        self,
        audio_path: str,
        language: str = "es",
        task: str = "transcribe",
        timestamp: str = "chunk",
        batch_size: int = 24,
        diarise_audio: bool = False,
        hf_token: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Tuple[List[Dict], Dict]:
        """
        Transcribe un archivo de audio usando Replicate Incredibly Fast Whisper.
        
        Args:
            audio_path: Ruta al archivo de audio
            language: Código de idioma (ej: 'es', 'en', 'fr')
            task: Tarea ('transcribe' o 'translate')
            timestamp: Tipo de timestamp ('chunk' o 'word')
            batch_size: Tamaño del batch para procesamiento
            diarise_audio: Si se debe hacer diarización
            hf_token: Token de Hugging Face para diarización
            progress_callback: Función de callback para progreso
            
        Returns:
            Tuple[List[Dict], Dict]: Segmentos con timestamps y metadata
        """
        import time
        from pathlib import Path
        
        start_time = time.time()
        
        try:
            logger.info(f"🚀 Iniciando transcripción con Replicate Incredibly Fast Whisper: {audio_path}")
            
            if progress_callback:
                progress_callback(0.1, "🚀 Iniciando transcripción con Replicate...")
            
            # Verificar que el archivo existe
            audio_file = Path(audio_path)
            if not audio_file.exists():
                raise FileNotFoundError(f"Archivo de audio no encontrado: {audio_path}")
            
            # Obtener nombre de idioma
            language_name = self.supported_languages.get(language, language)
            
            if progress_callback:
                progress_callback(0.2, "📤 Preparando archivo de audio...")
            
            # Usar el método correcto de Replicate: abrir el archivo directamente
            with open(audio_path, "rb") as audio_file:
                # Preparar input para Replicate
                input_params = {
                    "audio": audio_file,
                    "task": task,
                    "language": language_name,
                    "timestamp": timestamp,
                    "batch_size": batch_size,
                    "diarise_audio": diarise_audio
                }
                
                # Añadir hf_token si se proporciona
                if hf_token:
                    input_params["hf_token"] = hf_token
                
                if progress_callback:
                    progress_callback(0.3, "📡 Enviando audio a Replicate...")
                
                # Ejecutar transcripción usando el método correcto
                output = replicate.run(self.model_id, input=input_params)
                
                if progress_callback:
                    progress_callback(0.7, "📝 Procesando resultados...")
                
                # Procesar la salida
                segments, metadata = self._process_replicate_output(output, audio_path)
                
                end_time = time.time()
                duration = end_time - start_time
                
                # Añadir información de duración al metadata
                metadata["processing_duration"] = duration
                metadata["model"] = "incredibly-fast-whisper"
                metadata["provider"] = "replicate"
                
                if progress_callback:
                    progress_callback(1.0, "✅ Transcripción completada")
                
                logger.info(f"Transcripción Replicate completada en {duration:.2f} segundos")
                return segments, metadata
                
        except Exception as e:
            logger.error(f"Error durante la transcripción con Replicate: {str(e)}")
            raise
    
    def _process_replicate_output(self, output: Dict, audio_path: str) -> Tuple[List[Dict], Dict]:
        """
        Procesa la salida de Replicate y la convierte al formato estándar.
        MEJORADO: Manejo más robusto de la salida para evitar truncamientos silenciosos.
        """
        try:
            if not isinstance(output, dict) or "chunks" not in output:
                logger.error(f"Salida inesperada o incompleta de Replicate: No es un diccionario o no contiene 'chunks'. Salida: {str(output)[:500]}")
                # Devolver vacío para que el proceso falle explícitamente
                return [], {"error": "Formato de salida de Replicate inválido", "output_received": str(output)[:500]}

            chunks = output.get("chunks", [])
            if not chunks:
                logger.warning(f"Replicate devolvió una lista de 'chunks' vacía para {audio_path}. La transcripción podría estar vacía.")
                # Devolver vacío si no hay chunks, ya que no hay nada que procesar
                return [], {"error": "Lista de chunks vacía", "audio_path": audio_path}

            segments = []
            all_words = []
            full_text_from_chunks = []

            for chunk in chunks:
                if not isinstance(chunk, dict) or "text" not in chunk or "timestamp" not in chunk:
                    logger.warning(f"Saltando chunk mal formado en la respuesta de Replicate: {chunk}")
                    continue

                timestamp = chunk.get("timestamp", [0, 0])
                start_time = timestamp[0] if len(timestamp) > 0 else 0
                end_time = timestamp[1] if len(timestamp) > 1 else 0
                text = chunk.get("text", "").strip()
                
                if not text:
                    continue

                full_text_from_chunks.append(text)
                segment_info = {
                    "text": text,
                    "start": round(start_time, 2),
                    "end": round(end_time, 2),
                    "words": []
                }
                
                words = chunk.get("words", [])
                if words and isinstance(words, list):
                    for word in words:
                        if isinstance(word, dict):
                            word_info = {
                                "text": word.get("text", ""),
                                "start": round(word.get("start", 0), 2),
                                "end": round(word.get("end", 0), 2)
                            }
                            all_words.append(word_info)
                            segment_info["words"].append(word_info)
                
                segments.append(segment_info)

            # Comparar el texto completo de los chunks con el texto de nivel superior si existe
            top_level_text = output.get("text", "").strip()
            assembled_text = " ".join(full_text_from_chunks)
            if top_level_text and len(top_level_text) > len(assembled_text) * 0.9:
                 logger.info("El texto de nivel superior de Replicate parece completo, usando ese.")
            elif not segments:
                 logger.error(f"No se pudieron procesar segmentos válidos de Replicate para {audio_path}")
                 return [], {"error": "No se procesaron segmentos válidos", "audio_path": audio_path}


            metadata = {
                "language": output.get("language", "unknown"),
                "language_probability": output.get("language_probability", 0.0),
                "num_words": len(all_words),
                "num_segments": len(segments),
                "audio_path": audio_path,
                "model_id": self.model_id
            }
            
            return segments, metadata
            
        except Exception as e:
            logger.error(f"Error crítico procesando salida de Replicate para {audio_path}: {e}", exc_info=True)
            # Devolver formato básico en caso de error
            return [], {
                "language": "unknown",
                "language_probability": 0.0,
                "num_words": 0,
                "num_segments": 0,
                "audio_path": audio_path,
                "model_id": self.model_id,
                "error": str(e)
            }
    
    def save_transcription(
        self,
        segments: List[Dict],
        metadata: Dict,
        output_path: str,
        format: str = "json"
    ) -> str:
        """
        Guarda la transcripción en un archivo.
        
        Args:
            segments: Lista de segmentos con timestamps
            metadata: Metadata de la transcripción
            output_path: Ruta donde guardar el archivo
            format: Formato de salida ('json' o 'txt')
            
        Returns:
            str: Ruta al archivo guardado
        """
        import json
        
        output_path = Path(output_path)
        if format == "json":
            data = {
                "metadata": metadata,
                "segments": segments
            }
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            # Formato de texto simple con timestamps
            with open(output_path, "w", encoding="utf-8") as f:
                for segment in segments:
                    f.write(f"[{segment['start']:.2f} - {segment['end']:.2f}] {segment['text']}\n")
        
        logger.info(f"Transcripción Replicate guardada en {output_path}")
        return str(output_path)
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Devuelve los idiomas soportados."""
        return self.supported_languages.copy()
    
    def estimate_cost(self, audio_duration_seconds: float) -> Dict[str, float]:
        """
        Estima el costo de transcripción basado en la duración del audio.
        
        Args:
            audio_duration_seconds: Duración del audio en segundos
            
        Returns:
            Dict con estimación de costo
        """
        # Replicate cobra por tiempo de cómputo, no por duración de audio
        # Estimación aproximada: $0.01-0.05 por minuto de audio
        cost_per_minute = 0.03  # Estimación conservadora
        duration_minutes = audio_duration_seconds / 60
        
        estimated_cost = duration_minutes * cost_per_minute
        
        return {
            "estimated_cost_usd": estimated_cost,
            "duration_minutes": duration_minutes,
            "cost_per_minute": cost_per_minute
        }

# Función unificada para elegir el servicio de transcripción
def get_transcription_service(service_type: str = "local", **kwargs) -> TranscriptionService:
    """
    Obtiene el servicio de transcripción apropiado.
    
    Args:
        service_type: Tipo de servicio ('local' para Whisper local, 'replicate' para Replicate)
        **kwargs: Argumentos adicionales para el servicio
        
    Returns:
        TranscriptionService o ReplicateTranscriptionService
    """
    if service_type.lower() == "replicate":
        return ReplicateTranscriptionService(**kwargs)
    else:
        return TranscriptionService(**kwargs) 