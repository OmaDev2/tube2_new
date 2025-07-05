# utils/overlays.py

from moviepy.editor import VideoFileClip, CompositeVideoClip
from moviepy.video.fx.all import loop
from typing import List, Tuple, Optional, Dict
import os
import logging

logger = logging.getLogger(__name__)

class OverlayManager:
    """
    Gestiona la carga, aplicación y limpieza de overlays de video de forma eficiente.
    Combina un cache inteligente con lógica de bucle para evitar errores.
    """
    def __init__(self):
        self.overlays_dir = "overlays"
        if not os.path.exists(self.overlays_dir):
            try:
                os.makedirs(self.overlays_dir)
                logger.info(f"Directorio de overlays creado en: {self.overlays_dir}")
            except OSError as e:
                logger.error(f"No se pudo crear el directorio de overlays: {e}")
        
        self._overlay_cache: Dict[str, VideoFileClip] = {}
        logger.info("OverlayManager inicializado.")

    def get_available_overlays(self) -> List[str]:
        """Obtiene la lista de overlays disponibles en el directorio."""
        try:
            return [f for f in os.listdir(self.overlays_dir) 
                   if f.endswith(('.mp4', '.mov', '.avi', '.webm'))]
        except FileNotFoundError:
            return []

    def _load_overlay(self, overlay_name: str) -> Optional[VideoFileClip]:
        """Carga un overlay desde el archivo o lo recupera del caché."""
        if overlay_name in self._overlay_cache:
            logger.debug(f"Overlay '{overlay_name}' encontrado en caché.")
            return self._overlay_cache[overlay_name]

        overlay_path = os.path.join(self.overlays_dir, overlay_name)
        if not os.path.exists(overlay_path):
            logger.error(f"El archivo de overlay '{overlay_name}' NO se encontró en: {overlay_path}")
            return None

        try:
            overlay_clip = VideoFileClip(overlay_path)
            self._overlay_cache[overlay_name] = overlay_clip
            logger.info(f"Overlay '{overlay_name}' cargado y cacheado.")
            return overlay_clip
        except Exception as e:
            logger.error(f"Error al cargar el overlay '{overlay_name}': {e}", exc_info=True)
            return None

    def apply_overlays(self, base_clip: VideoFileClip, 
                      overlays: List[Tuple[str, float, float, float]]) -> VideoFileClip:
        """
        Aplica una lista de overlays a un clip base, gestionando bucles y duraciones.
        
        Args:
            base_clip: Clip de video base.
            overlays: Lista de tuplas (overlay_name, opacity, start_time, duration).
        """
        if not overlays:
            return base_clip
        
        clips_to_compose = [base_clip]
        
        for overlay_name, opacity, start_time, target_duration in overlays:
            
            overlay_original = self._load_overlay(overlay_name)
            if not overlay_original:
                continue # Si no se pudo cargar, pasar al siguiente

            try:
                # --- LÓGICA DE BUCLE (LOOP) INTEGRADA ---
                overlay_processed = overlay_original
                native_duration = overlay_original.duration

                # Lógica de bucle y recorte para asegurar la duración correcta del overlay
                overlay_processed = overlay_original
                native_duration = overlay_original.duration

                if native_duration < target_duration:
                    # Si el overlay es más corto, lo bucleamos para que sea al menos tan largo como el objetivo
                    # Añadimos un poco extra para evitar problemas de redondeo
                    overlay_processed = overlay_original.fx(loop, duration=target_duration + 1.0)
                    logger.info(f"Overlay '{overlay_name}' bucleado. Duración original: {native_duration:.2f}s, bucleado a: {overlay_processed.duration:.2f}s")
                
                # Recortar el overlay a la duración exacta del clip base
                if overlay_processed.duration > target_duration:
                    overlay_processed = overlay_processed.subclip(0, target_duration)
                    logger.info(f"Overlay '{overlay_name}' recortado a la duración objetivo: {target_duration:.2f}s")
                elif overlay_processed.duration < target_duration:
                    # Esto debería ser un caso raro si el bucle funciona, pero como fallback
                    overlay_processed = overlay_processed.set_duration(target_duration)
                    logger.warning(f"Overlay '{overlay_name}' duración ajustada a {target_duration:.2f}s (era más corto y no se bucleó correctamente o no se pudo recortar).")

                # Aplicar resto de transformaciones
                final_overlay = (overlay_processed
                               .set_opacity(opacity)
                               .set_start(start_time)
                               .resize(height=base_clip.h)
                               .set_position("center"))
                
                clips_to_compose.append(final_overlay)

            except Exception as e:
                logger.error(f"Error procesando la composición del overlay '{overlay_name}': {e}", exc_info=True)
                continue
        
        if len(clips_to_compose) > 1:
            logger.info(f"Componiendo {len(clips_to_compose) - 1} overlay(s) sobre el clip base.")
            return CompositeVideoClip(clips_to_compose, use_bgclip=True)
        else:
            logger.warning("No se aplicó ningún overlay válido.")
            return base_clip

    def close(self):
        """Libera la memoria de todos los clips de overlay cacheados."""
        logger.info(f"Cerrando {len(self._overlay_cache)} overlays cacheados para liberar memoria.")
        for clip in self._overlay_cache.values():
            try:
                clip.close()
            except Exception as e:
                logger.warning(f"Error cerrando un clip de overlay cacheado: {e}")
        self._overlay_cache.clear()

# Para compatibilidad con código anterior si fuera necesario.
class VideoOverlay:
    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path