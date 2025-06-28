from moviepy.editor import VideoClip, ImageClip, CompositeVideoClip
import numpy as np
from PIL import Image
import math

class EfectosVideo:
    @staticmethod
    def _ease_in_out(t):
        """
        Función de easing ease-in-out para movimientos suaves.
        Acelera gradualmente al inicio, mantiene velocidad, luego desacelera al final.
        """
        if t < 0.5:
            return 2 * t * t
        else:
            return -1 + (4 - 2 * t) * t
    
    @staticmethod
    def _ease_out(t):
        """
        Función de easing ease-out para movimientos suaves.
        Empieza rápido y desacelera gradualmente.
        """
        return 1 - (1 - t) * (1 - t)
    
    @staticmethod
    def _ease_in(t):
        """
        Función de easing ease-in para movimientos suaves.
        Acelera gradualmente desde el reposo.
        """
        return t * t
    
    @staticmethod
    def _ease_smooth(t):
        """
        Función de easing suave usando coseno para movimientos muy fluidos.
        """
        return 0.5 * (1 - math.cos(math.pi * t))
    @staticmethod
    def zoom_in(clip, duration=1.0, zoom_factor=1.5):
        """Aplica un efecto de zoom in continuo al clip"""
        def make_frame(t):
            # Calcula el zoom basado en el tiempo actual (CON EASING SUAVE)
            progress = EfectosVideo._ease_smooth(t / clip.duration)
            zoom = 1 + (zoom_factor - 1) * progress
            frame = clip.get_frame(t)
            h, w = frame.shape[:2]
            new_h = int(h / zoom)
            new_w = int(w / zoom)
            center_y = h // 2
            center_x = w // 2
            start_y = center_y - new_h // 2
            start_x = center_x - new_w // 2
            cropped = frame[start_y:start_y+new_h, start_x:start_x+new_w]
            return np.array(Image.fromarray(cropped).resize((w, h), Image.Resampling.LANCZOS))
        return VideoClip(make_frame, duration=clip.duration)

    @staticmethod
    def zoom_out(clip, duration=1.0, zoom_factor=1.5):
        """Aplica un efecto de zoom out continuo al clip"""
        def make_frame(t):
            # Calcula el zoom basado en el tiempo actual (CON EASING SUAVE)
            progress = EfectosVideo._ease_smooth(t / clip.duration)
            zoom = zoom_factor - (zoom_factor - 1) * progress
            frame = clip.get_frame(t)
            h, w = frame.shape[:2]
            new_h = int(h / zoom)
            new_w = int(w / zoom)
            center_y = h // 2
            center_x = w // 2
            start_y = center_y - new_h // 2
            start_x = center_x - new_w // 2
            cropped = frame[start_y:start_y+new_h, start_x:start_x+new_w]
            return np.array(Image.fromarray(cropped).resize((w, h), Image.Resampling.LANCZOS))
        return VideoClip(make_frame, duration=clip.duration)

    @staticmethod
    def pan_left(clip, duration=1.0, zoom_factor=1.2, distance=0.2):
        """
        Aplica un efecto de paneo a la izquierda (movimiento de la cámara a la izquierda).
        La imagen se mueve de izquierda a derecha en la pantalla durante TODA la duración de la imagen.
        
        Args:
            duration: Parámetro legacy (no se usa, el paneo recorre toda la duración del clip)
            zoom_factor: Factor de zoom para crear margen de paneo
            distance: Parámetro legacy (no se usa actualmente)
        """
        def make_frame(t):
            frame = clip.get_frame(t)
            h, w = frame.shape[:2]

            # Dimensiones de la ventana de recorte (más pequeña que el frame)
            new_h = int(h / zoom_factor)
            new_w = int(w / zoom_factor)

            # El progreso del paneo (RECORRE TODA LA DURACIÓN DE LA IMAGEN)
            progress = EfectosVideo._ease_smooth(t / clip.duration)
            
            # El paneo va desde el borde derecho al centro
            start_x_max = w - new_w
            start_x_min = int((w - new_w) / 2) # Centro
            
            # Interpolar la posición de inicio X
            start_x = int(start_x_max - (start_x_max - start_x_min) * progress)
            start_y = int((h - new_h) / 2) # Mantener centrado verticalmente

            # Recortar y redimensionar
            cropped = frame[start_y:start_y + new_h, start_x:start_x + new_w]
            return np.array(Image.fromarray(cropped).resize((w, h), Image.Resampling.LANCZOS))

        return VideoClip(make_frame, duration=clip.duration)

    @staticmethod
    def pan_right(clip, duration=1.0, zoom_factor=1.2, distance=0.2):
        """
        Aplica un efecto de paneo a la derecha (movimiento de la cámara a la derecha).
        La imagen se mueve de derecha a izquierda en la pantalla.
        """
        def make_frame(t):
            frame = clip.get_frame(t)
            h, w = frame.shape[:2]

            # Dimensiones de la ventana de recorte
            new_h = int(h / zoom_factor)
            new_w = int(w / zoom_factor)

            # Progreso del paneo (CON EASING SUAVE)
            progress = EfectosVideo._ease_smooth(t / clip.duration)

            # El paneo va desde el centro hacia el borde izquierdo
            start_x_min = 0
            start_x_max = int((w - new_w) / 2) # Centro

            # Interpolar la posición de inicio X
            start_x = int(start_x_max - (start_x_max - start_x_min) * progress)
            start_y = int((h - new_h) / 2) # Mantener centrado verticalmente

            # Recortar y redimensionar
            cropped = frame[start_y:start_y + new_h, start_x:start_x + new_w]
            return np.array(Image.fromarray(cropped).resize((w, h), Image.Resampling.LANCZOS))

        return VideoClip(make_frame, duration=clip.duration)

    @staticmethod
    def pan_up(clip, duration=1.0, zoom_factor=1.2):
        """
        Aplica un efecto de paneo hacia arriba (movimiento de la cámara hacia arriba).
        La imagen se mueve de arriba hacia abajo en la pantalla.
        """
        def make_frame(t):
            frame = clip.get_frame(t)
            h, w = frame.shape[:2]

            # Dimensiones de la ventana de recorte
            new_h = int(h / zoom_factor)
            new_w = int(w / zoom_factor)

            # Progreso del paneo (CON EASING SUAVE)
            progress = EfectosVideo._ease_smooth(t / clip.duration)

            # El paneo va desde el borde superior al centro
            start_y_min = 0
            start_y_max = int((h - new_h) / 2) # Centro

            # Interpolar la posición de inicio Y
            start_y = int(start_y_min + (start_y_max - start_y_min) * progress)
            start_x = int((w - new_w) / 2) # Mantener centrado horizontalmente

            # Recortar y redimensionar
            cropped = frame[start_y:start_y + new_h, start_x:start_x + new_w]
            return np.array(Image.fromarray(cropped).resize((w, h), Image.Resampling.LANCZOS))

        return VideoClip(make_frame, duration=clip.duration)

    @staticmethod
    def pan_down(clip, duration=1.0, zoom_factor=1.2):
        """
        Aplica un efecto de paneo hacia abajo (movimiento de la cámara hacia abajo).
        La imagen se mueve de abajo hacia arriba en la pantalla.
        """
        def make_frame(t):
            frame = clip.get_frame(t)
            h, w = frame.shape[:2]

            # Dimensiones de la ventana de recorte
            new_h = int(h / zoom_factor)
            new_w = int(w / zoom_factor)

            # Progreso del paneo (CON EASING SUAVE)
            progress = EfectosVideo._ease_smooth(t / clip.duration)

            # El paneo va desde el borde inferior al centro
            start_y_max = h - new_h
            start_y_min = int((h - new_h) / 2) # Centro

            # Interpolar la posición de inicio Y
            start_y = int(start_y_max - (start_y_max - start_y_min) * progress)
            start_x = int((w - new_w) / 2) # Mantener centrado horizontalmente

            # Recortar y redimensionar
            cropped = frame[start_y:start_y + new_h, start_x:start_x + new_w]
            return np.array(Image.fromarray(cropped).resize((w, h), Image.Resampling.LANCZOS))

        return VideoClip(make_frame, duration=clip.duration)

    @staticmethod
    def fade_in(clip, duration=1.0):
        """Aplica un efecto de fade in al clip"""
        def make_frame(t):
            alpha = min(1.0, t / duration)
            return clip.get_frame(t) * alpha
        return VideoClip(make_frame, duration=clip.duration)

    @staticmethod
    def fade_out(clip, duration=1.0):
        """Aplica un efecto de fade out al clip"""
        def make_frame(t):
            alpha = max(0.0, 1 - (t - (clip.duration - duration)) / duration)
            return clip.get_frame(t) * alpha
        return VideoClip(make_frame, duration=clip.duration)

    @staticmethod
    def mirror_x(clip):
        """Aplica un efecto de espejo horizontal"""
        def make_frame(t):
            return np.fliplr(clip.get_frame(t))
        return VideoClip(make_frame, duration=clip.duration)

    @staticmethod
    def mirror_y(clip):
        """Aplica un efecto de espejo vertical"""
        def make_frame(t):
            return np.flipud(clip.get_frame(t))
        return VideoClip(make_frame, duration=clip.duration)

    @staticmethod
    def rotate_180(clip):
        """Rota la imagen 180 grados."""
        def make_frame(t):
            # Rotar 180 grados es equivalente a np.rot90 dos veces
            return np.rot90(clip.get_frame(t), k=2)
        return VideoClip(make_frame, duration=clip.duration)

    @staticmethod
    def kenburns(clip, duration=None, zoom_start=1.0, zoom_end=1.2, pan_start=(0.5, 0.5), pan_end=(0.5, 0.5)):
        """
        Aplica un efecto Ken Burns (zoom y paneo simultáneos) al clip.

        Args:
            clip: Clip de video o imagen.
            duration: Duración del efecto. Si es None, usa la duración del clip.
            zoom_start: Factor de zoom inicial (ej: 1.0 para no zoom).
            zoom_end: Factor de zoom final (ej: 1.2 para 20% de zoom).
            pan_start: Tupla (x, y) del centro del cuadro al inicio (0.0 a 1.0).
                       (0.5, 0.5) es el centro de la imagen.
            pan_end: Tupla (x, y) del centro del cuadro al final (0.0 a 1.0).
        """
        if duration is None:
            duration = clip.duration

        def make_frame(t):
            frame = clip.get_frame(t)
            h, w = frame.shape[:2]

            # Interpolar SUAVEMENTE el zoom y el paneo (CON EASING)
            progress = EfectosVideo._ease_smooth(t / duration)
            current_zoom = zoom_start + (zoom_end - zoom_start) * progress
            current_pan_x = pan_start[0] + (pan_end[0] - pan_start[0]) * progress
            current_pan_y = pan_start[1] + (pan_end[1] - pan_start[1]) * progress

            # Calcular las dimensiones de la ventana de recorte
            new_w = int(w / current_zoom)
            new_h = int(h / current_zoom)

            # Calcular la posición de la ventana de recorte
            # El centro del recorte se mueve desde pan_start a pan_end
            center_x = current_pan_x * w
            center_y = current_pan_y * h

            start_x = int(center_x - new_w / 2)
            start_y = int(center_y - new_h / 2)

            # Asegurarse de que la ventana de recorte no se salga de los límites de la imagen
            start_x = max(0, min(start_x, w - new_w))
            start_y = max(0, min(start_y, h - new_h))

            # Recortar y redimensionar a las dimensiones originales del clip
            cropped = frame[start_y:start_y + new_h, start_x:start_x + new_w]
            return np.array(Image.fromarray(cropped).resize((w, h), Image.Resampling.LANCZOS))

        return VideoClip(make_frame, duration=duration)

    @staticmethod
    def shake(clip, duration=None, intensity=5, zoom_factor=1.1):
        """
        Aplica un efecto de sacudida (shake) al clip.

        Args:
            clip: Clip de video o imagen.
            duration: Duración del efecto. Si es None, usa la duración del clip.
            intensity: Máximo desplazamiento en píxeles para la sacudida.
            zoom_factor: Zoom para evitar bordes negros.
        """
        if duration is None:
            duration = clip.duration

        def make_frame(t):
            frame = clip.get_frame(t)
            h, w = frame.shape[:2]

            # Aplicar un zoom constante para tener margen
            new_w = int(w / zoom_factor)
            new_h = int(h / zoom_factor)

            # Generar un desplazamiento aleatorio para cada fotograma
            delta_x = np.random.uniform(-intensity, intensity)
            delta_y = np.random.uniform(-intensity, intensity)

            # Calcular la posición de inicio del recorte, centrada y con el temblor
            start_x = int((w - new_w) / 2 + delta_x)
            start_y = int((h - new_h) / 2 + delta_y)

            # Asegurarse de que la ventana de recorte no se salga de los límites
            start_x = max(0, min(start_x, w - new_w))
            start_y = max(0, min(start_y, h - new_h))

            # Recortar y redimensionar
            cropped = frame[start_y:start_y + new_h, start_x:start_x + new_w]
            return np.array(Image.fromarray(cropped).resize((w, h), Image.Resampling.LANCZOS))

        return VideoClip(make_frame, duration=duration)

    @staticmethod
    def shake_zoom_combo(clip, shake_duration=2.0, intensity=8, zoom_factor_shake=1.2, zoom_in_factor=1.4, zoom_out_factor=1.6):
        """
        Efecto combinado: Shake inicial por 1-2 segundos, luego zoom in y zoom out.
        
        Args:
            clip: Clip de video o imagen
            shake_duration: Duración del shake inicial en segundos (1.0-2.0 recomendado)
            intensity: Intensidad del shake
            zoom_factor_shake: Zoom del shake para evitar bordes negros
            zoom_in_factor: Factor de zoom in después del shake
            zoom_out_factor: Factor de zoom out al final
        """
        total_duration = clip.duration
        
        # Distribución de tiempo:
        # - shake_duration segundos: shake
        # - resto del tiempo dividido entre zoom_in y zoom_out
        remaining_time = total_duration - shake_duration
        zoom_in_duration = remaining_time * 0.6  # 60% para zoom in
        zoom_out_duration = remaining_time * 0.4  # 40% para zoom out
        
        def make_frame(t):
            frame = clip.get_frame(t)
            h, w = frame.shape[:2]
            
            if t <= shake_duration:
                # FASE 1: SHAKE (primeros 1-2 segundos)
                # Aplicar zoom constante para tener margen
                new_w = int(w / zoom_factor_shake)
                new_h = int(h / zoom_factor_shake)
                
                # Generar desplazamiento aleatorio
                delta_x = np.random.uniform(-intensity, intensity)
                delta_y = np.random.uniform(-intensity, intensity)
                
                # Posición con temblor
                start_x = int((w - new_w) / 2 + delta_x)
                start_y = int((h - new_h) / 2 + delta_y)
                
                # Asegurar límites
                start_x = max(0, min(start_x, w - new_w))
                start_y = max(0, min(start_y, h - new_h))
                
                cropped = frame[start_y:start_y + new_h, start_x:start_x + new_w]
                
            elif t <= shake_duration + zoom_in_duration:
                # FASE 2: ZOOM IN (después del shake)
                time_in_zoom_in = t - shake_duration
                progress = time_in_zoom_in / zoom_in_duration
                
                # Zoom progresivo de 1.0 a zoom_in_factor
                current_zoom = 1.0 + (zoom_in_factor - 1.0) * progress
                
                new_h = int(h / current_zoom)
                new_w = int(w / current_zoom)
                center_y = h // 2
                center_x = w // 2
                start_y = center_y - new_h // 2
                start_x = center_x - new_w // 2
                
                cropped = frame[start_y:start_y + new_h, start_x:start_x + new_w]
                
            else:
                # FASE 3: ZOOM OUT (final)
                time_in_zoom_out = t - shake_duration - zoom_in_duration
                progress = time_in_zoom_out / zoom_out_duration
                
                # Zoom progresivo de zoom_out_factor a zoom_in_factor (zoom out)
                current_zoom = zoom_out_factor - (zoom_out_factor - zoom_in_factor) * progress
                
                new_h = int(h / current_zoom)
                new_w = int(w / current_zoom)
                center_y = h // 2
                center_x = w // 2
                start_y = center_y - new_h // 2
                start_x = center_x - new_w // 2
                
                cropped = frame[start_y:start_y + new_h, start_x:start_x + new_w]
            
            return np.array(Image.fromarray(cropped).resize((w, h), Image.Resampling.LANCZOS))

        return VideoClip(make_frame, duration=total_duration)

    @staticmethod
    def shake_kenburns_combo(clip, shake_duration=1.5, intensity=10, zoom_factor_shake=1.15, 
                           kenburns_zoom_start=1.0, kenburns_zoom_end=1.4, 
                           kenburns_pan_start=(0.2, 0.2), kenburns_pan_end=(0.7, 0.6)):
        """
        Efecto combinado: Shake inicial breve, luego efecto Ken Burns suave.
        
        Args:
            clip: Clip de video o imagen
            shake_duration: Duración del shake inicial (1.0-2.0 segundos recomendado)
            intensity: Intensidad del shake
            zoom_factor_shake: Zoom del shake para evitar bordes
            kenburns_zoom_start: Zoom inicial del Ken Burns
            kenburns_zoom_end: Zoom final del Ken Burns
            kenburns_pan_start: Posición inicial del paneo (x, y)
            kenburns_pan_end: Posición final del paneo (x, y)
        """
        total_duration = clip.duration
        kenburns_duration = total_duration - shake_duration
        
        def make_frame(t):
            frame = clip.get_frame(t)
            h, w = frame.shape[:2]
            
            if t <= shake_duration:
                # FASE 1: SHAKE INICIAL
                new_w = int(w / zoom_factor_shake)
                new_h = int(h / zoom_factor_shake)
                
                delta_x = np.random.uniform(-intensity, intensity)
                delta_y = np.random.uniform(-intensity, intensity)
                
                start_x = int((w - new_w) / 2 + delta_x)
                start_y = int((h - new_h) / 2 + delta_y)
                
                start_x = max(0, min(start_x, w - new_w))
                start_y = max(0, min(start_y, h - new_h))
                
                cropped = frame[start_y:start_y + new_h, start_x:start_x + new_w]
                
            else:
                # FASE 2: KEN BURNS
                time_in_kenburns = t - shake_duration
                progress = time_in_kenburns / kenburns_duration
                
                # Interpolar zoom y paneo
                current_zoom = kenburns_zoom_start + (kenburns_zoom_end - kenburns_zoom_start) * progress
                current_pan_x = kenburns_pan_start[0] + (kenburns_pan_end[0] - kenburns_pan_start[0]) * progress
                current_pan_y = kenburns_pan_start[1] + (kenburns_pan_end[1] - kenburns_pan_start[1]) * progress
                
                # Calcular dimensiones y posición
                new_w = int(w / current_zoom)
                new_h = int(h / current_zoom)
                
                center_x = current_pan_x * w
                center_y = current_pan_y * h
                
                start_x = int(center_x - new_w / 2)
                start_y = int(center_y - new_h / 2)
                
                start_x = max(0, min(start_x, w - new_w))
                start_y = max(0, min(start_y, h - new_h))
                
                cropped = frame[start_y:start_y + new_h, start_x:start_x + new_w]
            
            return np.array(Image.fromarray(cropped).resize((w, h), Image.Resampling.LANCZOS))

        return VideoClip(make_frame, duration=total_duration)

    @staticmethod
    def apply_effect(clip, effect_name, **kwargs):
        """Aplica un efecto específico al clip"""
        effect_methods = {
            "zoom_in": EfectosVideo.zoom_in,
            "zoom_out": EfectosVideo.zoom_out,
            "pan_left": EfectosVideo.pan_left,
            "pan_right": EfectosVideo.pan_right,
            "pan_up": EfectosVideo.pan_up,
            "pan_down": EfectosVideo.pan_down,
            "shake": EfectosVideo.shake,
            "shake_zoom_combo": EfectosVideo.shake_zoom_combo,
            "shake_kenburns_combo": EfectosVideo.shake_kenburns_combo,
            "fade_in": EfectosVideo.fade_in,
            "fade_out": EfectosVideo.fade_out,
            "mirror_x": EfectosVideo.mirror_x,
            "mirror_y": EfectosVideo.mirror_y,
            "rotate_180": EfectosVideo.rotate_180,
            "kenburns": EfectosVideo.kenburns
        }
        
        if effect_name in effect_methods:
            return effect_methods[effect_name](clip, **kwargs)
        return clip

    @staticmethod
    def apply_effects_sequence(clip, effects_list):
        """
        Aplica una secuencia de efectos al clip
        Args:
            clip: Clip de video o imagen
            effects_list: Lista de tuplas (efecto, parámetros)
        """
        result = clip
        for effect, params in effects_list:
            if hasattr(EfectosVideo, effect):
                effect_func = getattr(EfectosVideo, effect)
                result = effect_func(result, **params)
        return result 