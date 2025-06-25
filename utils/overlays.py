from moviepy.editor import VideoFileClip, CompositeVideoClip
from moviepy.video.fx import all as vfx
from typing import List, Tuple, Optional
import os
from PIL import Image
import cv2
import numpy as np

class VideoOverlay:
    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path
        self.clip = None
    
    def load(self):
        if not self.clip:
            self.clip = VideoFileClip(self.path)
        return self.clip
    
    def apply(self, base_clip, opacity: float = 1.0, start_time: float = 0, duration: Optional[float] = None):
        overlay = self.load()
        if duration:
            overlay = overlay.subclip(0, duration)
        
        # Función para redimensionar usando cv2
        def resize_frame(frame):
            return cv2.resize(frame, (base_clip.w, base_clip.h), interpolation=cv2.INTER_LINEAR)
        
        # Aplicar redimensionamiento
        overlay = overlay.fl_image(resize_frame)
        
        # Aplicar opacidad
        if opacity < 1.0:
            overlay = overlay.set_opacity(opacity)
        
        # Posicionar en el tiempo
        overlay = overlay.set_start(start_time)
        
        return CompositeVideoClip([base_clip, overlay])

class OverlayManager:
    def __init__(self):
        self.overlays_dir = "overlays"
        if not os.path.exists(self.overlays_dir):
            os.makedirs(self.overlays_dir)
    
    def get_available_overlays(self) -> List[str]:
        """Obtiene la lista de overlays disponibles."""
        if not os.path.exists(self.overlays_dir):
            return []
        return [f for f in os.listdir(self.overlays_dir) 
                if f.endswith(('.mp4', '.mov', '.avi', '.webm'))]
    
    def has_alpha_channel(self, video_path: str) -> bool:
        """Detecta si un video tiene canal alpha."""
        try:
            # Intentar leer el video con OpenCV
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return False
                
            # Leer varios frames para asegurarnos
            for _ in range(5):  # Intentar con los primeros 5 frames
                ret, frame = cap.read()
                if not ret:
                    continue
                    
                # Verificar si el frame tiene 4 canales (RGBA)
                if len(frame.shape) == 3 and frame.shape[2] == 4:
                    cap.release()
                    return True
                    
            cap.release()
            return False
        except Exception as e:
            print(f"Error al detectar canal alpha: {e}")
            return False
    
    def optimize_overlay(self, overlay_clip: VideoFileClip, has_alpha: bool) -> VideoFileClip:
        """Simplificado: solo devuelve el overlay tal cual, sin canal alpha ni máscara."""
        return overlay_clip
    
    def apply_overlays(
        self,
        base_clip: VideoFileClip,
        overlays: List[Tuple[str, float, float, float]]
    ) -> VideoFileClip:
        print(f"[DEBUG] Entrando en apply_overlays con overlays: {overlays}")
        if not overlays:
            print("[DEBUG] No hay overlays para aplicar.")
            return base_clip
        
        overlay_clips = []
        
        for overlay_name, opacity, start_time, duration in overlays:
            overlay_path = os.path.join(self.overlays_dir, overlay_name)
            print(f"[DEBUG] Procesando overlay: {overlay_name} en {overlay_path}")
            if not os.path.exists(overlay_path):
                print(f"[DEBUG] Overlay no encontrado: {overlay_path}")
                continue
            
            try:
                # Cargar el overlay
                overlay_clip = VideoFileClip(overlay_path)
                print(f"[DEBUG] Overlay {overlay_name} cargado correctamente.")
                
                # Redimensionar overlay al tamaño del clip base
                def resize_frame(frame):
                    return cv2.resize(frame, (base_clip.w, base_clip.h), interpolation=cv2.INTER_LINEAR)
                overlay_clip = overlay_clip.fl_image(resize_frame)
                
                # Detectar si tiene canal alpha
                has_alpha = self.has_alpha_channel(overlay_path)
                print(f"[DEBUG] Overlay {overlay_name} - Tiene alpha: {has_alpha}")
                
                # Optimizar el overlay según su tipo
                overlay_clip = self.optimize_overlay(overlay_clip, has_alpha)
                
                # Ajustar la duración y el tiempo de inicio
                overlay_clip = overlay_clip.set_start(start_time).set_duration(duration)
                
                # Aplicar la opacidad
                if opacity < 1.0:
                    overlay_clip = overlay_clip.set_opacity(opacity)
                
                overlay_clips.append(overlay_clip)
                print(f"[DEBUG] Overlay {overlay_name} añadido a overlay_clips.")
                
            except Exception as e:
                print(f"[DEBUG] Error al procesar overlay {overlay_name}: {e}")
                continue
        
        if not overlay_clips:
            print("[DEBUG] Ningún overlay fue añadido. Devolviendo base_clip.")
            return base_clip
        
        # Combinar todos los overlays con el clip base
        final_clip = CompositeVideoClip([base_clip] + overlay_clips)
        print("[DEBUG] Overlays aplicados correctamente.")
        return final_clip 