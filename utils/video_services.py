# utils/video_services.py
from moviepy.editor import (
    VideoFileClip, AudioFileClip, TextClip, ImageClip,
    concatenate_videoclips, CompositeVideoClip, CompositeAudioClip,
    concatenate_audioclips
)
# Importar fx si realmente los usas en esta clase (vfx no se usa en el código actual)
# from moviepy.video.fx import all as vfx
# from moviepy.audio.fx import all as afx

# Importar clases de utils (si existen y se usan)
try: from utils.efectos import EfectosVideo
except ImportError: EfectosVideo = None # Manejar si no existe
try: from utils.transitions import TransitionEffect
except ImportError: TransitionEffect = None
try: from utils.overlays import OverlayManager
except ImportError: OverlayManager = None

import os
import shutil # Para copiar archivo en add_hardcoded_subtitles
import logging
import math # Para ceil en cálculo de loops de música
import uuid # Para nombres de archivo temporal
from typing import List, Union, Optional, Callable, Sequence
# from tqdm import tqdm # No usado directamente
from pathlib import Path # Importar Path

logger = logging.getLogger(__name__)

# Importar get_available_fonts (si está en otro archivo)
# try:
#     from utils.subtitle_utils import get_available_fonts
# except ImportError:
#     def get_available_fonts(): return ["DejaVuSans", "Arial"]

class VideoServices:
    def __init__(self):
        # Usar directorio temporal del sistema podría ser más robusto que 'output'
        # import tempfile
        # self.output_dir = tempfile.mkdtemp(prefix="videoservices_out_")
        # logger.info(f"Directorio de salida temporal para videos: {self.output_dir}")
        # O seguir usando 'output' pero asegurando permisos
        self.output_dir = "output"
        if not os.path.exists(self.output_dir):
            try:
                os.makedirs(self.output_dir)
            except OSError as e:
                logger.error(f"No se pudo crear dir de salida '{self.output_dir}': {e}")
                self.output_dir = "." # Fallback al directorio actual

    def _get_unique_output_path(self, prefix="video", ext=".mp4") -> str:
        """Genera una ruta única en el directorio de salida."""
        filename = f"{prefix}_{uuid.uuid4().hex}{ext}"
        return os.path.join(self.output_dir, filename)

    def create_video_from_images(
        self,
        images: List[str],
        # duration_per_image: float, # <-- Eliminado
        scene_durations: Sequence[Union[float, int]], # <-- NUEVO PARÁMETRO
        output_path: Optional[str] = None,
        fps: int = 24,
        codec: str = 'libx264',
        # audio_codec: str = 'aac', # Audio se maneja después en video_processing
        transition_duration: float = 1.0,
        transition_type: str = 'dissolve',
        # --- Parámetros de audio/efectos eliminados, se manejan después ---
        # background_music: Optional[AudioFileClip] = None,
        # voice_over: Optional[AudioFileClip] = None,
        effects_per_clip: Optional[List[Optional[List[tuple]]]] = None, # NUEVO: efectos por clip individual
        overlays_per_clip: Optional[List[Optional[List[tuple]]]] = None, # NUEVO: overlays por clip individual
        fade_in_duration: float = 1.0, # Se pueden mantener aquí o aplicar después
        fade_out_duration: float = 1.0,
        # music_volume: float = 0.5,
        # music_loop: bool = True,
        progress_callback: Optional[Callable[[float, str], None]] = None
    ) -> str:
        """
        Crea un video desde imágenes usando duraciones específicas para cada escena/imagen.
        YA NO APLICA AUDIO NI EFECTOS/OVERLAYS DIRECTAMENTE AQUÍ.
        """
        clips = []
        final_clip = None
        # final_audio = None # Ya no se maneja aquí

        if not images: raise ValueError("Lista de imágenes vacía.")

        # Validación estricta de duraciones
        if any(d <= 0 for d in scene_durations):
            invalid_durations = [(i, d) for i, d in enumerate(scene_durations) if d <= 0]
            logger.error(f"Duraciones inválidas detectadas: {invalid_durations}")
            raise ValueError(f"Se encontraron {len(invalid_durations)} duraciones <= 0: {invalid_durations}")

        if len(images) != len(scene_durations):
            # Permitir continuar si no hay duraciones pero sí imágenes (se usará un default en el llamador)
            # O si hay más duraciones que imágenes (se usarán las primeras N duraciones)
            # Esta lógica ahora está más en video_processing.py, aquí se asume que coinciden o es un error.
            logger.error(f"Discrepancia crítica: {len(images)} imágenes pero {len(scene_durations)} duraciones. Esto no debería ocurrir si video_processing.py las alineó.")
            raise ValueError(f"Discrepancia imágenes/duraciones: {len(images)} vs {len(scene_durations)}.")
        
        if not scene_durations and images: # Si las duraciones están vacías pero hay imágenes
            logger.warning(f"scene_durations está vacía pero hay {len(images)} imágenes. Esto puede indicar un problema previo.")
            # Se podría lanzar error o intentar un fallback, pero idealmente video_processing.py lo maneja.
            raise ValueError("scene_durations está vacía pero se proporcionaron imágenes.")
            
        if scene_durations and not all(isinstance(d, (float, int)) and d > 0 for d in scene_durations):
             logger.error(f"Se encontraron duraciones de escena inválidas (<=0 o tipo incorrecto): {scene_durations}")
             raise ValueError(f"Duraciones de escena inválidas: {scene_durations}")

        logger.info(f"Creando video con {len(images)} imágenes. Duraciones: {[f'{d:.2f}s' for d in scene_durations]}. Transición: {transition_type} ({transition_duration:.2f}s)")

        # Calcular duración total estimada basada en duraciones de escena y transiciones
        video_duration = 0.0
        if transition_type.lower() != 'none' and transition_duration > 0 and len(images) > 1:
            video_duration = sum(scene_durations) - ((len(images) - 1) * transition_duration)
        elif len(images) > 0 : 
            video_duration = sum(scene_durations)
        
        if video_duration <= 0 and len(images) > 0: # Si la duración calculada es 0 o negativa, es un problema
            logger.warning(f"Duración calculada del video base es {video_duration:.2f}s. Esto puede ser debido a transiciones largas y duraciones cortas. Se usará la suma simple de duraciones de escena como fallback.")
            video_duration = sum(scene_durations)
            if video_duration <=0:
                logger.error("La suma de las duraciones de escena también es <=0. No se puede crear video.")
                raise ValueError("Duraciones de escena resultan en video de duración no positiva.")

        logger.info(f"Duración final estimada del video base (sin audio): {video_duration:.2f} segundos")

        # Definición de _update_progress (asumiendo que existe o es local a este método)
        def _update_progress(step: int, step_progress: float, message: str):
            if progress_callback:
                total_progress = 0.0; total_steps = 3 # Solo preparación, transiciones, renderizado
                if step == 1: total_progress = step_progress * 0.70      # Preparando clips (más pesado)
                elif step == 2: total_progress = 0.70 + (step_progress * 0.10) # Transiciones
                elif step == 3: total_progress = 0.80 + (step_progress * 0.20) # Renderizado base
                progress_callback(max(0.0, min(1.0, total_progress)), message)

        try:
            # --- 1. Procesar Imágenes con sus duraciones ---
            _update_progress(1, 0, "Preparando clips de imagen...")
            for i, image_path in enumerate(images):
                 if i >= len(scene_durations): # Salvaguarda por si hay más imágenes que duraciones
                     logger.warning(f"Más imágenes que duraciones. Omitiendo imagen extra: {image_path}")
                     break
                 _update_progress(1, (i+1)/len(images), f"Procesando imagen {i+1}/{len(images)}: {Path(image_path).name}")
                 try:
                     clip_duration = scene_durations[i] 
                     if not isinstance(clip_duration, (float, int)) or clip_duration <= 0:
                         logger.error(f"Duración inválida ({clip_duration}) para imagen {image_path}. Saltando.")
                         continue # Saltar esta imagen si su duración es mala
                     
                     # Crear ImageClip y asignarle su duración específica
                     clip = ImageClip(str(image_path)).set_duration(clip_duration)
                     
                     # Aplicar efectos específicos a este clip si están definidos
                     if effects_per_clip and i < len(effects_per_clip) and effects_per_clip[i]:
                         clip_effects = effects_per_clip[i]
                         logger.info(f"Aplicando {len(clip_effects)} efectos al clip {i+1}: {[effect[0] for effect in clip_effects]}")
                         try:
                             from utils.efectos import EfectosVideo
                             clip = EfectosVideo.apply_effects_sequence(clip, clip_effects)
                             logger.info(f"Efectos aplicados exitosamente al clip {i+1}")
                         except Exception as effect_e:
                             logger.error(f"Error aplicando efectos al clip {i+1}: {effect_e}")
                             # Continuar con el clip sin efectos
                     
                     # Aplicar overlays específicos a este clip si están definidos
                     if overlays_per_clip and i < len(overlays_per_clip) and overlays_per_clip[i]:
                         clip_overlays = overlays_per_clip[i]
                         logger.info(f"Aplicando {len(clip_overlays)} overlays al clip {i+1}: {[overlay[0] for overlay in clip_overlays]}")
                         try:
                             from utils.overlays import OverlayManager
                             overlay_manager = OverlayManager()
                             # Convertir overlays a formato esperado por apply_overlays: (nombre, opacidad, start_time, duration)
                             formatted_overlays = []
                             for overlay_name, opacity, start_time, duration in clip_overlays:
                                 # Para aplicar overlay a todo el clip, usar start_time=0 y duration=clip.duration
                                 formatted_overlays.append((overlay_name, opacity, 0, clip_duration))
                             clip = overlay_manager.apply_overlays(clip, formatted_overlays)
                             logger.info(f"Overlays aplicados exitosamente al clip {i+1}")
                         except Exception as overlay_e:
                             logger.error(f"Error aplicando overlays al clip {i+1}: {overlay_e}")
                             # Continuar con el clip sin overlays
                     
                     clips.append(clip)
                 except Exception as img_e: 
                     logger.error(f"Error procesando imagen {image_path} (dur: {scene_durations[i] if i < len(scene_durations) else 'N/A'}s): {img_e}", exc_info=True)
                     # No añadir clip si falla

            if not clips: 
                logger.error("No se crearon clips de imagen válidos. No se puede continuar.")
                raise ValueError("No se pudieron crear clips de imagen válidos a partir de las rutas proporcionadas.")
            _update_progress(1, 1.0, "Clips de imagen preparados.")

            # --- 2. Transiciones ---
            _update_progress(2, 0, "Aplicando transiciones entre clips...")
            if len(clips) > 1 and transition_type.lower() != 'none' and transition_duration > 0:
                try:
                    # Usar la clase TransitionEffect si está disponible
                    if TransitionEffect and transition_type.lower() == 'dissolve':
                        logger.info(f"Aplicando transición '{transition_type}' usando TransitionEffect...")
                        final_clip = TransitionEffect.apply_transition(clips, transition_type, transition_duration)
                        logger.info(f"Transición '{transition_type}' aplicada exitosamente.")
                    elif transition_type.lower() == 'fade':
                        # Mantener la implementación manual de fade para compatibilidad
                        transition_clips = []
                        for i, clip in enumerate(clips):
                            if i == 0:
                                # Primer clip: solo fade out al final
                                transition_clips.append(clip.fadeout(transition_duration))
                            elif i == len(clips) - 1:
                                # Último clip: solo fade in al principio
                                transition_clips.append(clip.fadein(transition_duration))
                            else:
                                # Clips intermedios: fade in y fade out
                                transition_clips.append(clip.fadein(transition_duration).fadeout(transition_duration))
                        
                        # Concatenar con superposición para crear el efecto fade
                        final_clip = transition_clips[0]
                        current_duration = transition_clips[0].duration
                        
                        for i in range(1, len(transition_clips)):
                            # El siguiente clip empieza cuando el anterior está terminando su fade out
                            start_time = current_duration - transition_duration
                            next_clip = transition_clips[i].set_start(start_time)
                            
                            # Crear composición temporal
                            final_clip = CompositeVideoClip([final_clip, next_clip])
                            
                            # Actualizar duración acumulada (menos la superposición)
                            current_duration = current_duration + transition_clips[i].duration - transition_duration
                        
                        logger.info(f"Transición '{transition_type}' aplicada manualmente.")
                    else:
                        # Para otros tipos de transición, usar concatenación simple
                        final_clip = concatenate_videoclips(clips, method="compose")
                        logger.info(f"Transición '{transition_type}' no implementada, usando concatenación.")
                except Exception as trans_e: 
                    logger.error(f"Aplicación de transición '{transition_type}' falló: {trans_e}. Concatenando clips directamente.", exc_info=True)
                    final_clip = concatenate_videoclips(clips, method="compose")
            elif len(clips) > 1:
                final_clip = concatenate_videoclips(clips, method="compose")
                logger.info("Clips concatenados directamente (sin transición especial).")
            else: # Solo un clip
                final_clip = clips[0]
                logger.info("Solo un clip, no se aplican transiciones.")
            
            # Asegurar que la duración del clip final coincida con la calculada video_duration
            # Esto es importante porque las transiciones pueden afectar la duración percibida.
            if final_clip.duration is None or abs(final_clip.duration - video_duration) > 0.01:
                logger.warning(f"Ajustando duración del clip compuesto de {final_clip.duration if final_clip.duration else 'None'}s a {video_duration:.2f}s.")
                final_clip = final_clip.set_duration(video_duration)

            # --- Fades (se aplican al video base sin audio) ---
            if fade_in_duration > 0 and final_clip.duration is not None and fade_in_duration < final_clip.duration:
                final_clip = final_clip.fadein(fade_in_duration)
                logger.info(f"Fade in ({fade_in_duration}s) aplicado.")
            if fade_out_duration > 0 and final_clip.duration is not None and fade_out_duration < final_clip.duration:
                final_clip = final_clip.fadeout(fade_out_duration)
                logger.info(f"Fade out ({fade_out_duration}s) aplicado.")
            _update_progress(2, 1.0, "Transiciones y fades aplicados.")

            # --- 3. Audio (Eliminado de esta función) ---
            # Ya no se llama a _update_progress para el paso 3 (audio)

            # --- 4. Renderizar (SIN AUDIO) ---
            _update_progress(3, 0, "Renderizando video base (sin audio)...") # Ahora es el paso 3
            output_path_to_use = os.path.abspath(output_path if output_path else self._get_unique_output_path(prefix="video_base"))
            Path(output_path_to_use).parent.mkdir(parents=True, exist_ok=True) # Asegurar que el directorio existe
            
            logger.info(f"Escribiendo video base (sin audio) en: {output_path_to_use}. Duración: {final_clip.duration:.2f}s, FPS: {fps}")
            # Renderizar sin especificar audio_codec o temp_audiofile, y explícitamente sin audio.
            final_clip.write_videofile(
                output_path_to_use, 
                fps=fps, 
                codec=codec, 
                audio=False, # Indicar explícitamente que NO hay audio en este archivo base
                logger='bar', 
                threads=os.cpu_count() or 2,
                preset='medium' # Añadir un preset razonable
            )
            _update_progress(3, 1.0, "¡Video base (sin audio) finalizado!") # Ahora es el paso 3
            logger.info(f"Video base (sin audio) guardado: {output_path_to_use}")
            return output_path_to_use

        except Exception as e:
             logger.error(f"Error fatal en create_video_from_images: {e}", exc_info=True)
             # No re-lanzar aquí directamente, permitir que el finally se ejecute.
             # El error será relanzado por el llamador (process_single_video) si es necesario.
             raise # Relanzar para que process_single_video lo capture
        finally:
             # Liberar memoria de los clips de MoviePy
             if final_clip: 
                  try: final_clip.close() 
                  except Exception as e_cls: logger.debug(f"Excepción al cerrar final_clip: {e_cls}")
             for clip_obj in clips: # clips es la lista de ImageClip individuales
                  try: clip_obj.close()
                  except Exception as e_cls: logger.debug(f"Excepción al cerrar clip individual: {e_cls}")

    def add_hardcoded_subtitles(
        self,
        video_clip: VideoFileClip,
        segments: list,
        font: str = "Arial",
        font_size: int = 40,
        color: str = "white",
        stroke_color: str = "black",
        stroke_width: int = 2,
        position: str = "bottom",
        fade_out_duration: float = 0.0
    ) -> Optional[CompositeVideoClip]:
        """Incrusta subtítulos en el video usando MoviePy."""
        video = None
        final = None
        processed_segments = 0
        try:
            logger.info(f"Iniciando add_hardcoded_subtitles para clip en memoria (Dur: {video_clip.duration:.2f}s)")
            
            # Preservar el audio original y asegurarnos de que está cargado
            original_audio = None
            if video_clip.audio is not None:
                try:
                    # Crear una copia del audio para evitar problemas de referencia
                    original_audio = video_clip.audio.copy()
                    logger.info(f"Audio original preservado (duración: {original_audio.duration:.2f}s)")
                except Exception as audio_e:
                    logger.error(f"Error al copiar audio: {audio_e}")
            
            # Usar el clip directamente
            video = video_clip 
            video_width, video_height = video.size
            logger.info(f"Procesando clip ({video_width}x{video_height}). Fuente: '{font}', Tamaño: {font_size}, Pos: {position}. Segmentos: {len(segments)}")
            
            # CORRECCIÓN: Usar el tamaño de fuente proporcionado por el usuario
            # Pero asegurar un tamaño mínimo razonable
            final_font_size = max(font_size, 20)  # Mínimo 20px
            
            # Usar el valor de stroke_width del parámetro, pero con un mínimo
            # Convertir a int por seguridad
            try:
                stroke_width_value = int(stroke_width)
            except (ValueError, TypeError):
                stroke_width_value = 2  # Valor por defecto si no es válido
                
            # Ajustar el grosor del borde según el tamaño y garantizar mínimo 2px
            final_stroke_width = max(stroke_width_value, 2)
            
            # CORRECCIÓN: Usar el color pasado como parámetro
            subtitle_color = color  # Usar el color que el usuario especificó
            subtitle_stroke_color = stroke_color  # Usar el color de borde especificado
            
            logger.info(f"Subtítulos configurados: font_size={final_font_size}px (solicitado: {font_size}px), stroke={final_stroke_width}px, color={subtitle_color}, stroke={subtitle_stroke_color}")

            # Calcular mejores márgenes basados en la resolución del video
            # Esto asegura que los subtítulos no queden muy pegados a los bordes
            top_margin = max(int(video_height * 0.05), 20)       # 5% desde arriba o mínimo 20px
            bottom_margin = max(int(video_height * 0.08), 30)    # 8% desde abajo o mínimo 30px
            center_offset = 0  # Sin offset adicional para center

            subtitle_clips = []
            for i, seg in enumerate(segments):
                txt = seg.get('text', '').strip()
                start = seg.get('start')
                end = seg.get('end')

                if not txt or start is None or end is None or end <= start:
                    continue

                duration = end - start

                try:
                    # Crear TextClip simple pero efectivo
                    txt_clip = TextClip(
                        txt,
                        fontsize=final_font_size,  # Usar el tamaño de fuente especificado
                        font=font,  # Usar la fuente especificada
                        color=subtitle_color,
                        stroke_color=subtitle_stroke_color,
                        stroke_width=final_stroke_width,
                        method='caption',
                        size=(int(video_width * 0.9), None),
                        align='center'
                    ).set_start(start).set_duration(duration)

                    # Posición: mejorada para dar más espacio en los bordes
                    if position == "top":
                        # Posición superior con margen
                        txt_clip = txt_clip.set_position(('center', top_margin))
                    elif position == "center":
                        # Posición central (posiblemente con pequeño offset)
                        if center_offset == 0:
                            txt_clip = txt_clip.set_position('center')
                        else:
                            center_y = video_height // 2 + center_offset
                            txt_clip = txt_clip.set_position(('center', center_y))
                    else:  # bottom
                        # Posición inferior con margen adecuado
                        bottom_y = video_height - bottom_margin - txt_clip.h
                        txt_clip = txt_clip.set_position(('center', bottom_y))

                    # MEJORA: Aplicar fade out a subtítulos que aparecen al final del video
                    if fade_out_duration > 0 and video_clip.duration:
                        fade_start_time = video_clip.duration - fade_out_duration
                        # Si el subtítulo termina después del inicio del fade out, aplicar fade out
                        if end > fade_start_time:
                            # Calcular cuánto del subtítulo necesita fade out
                            subtitle_fade_start = max(0, fade_start_time - start)
                            if subtitle_fade_start < duration:
                                txt_clip = txt_clip.fadeout(duration - subtitle_fade_start)
                                if i == len(segments) - 1:  # Solo log para el último subtítulo
                                    logger.info(f"[Subtitles] Fade out aplicado al subtítulo final (duración: {duration - subtitle_fade_start:.2f}s)")

                    subtitle_clips.append(txt_clip)
                    processed_segments += 1
                    
                    if i == 0:
                        logger.info(f"[DEBUG] Primer subtítulo creado: '{txt[:30]}...' (color={subtitle_color}, size={final_font_size}px)")

                except Exception as clip_err:
                     # Reportar error pero continuar con los siguientes subtítulos
                     logger.error(f"[Subtitles] No se pudo crear TextClip para seg {i+1}: '{txt}'. Font:'{font}'. Error: {clip_err}", exc_info=True)

            if not subtitle_clips:
                logger.warning("[Subtitles] No se generaron clips de subtítulos válidos. Devolviendo clip original.")
                return video_clip

            logger.info(f"[Subtitles] Componiendo video con {processed_segments} clips de subtítulos.")
            # Componer sobre el clip original
            final_clip_with_subs = CompositeVideoClip([video] + subtitle_clips)
            
            # Restaurar el audio original si existe
            if original_audio is not None:
                try:
                    final_clip_with_subs = final_clip_with_subs.set_audio(original_audio)
                    logger.info("Audio restaurado exitosamente en el clip final")
                except Exception as audio_e:
                    logger.error(f"Error al restaurar audio: {audio_e}")
            
            logger.info(f"[Subtitles] Composición completada.")
            return final_clip_with_subs

        except Exception as e:
            logger.error(f"[Subtitles] Fallo general en add_hardcoded_subtitles: {e}", exc_info=True)
            if video is not None:
                video.close()
            if original_audio is not None:
                try:
                    original_audio.close()
                except:
                    pass
            return None
        finally:
            # No cerrar video_clip aquí, se maneja en el llamador
            pass

    def add_hardcoded_subtitles_with_bg(
        self,
        video_path: str,
        segments: list,
        output_path: str,
        font: str = "DejaVuSans",
        font_size: int = 40,
        color: str = "white",
        stroke_color: str = "black",
        stroke_width: int = 2,
        position: str = "bottom",
        bg_opacity: float = 0.5
    ) -> str:
        """Incrusta subtítulos en el video usando MoviePy con un fondo semi-transparente."""
        video = None
        final = None
        processed_segments = 0
        try:
            logger.info(f"Iniciando add_hardcoded_subtitles_with_bg para {video_path}")
            video = VideoFileClip(video_path)
            # Forzar recarga de tamaño por si acaso
            video_width, video_height = video.size
            logger.info(f"Video base cargado ({video_width}x{video_height}). Fuente: '{font}', Tamaño: {font_size}, Pos: {position}, BG: {bg_opacity}")
            
            # CORRECCIÓN: Usar el tamaño de fuente proporcionado por el usuario
            # Pero asegurar un tamaño mínimo razonable
            final_font_size = max(font_size, 20)  # Mínimo 20px
            
            # Usar el valor de stroke_width del parámetro, pero con un mínimo
            try:
                stroke_width_value = int(stroke_width)
            except (ValueError, TypeError):
                stroke_width_value = 2
                
            # Asegurar valores mínimos
            final_stroke_width = max(stroke_width_value, 2)
            
            # Asegurar opacidad en rango válido (0.0-1.0)
            bg_opacity_value = min(max(float(bg_opacity), 0.0), 1.0)
            
            # CORRECCIÓN: Usar el color pasado como parámetro
            subtitle_color = color  # Usar el color que el usuario especificó
            subtitle_stroke_color = stroke_color  # Usar el color de borde especificado
            
            logger.info(f"Subtítulos con fondo: font_size={final_font_size}px (solicitado: {font_size}px), stroke={final_stroke_width}px, opacity={bg_opacity_value:.1f}, color={subtitle_color}")

            # Calcular mejores márgenes basados en la resolución del video
            # Esto asegura que los subtítulos no queden muy pegados a los bordes
            top_margin = max(int(video_height * 0.05), 20)       # 5% desde arriba o mínimo 20px
            bottom_margin = max(int(video_height * 0.08), 30)    # 8% desde abajo o mínimo 30px
            center_offset = 0  # Sin offset adicional para center

            subtitle_clips = []
            for i, seg in enumerate(segments):
                txt = seg.get('text', '').strip()
                start = seg.get('start')
                end = seg.get('end')

                if not txt or start is None or end is None or end <= start:
                    continue

                duration = end - start

                try:
                    # 1. Crear texto principal
                    txt_clip = TextClip(
                        txt,
                        fontsize=final_font_size,  # Usar el tamaño de fuente especificado
                        font=font,
                        color=subtitle_color,
                        stroke_color=subtitle_stroke_color,
                        stroke_width=final_stroke_width,
                        method='caption',
                        size=(int(video_width * 0.85), None),
                        align='center'
                    )
                    
                    # 2. Crear un fondo negro semi-transparente con mejores márgenes
                    from moviepy.editor import ColorClip
                    
                    # Mejores márgenes: vertical y horizontal
                    margin_h = int(final_font_size * 0.7)  # Margen horizontal proporcional al tamaño de fuente
                    margin_v = int(final_font_size * 0.3)  # Margen vertical menor
                    
                    # Tamaño del fondo
                    bg_width = txt_clip.w + margin_h * 2
                    bg_height = txt_clip.h + margin_v * 2
                    
                    # Crear un fondo redondeado (simulación usando un color de fondo neutro)
                    # En realidad MoviePy no soporta esquinas redondeadas directamente
                    bg_clip = ColorClip(
                        size=(bg_width, bg_height),
                        color=(0, 0, 0)  # Negro
                    ).set_opacity(bg_opacity_value)
                    
                    # 3. Centrar texto sobre fondo
                    txt_pos = ('center', 'center')
                    txt_clip = txt_clip.set_position(txt_pos)
                    
                    # 4. Combinar texto y fondo
                    combined_clip = CompositeVideoClip(
                        [bg_clip, txt_clip],
                        size=bg_clip.size
                    ).set_duration(duration)
                    
                    # 5. Posicionar en video, mejorado para dar buen margen en los bordes
                    if position == "top":
                        # Posición superior con margen
                        final_pos = ('center', top_margin)
                    elif position == "center":
                        # Posición central (posiblemente con pequeño offset)
                        if center_offset == 0:
                            final_pos = 'center'
                        else:
                            center_y = video_height // 2 + center_offset
                            final_pos = ('center', center_y)
                    else:  # bottom (default)
                        # Posición inferior con margen mejorado
                        bottom_y = video_height - bottom_margin - combined_clip.h
                        final_pos = ('center', bottom_y)
                        
                    combined_clip = combined_clip.set_position(final_pos).set_start(start)
                    
                    subtitle_clips.append(combined_clip)
                    processed_segments += 1
                    
                    if i == 0:
                        logger.info(f"[DEBUG] Primer subtítulo con fondo creado: '{txt[:30]}...' (color={subtitle_color}, size={final_font_size}px)")

                except Exception as clip_err:
                     # Reportar error pero continuar con los siguientes subtítulos
                     logger.error(f"[Subtitles BG] Error en seg {i+1}: '{txt}'. Font:'{font}'. Error: {clip_err}", exc_info=True)

            if not subtitle_clips:
                 logger.warning("[Subtitles BG] No se generaron clips de subtítulos válidos.")
                 video.close()
                 # Copiar original si la ruta de salida es diferente
                 output_path_abs = os.path.abspath(output_path)
                 if os.path.abspath(video_path) != output_path_abs:
                      shutil.copyfile(video_path, output_path_abs)
                 return output_path_abs

            logger.info(f"[Subtitles BG] Componiendo video con {processed_segments} clips con fondo.")
            final = CompositeVideoClip([video] + subtitle_clips)

            # Escribir video final con subtítulos
            output_path_abs = os.path.abspath(output_path)
            temp_audio_path_sub = f'temp-sub-audio_{uuid.uuid4().hex}.m4a'
            logger.info(f"Escribiendo video subtitulado en: {output_path_abs}")
            
            num_cores = os.cpu_count() or 2
            logger.info(f"[DEBUG] Usando {num_cores} núcleos para la codificación.")
            threads_to_use = 2
            
            final.write_videofile(
                 output_path_abs,
                 fps=video.fps,
                 codec='libx264',
                 audio_codec='aac',
                 temp_audiofile=temp_audio_path_sub,
                 remove_temp=True,
                 logger='bar',
                 threads=threads_to_use,
                 preset='medium'
            )
            logger.info(f"[Subtitles BG] Video con subtítulos y fondo guardado en {output_path_abs}")
            return output_path_abs
        except Exception as e:
            logger.error(f"Error en add_hardcoded_subtitles_with_bg: {e}", exc_info=True)
            if video is not None:
                video.close()
            raise e

    # --- Otras funciones (add_text_to_video, apply_effect, create_video, edit_video, add_effects) ---
    # Mantenidas como estaban en tu versión anterior, o puedes quitarlas si no las usas.
    # ... (pegar aquí esas funciones si las necesitas) ...

# --- EL BLOQUE except FUERA DE LA CLASE YA NO ESTÁ ---