from faster_whisper import WhisperModel
import time
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import logging

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