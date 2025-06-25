from moviepy.editor import VideoClip, ImageClip, CompositeVideoClip
import numpy as np
from PIL import Image

class EfectosVideo:
    @staticmethod
    def zoom_in(clip, duration=1.0, zoom_factor=1.5):
        """Aplica un efecto de zoom in continuo al clip"""
        def make_frame(t):
            # Calcula el zoom basado en el tiempo actual
            progress = t / clip.duration
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
            # Calcula el zoom basado en el tiempo actual
            progress = t / clip.duration
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
    def pan_left(clip, duration=1.0, distance=0.5):
        """Aplica un efecto de paneo continuo a la izquierda"""
        def make_frame(t):
            # Calcula el desplazamiento basado en el tiempo actual
            progress = t / clip.duration
            x = -distance * progress
            frame = clip.get_frame(t)
            h, w = frame.shape[:2]
            offset = int(x * w)
            
            # Crear un nuevo frame con la imagen original
            new_frame = frame.copy()
            
            # Si el offset es negativo (movimiento a la izquierda)
            if offset < 0:
                # Asegurarse de que las dimensiones coincidan
                visible_width = w + offset
                if visible_width > 0:
                    new_frame[:, :visible_width] = frame[:, -offset:-offset+visible_width]
                    new_frame[:, visible_width:] = frame[:, :w-visible_width]
            else:
                # Asegurarse de que las dimensiones coincidan
                visible_width = w - offset
                if visible_width > 0:
                    new_frame[:, offset:] = frame[:, :visible_width]
                    new_frame[:, :offset] = frame[:, visible_width:visible_width+offset]
            
            return new_frame
        return VideoClip(make_frame, duration=clip.duration)

    @staticmethod
    def pan_right(clip, duration=1.0, distance=0.5):
        """Aplica un efecto de paneo continuo a la derecha"""
        def make_frame(t):
            # Calcula el desplazamiento basado en el tiempo actual
            progress = t / clip.duration
            x = distance * progress
            frame = clip.get_frame(t)
            h, w = frame.shape[:2]
            offset = int(x * w)
            
            # Crear un nuevo frame con la imagen original
            new_frame = frame.copy()
            
            # Si el offset es negativo (movimiento a la derecha)
            if offset < 0:
                # Asegurarse de que las dimensiones coincidan
                visible_width = w + offset
                if visible_width > 0:
                    new_frame[:, -offset:] = frame[:, :visible_width]
                    new_frame[:, :-offset] = frame[:, visible_width:visible_width+w+offset]
            else:
                # Asegurarse de que las dimensiones coincidan
                visible_width = w - offset
                if visible_width > 0:
                    new_frame[:, :visible_width] = frame[:, offset:offset+visible_width]
                    new_frame[:, visible_width:] = frame[:, :w-visible_width]
            
            return new_frame
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
    def kenburns(clip, duration=1.0, zoom_start=1.0, zoom_end=1.5, pan_start=(0, 0), pan_end=(0.2, 0.2)):
        """
        Aplica un efecto Ken Burns al clip.
        Args:
            clip: Clip de video o imagen
            duration: Duración del efecto
            zoom_start: Factor de zoom inicial (1.0 = tamaño normal)
            zoom_end: Factor de zoom final
            pan_start: Posición inicial del paneo (x, y) en porcentaje
            pan_end: Posición final del paneo (x, y) en porcentaje
        """
        def make_frame(t):
            # Calcular el progreso del efecto
            progress = t / duration
            
            # Calcular el zoom actual
            zoom = zoom_start + (zoom_end - zoom_start) * progress
            
            # Calcular la posición del paneo actual
            pan_x = pan_start[0] + (pan_end[0] - pan_start[0]) * progress
            pan_y = pan_start[1] + (pan_end[1] - pan_start[1]) * progress
            
            # Obtener el frame original
            frame = clip.get_frame(t)
            h, w = frame.shape[:2]
            
            # Calcular las nuevas dimensiones basadas en el zoom
            new_h = int(h / zoom)
            new_w = int(w / zoom)
            
            # Calcular el centro de la imagen
            center_y = h // 2
            center_x = w // 2
            
            # Calcular el desplazamiento basado en el paneo
            offset_x = int(pan_x * w)
            offset_y = int(pan_y * h)
            
            # Calcular la posición de inicio del recorte
            start_y = center_y - new_h // 2 + offset_y
            start_x = center_x - new_w // 2 + offset_x
            
            # Asegurar que no nos salgamos de los límites de la imagen
            start_y = max(0, min(start_y, h - new_h))
            start_x = max(0, min(start_x, w - new_w))
            
            # Recortar y redimensionar
            cropped = frame[start_y:start_y+new_h, start_x:start_x+new_w]
            return np.array(Image.fromarray(cropped).resize((w, h), Image.Resampling.LANCZOS))
        
        return VideoClip(make_frame, duration=clip.duration)

    @staticmethod
    def apply_effect(clip, effect_name, **kwargs):
        """Aplica un efecto específico al clip"""
        effect_methods = {
            "zoom_in": EfectosVideo.zoom_in,
            "zoom_out": EfectosVideo.zoom_out,
            "pan_left": EfectosVideo.pan_left,
            "pan_right": EfectosVideo.pan_right,
            "fade_in": EfectosVideo.fade_in,
            "fade_out": EfectosVideo.fade_out,
            "mirror_x": EfectosVideo.mirror_x,
            "mirror_y": EfectosVideo.mirror_y,
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