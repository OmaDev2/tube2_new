# utils/scene_generator.py
import json
from pathlib import Path
from typing import List, Dict, Optional, Callable
import logging
import math
import os
import yaml
import datetime # Added for save_scenes
import re

# Importar AIServices desde el módulo correcto
try:
    from utils.ai_services import AIServices
except ImportError:
    logging.error("No se pudo importar AIServices desde utils.ai_services.")
    # Define un placeholder si no se encuentra para evitar errores al cargar
    class AIServices:
        def generate_content(self, *args, **kwargs):
            return "[ERROR] AIServices no disponible."

logger = logging.getLogger(__name__)

# --- NUEVA CONSTANTE ---
# Si una escena dura más que esto (en segundos), se subdividirá para mantener el dinamismo.


class SceneGenerator:
    def __init__(self, config: Optional[Dict] = None, max_scene_duration: float = 12.0, use_auto_duration: bool = True, duration_per_image_manual: float = 10.0):
        self.config = config or self._load_void_config()
        self.video_gen_config = self.config.get('video_generation', {})
        self.max_scene_duration = max_scene_duration
        self.use_auto_duration = use_auto_duration
        self.duration_per_image_manual = duration_per_image_manual
        self.duration_per_image = self.video_gen_config.get('timing', {}).get('default_duration_per_image', 10.0)
        logger.info(f"SceneGenerator inicializado con duración/imagen base: {self.duration_per_image:.2f}s, max_scene_duration: {self.max_scene_duration}s, use_auto_duration: {self.use_auto_duration}, duration_per_image_manual: {self.duration_per_image_manual}")

    def _load_void_config(self) -> Dict:
        try:
            root_dir = Path(__file__).resolve().parent.parent
            voidrules_path = root_dir / ".voidrules"
            if not voidrules_path.exists():
                logger.warning(f".voidrules file not found at {voidrules_path}. Returning empty config.")
                return {}
            with open(voidrules_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error cargando .voidrules en SceneGenerator: {e}", exc_info=True)
            return {} # Devolver config vacía en caso de error

    def set_duration_per_image(self, duration: float):
        """Actualiza la duración por imagen."""
        self.duration_per_image = max(1.0, duration) # Asegura mínimo 1s
        logger.info(f"Duración por imagen actualizada a {self.duration_per_image:.2f} segundos")
        return self.duration_per_image

    def calculate_optimal_duration(self, audio_duration: float, desired_num_images: Optional[int] = None, transition_duration: float = 1.0, transition_type: str = "dissolve") -> float:
        if desired_num_images is None:
             estimated_images = self.estimate_num_images(audio_duration) 
             if estimated_images == 0: return self.duration_per_image 
             desired_num_images = estimated_images

        if desired_num_images <= 0: # Avoid division by zero or invalid calculations
            logger.warning("calculate_optimal_duration: desired_num_images es 0 o negativo. Devolviendo duración base.")
            return self.duration_per_image

        if transition_type.lower() == "none" or transition_duration <= 0 or desired_num_images <= 1:
            optimal_duration = audio_duration / desired_num_images
        else:
            total_overlap = (desired_num_images - 1) * transition_duration
            effective_audio_duration = audio_duration + total_overlap
            optimal_duration = effective_audio_duration / desired_num_images

        optimal_duration = max(min(optimal_duration, 30.0), 5.0) 
        logger.info(f"Duración óptima calculada por imagen: {optimal_duration:.2f}s para {desired_num_images} imágenes y {audio_duration:.2f}s de audio.")
        return optimal_duration

    def estimate_num_images(self, audio_duration: float, min_images: int = 4, max_duration_per_image: float = 15.0) -> int:
        if audio_duration <= 0: return min_images
        if max_duration_per_image <= 0: max_duration_per_image = 15.0
        
        num_images = max(min_images, int(math.ceil(audio_duration / max_duration_per_image)))
        logger.info(f"Estimadas {num_images} imágenes para {audio_duration:.2f}s de audio (max_dur_img: {max_duration_per_image}s).")
        return num_images

    def _segment_transcription_by_duration(self, transcription_segments: List[Dict], target_duration: float) -> List[Dict]:
        if not transcription_segments:
            return []
        
        timed_scenes = []
        current_scene_text_list = []
        current_scene_start_time = transcription_segments[0].get('start', 0) # Default to 0 if not present
        current_scene_accumulated_duration = 0
        scene_idx = 0

        for i, seg in enumerate(transcription_segments):
            seg_text = seg.get('text', '').strip()
            seg_start = seg.get('start')
            seg_end = seg.get('end')
            
            if seg_text is None or seg_start is None or seg_end is None: 
                logger.warning(f"Saltando segmento inválido en transcripción (faltan claves start/end/text): {seg}")
                continue
            
            seg_duration = seg_end - seg_start
            if seg_duration < 0:
                logger.warning(f"Segmento con duración negativa: {seg}. Saltando.")
                continue

            # Condition to finalize the current scene
            # Finalize if:
            # 1. Current scene is not empty AND adding the current segment would make it too long (e.g., > 125% of target)
            # 2. It's the last segment (must be added to some scene)
            finalize_this_scene = False
            if current_scene_text_list and (current_scene_accumulated_duration + seg_duration > target_duration * 1.25):
                finalize_this_scene = True
            
            if i == len(transcription_segments) - 1: # If it's the last segment
                current_scene_text_list.append(seg_text)
                current_scene_accumulated_duration += seg_duration
                finalize_this_scene = True # Force finalization

            if finalize_this_scene:
                scene_text_final = " ".join(current_scene_text_list)
                scene_end_time = current_scene_start_time + current_scene_accumulated_duration
                
                if current_scene_accumulated_duration <= 0:
                    logger.warning(f"Duración no positiva detectada: {current_scene_accumulated_duration}s. Saltando escena.")
                    continue

                timed_scenes.append({
                    'index': scene_idx,
                    'text': scene_text_final.strip(),
                    'start': current_scene_start_time,
                    'end': scene_end_time,
                    'duration': max(current_scene_accumulated_duration, 0.1)
                })
                scene_idx += 1
                
                # Reset for the next scene (if the current segment was not the one that got included in the finalized scene *and* it's not the last one)
                if i < len(transcription_segments) - 1 and not (i == len(transcription_segments) - 1 and seg_text in current_scene_text_list) : 
                    # If the current segment (seg) caused overflow and wasn't the last one, it starts the new scene.
                    current_scene_text_list = [seg_text]
                    current_scene_start_time = seg_start
                    current_scene_accumulated_duration = seg_duration
                else: # Last segment was processed and included, or current segment was included.
                    current_scene_text_list = []
                    current_scene_accumulated_duration = 0
                    # next scene start time will be set by the next segment that isn't skipped
            
            else: # Segment fits or scene is empty, so add it
                if not current_scene_text_list: # If this is the first segment for the current_scene
                    current_scene_start_time = seg_start
                current_scene_text_list.append(seg_text)
                current_scene_accumulated_duration += seg_duration
                 
        # Safety check for any remaining text (should be covered by last segment logic)
        if current_scene_text_list:
            scene_text_final = " ".join(current_scene_text_list)
            scene_end_time = current_scene_start_time + current_scene_accumulated_duration
            timed_scenes.append({
                'index': scene_idx,
                'text': scene_text_final.strip(),
                'start': current_scene_start_time,
                'end': scene_end_time,
                'duration': current_scene_accumulated_duration
            })

        logger.info(f"Transcripción segmentada en {len(timed_scenes)} escenas basadas en duración objetivo de {target_duration:.2f}s.")
        return timed_scenes

    def _segment_script_by_paragraphs(self, script_text: str) -> List[str]:
        """Divide el guión en párrafos usando saltos de línea dobles."""
        paragraphs = re.split(r'\n\s*\n', script_text)
        return [p.strip() for p in paragraphs if p.strip()]

    def _create_semantic_scenes(self, transcription_segments: List[Dict], target_duration: float = 12.0) -> List[Dict]:
        """
        Crea escenas semánticamente coherentes con subdivisión inteligente.
        
        LÓGICA MEJORADA V2.1 - CORRECCIONES APLICADAS:
        1. Detecta unidades narrativas completas
        2. Si unidad > 12s → subdividir en momentos visuales dinámicos
        3. Mantiene sincronización exacta con audio REAL
        4. Considera transiciones y fades
        5. NUEVO: Corrige codificación de caracteres
        6. NUEVO: Evita cortes en medio de frases importantes
        """
        if not transcription_segments:
            return []
        
        # PASO 0: Corregir codificación de caracteres en todos los segmentos
        transcription_segments = self._fix_encoding_in_segments(transcription_segments)
        
        # PARÁMETROS OPTIMIZADOS PARA CONTEXTO Y DINAMISMO
        # Derivados de max_scene_duration para flexibilidad
        MAX_IMAGE_DURATION = self.max_scene_duration  # El límite estricto es el que viene de la UI
        TARGET_IMAGE_DURATION = MAX_IMAGE_DURATION * 0.8  # Objetivo es un 80% del máximo
        MAX_NARRATIVE_UNIT = MAX_IMAGE_DURATION * 1.25 # Una unidad narrativa puede ser un poco más larga que una imagen
        MIN_NARRATIVE_DURATION = MAX_IMAGE_DURATION * 0.5 # Mínimo para mantener contexto (50% del máximo)
        TRANSITION_DURATION = 1.0     # Duración de transiciones (se mantiene fija por ahora)
        
        logger.info(f"🎬 Creando escenas dinámicas V2 (basado en UI max_scene_duration: {self.max_scene_duration}s):")
        logger.info(f"  • Unidad narrativa máxima: {MAX_NARRATIVE_UNIT}s")
        logger.info(f"  • Duración objetivo por imagen: {TARGET_IMAGE_DURATION}s")
        logger.info(f"  • Duración máxima por imagen: {MAX_IMAGE_DURATION}s")
        logger.info(f"  • Duración mínima por imagen: {MIN_NARRATIVE_DURATION}s")
        logger.info(f"  • Duración de transiciones: {TRANSITION_DURATION}s")
        
        # PASO 1: Detectar unidades narrativas completas
        narrative_units = self._detect_narrative_units(transcription_segments, MAX_NARRATIVE_UNIT)
        
        # PASO 2: Procesar cada unidad narrativa
        final_scenes = []
        
        for unit_idx, unit in enumerate(narrative_units):
            unit_duration = unit['duration']
            unit_text = unit['text']
            
            logger.info(f"Unidad {unit_idx+1}: {unit_duration:.1f}s - {unit_text[:60]}...")
            
            # Verificar si la unidad necesita subdivisión
            if unit_duration <= MAX_IMAGE_DURATION:
                # Unidad corta: usar como una sola escena
                final_scenes.append({
                    "index": len(final_scenes),
                    "text": unit_text,
                    "start": unit['start'],
                    "end": unit['end'],
                    "duration": unit_duration,
                    "narrative_unit": unit_idx + 1,
                    "visual_moment": 1,
                    "scene_type": "single_unit"
                })
                logger.info(f"  → Escena única ({unit_duration:.1f}s)")
            
            else:
                # Unidad larga: subdividir en momentos visuales dinámicos
                logger.info(f"  → Subdividiendo unidad larga ({unit_duration:.1f}s)")
                visual_moments = self._create_dynamic_visual_moments(unit, TARGET_IMAGE_DURATION, MAX_IMAGE_DURATION, MIN_NARRATIVE_DURATION)
                
                for moment_idx, moment in enumerate(visual_moments):
                    final_scenes.append({
                        "index": len(final_scenes),
                        "text": moment['text'],
                        "start": moment['start'],
                        "end": moment['end'],
                        "duration": moment['duration'],
                        "narrative_unit": unit_idx + 1,
                        "visual_moment": moment_idx + 1,
                        "scene_type": "subdivided_moment"
                    })
                    logger.info(f"    • Momento {moment_idx+1}: {moment['duration']:.1f}s - {moment['text'][:50]}...")
        
        logger.info(f"Resultado final: {len(final_scenes)} escenas visuales de {len(narrative_units)} unidades narrativas")
        return final_scenes

    def _detect_narrative_units(self, transcription_segments: List[Dict], max_unit_duration: float) -> List[Dict]:
        """
        Detecta unidades narrativas completas que pueden durar más que una imagen individual.
        Una unidad narrativa es una secuencia de eventos que deben mantenerse juntos conceptualmente.
        """
        if not transcription_segments:
            return []
        
        units = []
        current_unit_text = []
        current_unit_start = transcription_segments[0]['start']
        current_unit_duration = 0.0
        
        logger.info(f"Detectando unidades narrativas (máx: {max_unit_duration}s)...")
        
        for i, segment in enumerate(transcription_segments):
            segment_text = segment['text'].strip()
            segment_duration = segment['end'] - segment['start']
            
            # Agregar segmento a la unidad actual
            current_unit_text.append(segment_text)
            current_unit_duration = segment['end'] - current_unit_start
            
            # Determinar si es momento de cerrar la unidad narrativa
            is_narrative_break = self._is_strong_narrative_break(segment_text, current_unit_text)
            is_too_long = current_unit_duration >= max_unit_duration
            is_last_segment = i == len(transcription_segments) - 1
            
            should_close_unit = False
            close_reason = ""
            
            if is_last_segment:
                should_close_unit = True
                close_reason = "último segmento"
            elif is_too_long:
                should_close_unit = True  
                close_reason = f"duración máxima ({current_unit_duration:.1f}s)"
            elif is_narrative_break and current_unit_duration >= 8.0:  # Solo si ya tiene contenido suficiente
                should_close_unit = True
                close_reason = "ruptura narrativa fuerte"
            
            if should_close_unit:
                unit_text = " ".join(current_unit_text).strip()
                if unit_text:
                    units.append({
                        "text": unit_text,
                        "start": current_unit_start,
                        "end": segment['end'],
                        "duration": current_unit_duration,
                        "segments_count": len(current_unit_text)
                    })
                    logger.debug(f"  Unidad {len(units)}: {current_unit_duration:.1f}s ({close_reason})")
                
                # Iniciar nueva unidad (si no es el último)
                if not is_last_segment:
                    current_unit_text = []
                    current_unit_start = segment['end']
                    current_unit_duration = 0.0
        
        logger.info(f"Detectadas {len(units)} unidades narrativas")
        return units

    def _is_strong_narrative_break(self, current_segment: str, unit_text_so_far: List[str]) -> bool:
        """
        Detecta rupturas narrativas FUERTES que justifican cerrar una unidad narrativa completa.
        Más estricto que _is_narrative_break para evitar cortes prematuros.
        """
        if not unit_text_so_far or len(unit_text_so_far) < 3:  # Necesita al menos 3 segmentos
            return False
            
        current_text = current_segment.lower().strip()
        
        # INDICADORES DE RUPTURA NARRATIVA FUERTE
        strong_break_indicators = [
            # Cambios temporales grandes
            "años después", "tiempo después", "más tarde", "al día siguiente",
            "en otra ocasión", "posteriormente", "tiempo más tarde",
            
            # Cambios de escenario grandes  
            "en otro lugar", "en otra ciudad", "mientras tanto en",
            "en una ciudad diferente", "lejos de allí",
            
            # Nuevas secuencias narrativas
            "la historia continúa", "ahora", "por otro lado", "sin embargo",
            "pero la historia", "mientras esto ocurría",
            
            # Transiciones de biografía/narración
            "la vida de", "su biografía", "su historia", "el relato",
            "imagina que", "transportémonos", "veamos ahora",
            
            # Conclusiones/cierres
            "finalmente", "en conclusión", "para terminar", "cerramos",
            "el resultado", "así fue como"
        ]
        
        # INDICADORES DE CONTINUIDAD FUERTE (previenen corte)
        strong_continuity_indicators = [
            # Acciones físicas en progreso
            "sujeta en sus brazos", "llevaba en brazos", "caminaba con",
            "mientras caminaba", "al mismo tiempo", "en ese momento",
            
            # Secuencias de diálogo
            "le dijo", "respondió", "preguntó", "exclamó", "murmuró",
            "entonces él", "entonces ella", "luego añadió",
            
            # Descripciones físicas continuas
            "su rostro", "sus manos", "sus ojos", "su cuerpo",
            "golpeando", "respirando", "llorando", "gritando"
        ]
        
        # Verificar continuidad fuerte
        has_strong_continuity = any(indicator in current_text for indicator in strong_continuity_indicators)
        
        # Verificar ruptura fuerte
        has_strong_break = any(indicator in current_text for indicator in strong_break_indicators)
        
        # DECISIÓN: Solo romper si hay ruptura fuerte Y no hay continuidad fuerte
        if has_strong_continuity:
            logger.debug(f"    🔗 Continuidad fuerte detectada - NO romper unidad")
            return False
        elif has_strong_break:
            logger.debug(f"    ✂️ Ruptura fuerte detectada - Cerrar unidad narrativa")
            return True
        else:
            logger.debug(f"    ➡️ Sin indicadores fuertes - Continuar unidad")
            return False

    def _create_dynamic_visual_moments(self, narrative_unit: Dict, target_duration: float, max_duration: float, min_duration: float) -> List[Dict]:
        """
        Subdivide una unidad narrativa larga en momentos visuales dinámicos.
        MEJORADO: Usa timestamps reales del audio y respeta límites estrictos.
        """
        unit_segments = narrative_unit.get('segments', [])
        unit_text = narrative_unit['text']
        unit_start = narrative_unit['start']
        unit_end = narrative_unit['end']
        unit_duration = narrative_unit['duration']
        
        # Calcular número óptimo de momentos basado en límites estrictos
        num_moments = max(2, math.ceil(unit_duration / max_duration))
        
        # Si tenemos segmentos de audio, usar distribución inteligente
        if unit_segments:
            return self._subdivide_using_audio_segments(unit_segments, target_duration, max_duration, min_duration)
        
        # Fallback: distribución uniforme
        moment_duration = unit_duration / num_moments
        
        # Asegurar que no exceda el máximo
        if moment_duration > max_duration:
            num_moments = math.ceil(unit_duration / max_duration)
            moment_duration = unit_duration / num_moments
        
        logger.info(f"    Subdividiendo en {num_moments} momentos de ~{moment_duration:.1f}s cada uno")
        
        # Dividir el texto en frases/segmentos lógicos
        sentences = self._split_into_logical_segments(unit_text)
        
        # Distribuir frases entre momentos
        moments = []
        sentences_per_moment = max(1, len(sentences) // num_moments)
        
        for moment_idx in range(num_moments):
            start_idx = moment_idx * sentences_per_moment
            
            # Para el último momento, incluir todas las frases restantes
            if moment_idx == num_moments - 1:
                end_idx = len(sentences)
            else:
                end_idx = (moment_idx + 1) * sentences_per_moment
            
            moment_sentences = sentences[start_idx:end_idx]
            moment_text = " ".join(moment_sentences).strip()
            
            # Calcular tiempos basados en proporción
            moment_start = unit_start + (moment_idx * moment_duration)
            moment_end = unit_start + ((moment_idx + 1) * moment_duration)
            
            # Ajustar el último momento para que termine exactamente con la unidad
            if moment_idx == num_moments - 1:
                moment_end = unit_end
            
            actual_duration = moment_end - moment_start
            
            if moment_text:  # Solo agregar si hay texto
                moments.append({
                    "text": self._enhance_visual_moment_text(moment_text, moment_idx + 1, num_moments),
                    "start": moment_start,
                    "end": moment_end,
                    "duration": actual_duration
                })
        
        return moments
    
    def _subdivide_using_audio_segments(self, unit_segments: List[Dict], target_duration: float, max_duration: float, min_duration: float) -> List[Dict]:
        """
        Subdivide usando los segmentos reales del audio para máxima precisión.
        MEJORADA V2.1: Usa timestamps exactos + evita cortes problemáticos.
        """
        
        if not unit_segments:
            return []
        
        moments = []
        current_moment_segments = []
        current_moment_start = unit_segments[0]['start']
        current_moment_duration = 0.0
        
        logger.info(f"    📡 Usando {len(unit_segments)} segmentos de audio para subdivisión precisa (V2.1)")
        
        for i, segment in enumerate(unit_segments):
            current_moment_segments.append(segment)
            current_moment_duration = segment['end'] - current_moment_start
            
            # Determinar si cerrar el momento actual
            should_close_moment = False
            close_reason = ""
            
            # Es el último segmento
            if i == len(unit_segments) - 1:
                should_close_moment = True
                close_reason = "último segmento"
            
            # Ha alcanzado duración máxima (límite estricto)
            elif current_moment_duration >= max_duration:
                should_close_moment = True
                close_reason = f"límite máximo ({current_moment_duration:.1f}s >= {max_duration}s)"
            
            # Ha alcanzado duración objetivo Y hay un buen punto de corte (MEJORADO)
            elif (current_moment_duration >= target_duration and 
                  self._is_good_audio_cut_point(segment['text']) and
                  not self._is_problematic_cut(segment['text'])):
                should_close_moment = True
                close_reason = f"duración objetivo + punto de corte natural (sin problemas)"
            
            # Hay una pausa larga después de este segmento
            elif i < len(unit_segments) - 1:
                next_segment = unit_segments[i + 1]
                pause_duration = next_segment['start'] - segment['end']
                
                if (pause_duration > 0.8 and current_moment_duration >= min_duration):
                    should_close_moment = True
                    close_reason = f"pausa natural ({pause_duration:.1f}s)"
            
            if should_close_moment:
                # Crear momento visual con timestamps EXACTOS (sin extensiones)
                moment_text = " ".join(seg['text'].strip() for seg in current_moment_segments)
                moment_end = segment['end']  # Usar timestamp exacto del audio
                actual_duration = moment_end - current_moment_start
                
                # CORRECCIÓN: Asegurar que no hay extensiones artificiales
                # El momento debe terminar exactamente donde termina el audio real
                
                # NUEVA VALIDACIÓN: Verificar contexto completo antes de crear momento
                if actual_duration >= min_duration and self._has_complete_context(moment_text):
                    moments.append({
                        'text': moment_text,
                        'start': current_moment_start,
                        'end': moment_end,
                        'duration': actual_duration,
                        'segments_count': len(current_moment_segments),
                        'close_reason': close_reason,
                        'context_complete': True
                    })
                    
                    logger.info(f"      ✓ Momento: {actual_duration:.1f}s ({close_reason})")
                else:
                    # Si es muy corto O le falta contexto, combinar con el momento anterior
                    if moments:
                        last_moment = moments[-1]
                        # Verificar si la combinación mejora el contexto
                        combined_text = last_moment['text'] + " " + moment_text
                        
                        if self._improves_context(last_moment['text'], combined_text):
                            last_moment['text'] = combined_text
                            last_moment['end'] = moment_end
                            last_moment['duration'] = moment_end - last_moment['start']
                            last_moment['segments_count'] += len(current_moment_segments)
                            last_moment['context_complete'] = True
                            
                            logger.info(f"      🔗 Combinado para mejorar contexto: {last_moment['duration']:.1f}s")
                        else:
                            # Crear momento separado si no mejora el contexto
                            moments.append({
                                'text': moment_text,
                                'start': current_moment_start,
                                'end': moment_end,
                                'duration': actual_duration,
                                'segments_count': len(current_moment_segments),
                                'close_reason': f"{close_reason} (contexto independiente)",
                                'context_complete': self._has_complete_context(moment_text)
                            })
                    else:
                        # Es el primer momento, mantenerlo aunque sea corto
                        moments.append({
                            'text': moment_text,
                            'start': current_moment_start,
                            'end': moment_end,
                            'duration': actual_duration,
                            'segments_count': len(current_moment_segments),
                            'close_reason': f"{close_reason} (primer momento)",
                            'context_complete': self._has_complete_context(moment_text)
                        })
                        
                        if actual_duration < min_duration:
                            logger.warning(f"      ⚠️ Primer momento corto: {actual_duration:.1f}s")
                        else:
                            logger.info(f"      ✓ Primer momento: {actual_duration:.1f}s")
                
                # Iniciar nuevo momento
                current_moment_segments = []
                if i < len(unit_segments) - 1:
                    current_moment_start = unit_segments[i + 1]['start']
                    current_moment_duration = 0.0
        
        # Validación final: asegurar que no hay momentos demasiado largos
        validated_moments = []
        for moment in moments:
            if moment['duration'] <= max_duration:
                validated_moments.append(moment)
            else:
                # Momento aún muy largo: forzar subdivisión
                logger.warning(f"      🔧 Forzando subdivisión de momento largo: {moment['duration']:.1f}s")
                forced_sub_moments = self._force_subdivide_moment(moment, max_duration, min_duration)
                validated_moments.extend(forced_sub_moments)
        
        return validated_moments
    
    def _is_good_audio_cut_point(self, text: str) -> bool:
        """
        Determina si un segmento de audio es un buen punto para cortar.
        MEJORADO: Más criterios para puntos de corte naturales.
        """
        
        text_lower = text.lower().strip()
        
        # Excelentes puntos de corte (finales de oración)
        excellent_cuts = [".", "!", "?"]
        for cut in excellent_cuts:
            if text_lower.endswith(cut):
                return True
        
        # Buenos puntos de corte (pausas naturales)
        good_cuts = [",", ";", ":", " y ", " pero ", " sin embargo ", " además "]
        for cut in good_cuts:
            if cut in text_lower[-20:]:  # En los últimos 20 caracteres
                return True
        
        # Conectores que permiten corte suave
        connectors = [
            "entonces", "después", "luego", "mientras", "cuando", "donde", 
            "como", "así", "también", "además", "por tanto"
        ]
        
        words = text_lower.split()
        if words and words[-1] in connectors:
            return True
        
        return False
    
    def _force_subdivide_moment(self, moment: Dict, max_duration: float, min_duration: float) -> List[Dict]:
        """
        Fuerza la subdivisión de un momento que sigue siendo demasiado largo.
        Último recurso para garantizar límites estrictos.
        """
        
        moment_duration = moment['duration']
        moment_text = moment['text']
        moment_start = moment['start']
        moment_end = moment['end']
        
        # Calcular número de sub-momentos necesarios
        num_sub_moments = math.ceil(moment_duration / max_duration)
        sub_duration = moment_duration / num_sub_moments
        
        logger.info(f"        🔧 Forzando {num_sub_moments} sub-momentos de ~{sub_duration:.1f}s")
        
        # Dividir texto en partes aproximadamente iguales
        sentences = self._split_text_into_sentences(moment_text)
        sentences_per_sub = max(1, len(sentences) // num_sub_moments)
        
        sub_moments = []
        
        for sub_idx in range(num_sub_moments):
            start_sentence = sub_idx * sentences_per_sub
            
            if sub_idx == num_sub_moments - 1:
                # Último sub-momento: incluir oraciones restantes
                end_sentence = len(sentences)
            else:
                end_sentence = (sub_idx + 1) * sentences_per_sub
            
            sub_sentences = sentences[start_sentence:end_sentence]
            sub_text = " ".join(sub_sentences).strip()
            
            # Calcular tiempos proporcionales
            sub_start = moment_start + (sub_idx * sub_duration)
            sub_end = moment_start + ((sub_idx + 1) * sub_duration)
            
            # Ajustar último sub-momento para que termine exactamente
            if sub_idx == num_sub_moments - 1:
                sub_end = moment_end
            
            actual_sub_duration = sub_end - sub_start
            
            if sub_text and actual_sub_duration >= min_duration:
                sub_moments.append({
                    'text': sub_text,
                    'start': sub_start,
                    'end': sub_end,
                    'duration': actual_sub_duration,
                    'segments_count': 1,  # Estimado
                    'close_reason': 'forced_subdivision'
                })
                
                logger.info(f"          • Sub-momento {sub_idx+1}: {actual_sub_duration:.1f}s")
        
        return sub_moments
    
    def _split_text_into_sentences(self, text: str) -> List[str]:
        """
        Divide texto en oraciones para subdivisión forzada.
        """
        import re
        
        # Dividir por puntos, pero mantener oraciones completas
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Limpiar y filtrar
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Si hay muy pocas oraciones, dividir por comas
        if len(sentences) < 3:
            segments = re.split(r',\s+', text)
            sentences = [s.strip() for s in segments if s.strip()]
        
        # Si aún hay muy pocos segmentos, dividir por palabras
        if len(sentences) < 2:
            words = text.split()
            # Agrupar palabras en segmentos de ~10 palabras
            sentences = []
            for i in range(0, len(words), 10):
                segment = " ".join(words[i:i+10])
                sentences.append(segment)
        
        return sentences

    def _split_into_logical_segments(self, text: str) -> List[str]:
        """
        Divide el texto en segmentos lógicos para distribuir entre momentos visuales.
        """
        import re
        
        # Dividir por puntos, pero mantener frases completas
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Limpiar y filtrar
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Si hay muy pocas frases, dividir por comas
        if len(sentences) < 3:
            segments = re.split(r',\s+', text)
            sentences = [s.strip() for s in segments if s.strip()]
        
        return sentences

    def _enhance_visual_moment_text(self, text: str, moment_num: int, total_moments: int) -> str:
        """
        Mejora el texto del momento visual para generar mejores prompts de imagen.
        Agrega contexto visual específico según la posición en la secuencia.
        """
        # Agregar descriptores visuales según la posición
        if moment_num == 1 and total_moments > 1:
            # Primer momento: establecer escena
            if "madre" in text.lower():
                text += " [Enfoque inicial en la expresión de desesperación]"
            elif "blas" in text.lower() and "camina" in text.lower():
                text += " [Vista de apertura de la escena]"
        elif moment_num == total_moments and total_moments > 1:
            # Último momento: momento culminante
            if "niño" in text.lower() or "hijo" in text.lower():
                text += " [Close-up del momento crítico]"
            elif "milagro" in text.lower() or "sanó" in text.lower():
                text += " [Momento climático de la curación]"
        
        return text

    def _align_paragraphs_to_transcription(self, paragraphs: List[str], transcription_segments: List[Dict], max_scene_duration: float = 12.0) -> List[Dict]:
        """
        NUEVO: Usa segmentación semántica en lugar de alineación compleja con fuzzywuzzy.
        Esto es más confiable y siempre produce escenas sincronizadas.
        """
        logger.info("Usando segmentación semántica inteligente (sin fuzzywuzzy)")
        
        if not transcription_segments:
            return []
        
        if self.use_auto_duration:
            total_duration = transcription_segments[-1]['end'] - transcription_segments[0]['start']
            num_paragraphs = len([p for p in paragraphs if p.strip()])
            target_duration = total_duration / max(num_paragraphs, 1) if num_paragraphs > 0 else self.max_scene_duration
            
            # Ajustar duración objetivo para que sea razonable (8-15 segundos) si es automática
            target_duration = max(8.0, min(target_duration, 15.0))
            logger.info(f"Duración objetivo calculada automáticamente: {target_duration:.1f}s (total: {total_duration:.1f}s, párrafos: {num_paragraphs})")
        else:
            target_duration = self.duration_per_image_manual
            logger.info(f"Duración objetivo manual: {target_duration:.1f}s")
        
        # Crear escenas semánticas
        return self._create_semantic_scenes(transcription_segments, target_duration)
    
    def generate_scenes_from_script(self, script_content: str, transcription_segments: List[Dict], mode: str, project_info: Dict, image_prompt_config: Dict, ai_service: AIServices) -> List[Dict]:
        """Genera escenas con el nuevo modo híbrido por párrafos y una subdivisión robusta."""
        logger.info(f"Generando escenas con modo: '{mode}'...")
        
        if mode == "Por Párrafos (Híbrido)":
            # --- LÓGICA POR PÁRRAFOS (HÍBRIDA) ---
            paragraphs = self._segment_script_by_paragraphs(script_content)
            timed_scenes = self._align_paragraphs_to_transcription(paragraphs, transcription_segments, max_scene_duration=self.max_scene_duration)
            
            final_scenes_base = []
            for scene in timed_scenes:
                if scene['duration'] > self.max_scene_duration:
                    logger.info(f"Scene {scene['index']} is too long ({scene['duration']:.1f}s > {self.max_scene_duration}s). Subdividing robustly.")
                    
                    # Robust subdivision logic
                    scene_segments = [
                        seg for seg in transcription_segments 
                        if seg['start'] < scene['end'] and seg['end'] > scene['start']
                    ]
                    
                    if not scene_segments:
                        logger.warning(f"No segments found for long scene {scene['index']}. Using as is.")
                        scene_copy = scene.copy()
                        scene_copy["index"] = len(final_scenes_base)
                        final_scenes_base.append(scene_copy)
                        continue

                    target_sub_duration = self.max_scene_duration * 0.9
                    num_sub_scenes = max(2, round(scene['duration'] / target_sub_duration))
                    
                    k, m = divmod(len(scene_segments), num_sub_scenes)
                    segment_groups = [
                        scene_segments[i*k+min(i, m):(i+1)*k+min(i+1, m)] 
                        for i in range(num_sub_scenes)
                    ]
                    
                    for group in segment_groups:
                        if not group: continue
                        
                        sub_scene_text = " ".join(s['text'].strip() for s in group)
                        sub_start_time = group[0]['start']
                        sub_end_time = group[-1]['end']
                        sub_duration = sub_end_time - sub_start_time
                        
                        if sub_duration > 0:
                            final_scenes_base.append({
                                "index": len(final_scenes_base),
                                "text": sub_scene_text,
                                "start": sub_start_time,
                                "end": sub_end_time,
                                "duration": sub_duration
                            })
                else:
                    scene_copy = scene.copy()
                    scene_copy["index"] = len(final_scenes_base)
                    final_scenes_base.append(scene_copy)
            
            logger.info(f"Segmentación por párrafos resultó en {len(final_scenes_base)} escenas base.")
            
            # Generar prompts para estas escenas finales.
            final_scenes_with_prompts = self.generate_prompts_for_scenes(
                final_scenes_base, project_info, image_prompt_config, ai_service
            )
            logger.info(f"Se generaron prompts para {len(final_scenes_with_prompts)} escenas.")

            return final_scenes_with_prompts
        
        else:
            # Fallback a métodos anteriores (sin cambios)
            return self._generate_scenes_legacy(script_content, transcription_segments, mode)

    def _generate_scenes_legacy(self, script_content: str, transcription_segments: List[Dict], mode: str) -> List[Dict]:
        """Métodos de segmentación anteriores para compatibilidad."""
        if mode == "Por Duración (Basado en Audio)":
            # Lógica original por duración
            scenes = []
            for i, seg in enumerate(transcription_segments):
                scenes.append({
                    "index": i,
                    "text": seg['text'],
                    "start": seg['start'],
                    "end": seg['end'],
                    "duration": seg['end'] - seg['start']
                })
            return scenes
        else:
            # Automático (Texto) - dividir por párrafos simples
            paragraphs = script_content.split('\n\n')
            scenes = []
            duration_per_scene = 10.0  # duración fija
            
            for i, paragraph in enumerate(paragraphs):
                if paragraph.strip():
                    scenes.append({
                        "index": i,
                        "text": paragraph.strip(),
                        "start": i * duration_per_scene,
                        "end": (i + 1) * duration_per_scene,
                        "duration": duration_per_scene
                    })
            return scenes

    def generate_prompts_for_scenes(self, scenes: List[Dict], project_info: Dict, image_prompt_config: Dict, ai_service: AIServices) -> List[Dict]:
        """Genera prompts para las escenas con sistema de fallback robusto."""
        
        # 🔍 DEBUG INICIAL - CONFIGURACIÓN RECIBIDA
        logger.info("=" * 100)
        logger.info("🔍 DEBUG COMPLETO - INICIANDO GENERACIÓN DE PROMPTS")
        logger.info("=" * 100)
        logger.info(f"📊 Proyecto: {project_info.get('titulo', 'Sin título')}")
        logger.info(f"📊 Total de escenas: {len(scenes)}")
        logger.info(f"📊 Configuración inicial recibida:")
        prompt_obj_name = "No definido"
        if image_prompt_config.get('prompt_obj') and hasattr(image_prompt_config['prompt_obj'], 'get'):
            prompt_obj_name = image_prompt_config['prompt_obj'].get('nombre', 'Sin nombre')
        logger.info(f"  • prompt_obj inicial: {prompt_obj_name}")
        logger.info(f"  • historical_variables inicial: {image_prompt_config.get('historical_variables', 'No definidas')}")
        logger.info(f"  • providers: {image_prompt_config.get('img_prompt_providers_priority', ['gemini'])}")
        
        # 🏛️ DETECCIÓN AUTOMÁTICA DE CONTEXTO HISTÓRICO
        logger.info("🏛️ Ejecutando detección automática de contexto histórico...")
        original_config = image_prompt_config.copy()
        image_prompt_config = self._force_historical_prompt_if_needed(project_info, image_prompt_config)
        
        # DEBUG: Mostrar si cambió la configuración
        if original_config != image_prompt_config:
            logger.info("✅ Configuración modificada por detección automática")
            logger.info(f"  • Prompt nuevo: {image_prompt_config.get('prompt_obj', {}).get('nombre', 'No definido')}")
            logger.info(f"  • Variables históricas aplicadas: {list(image_prompt_config.get('historical_variables', {}).keys())}")
        else:
            logger.info("ℹ️ Configuración no modificada (ya era correcta o no aplicable)")
        
        # VERIFICACIÓN CRÍTICA DEL AI_SERVICE
        if not ai_service:
            logger.error("🚨 ai_service es None! No se pueden generar prompts de imagen.")
            for scene in scenes:
                scene['image_prompt'] = f"[ERROR] AIServices no disponible. Prompt básico: {scene.get('text', '')[:350]}"
            return scenes
        
        prompt_obj = image_prompt_config.get('prompt_obj')
        provider_priority_list = image_prompt_config.get('img_prompt_providers_priority', ['gemini'])
        
        logger.info(f"🔍 CONFIGURACIÓN FINAL PARA GENERACIÓN:")
        logger.info(f"  • prompt_obj: {prompt_obj.get('nombre', 'Sin nombre') if prompt_obj else 'None'}")
        logger.info(f"  • provider_priority_list: {provider_priority_list}")
        logger.info(f"  • ai_service disponible: {ai_service is not None}")
        logger.info(f"  • variables históricas finales: {image_prompt_config.get('historical_variables', {})}")
        logger.info("=" * 100)
        
        if not prompt_obj:
            logger.warning("No se proporcionó plantilla de prompt. Usando fallback simple.")
            for scene in scenes:
                scene['image_prompt'] = f"Photorealistic, cinematic: {scene.get('text', '')[:350]}"
            return scenes

        # 🎭 GENERACIÓN DE DOSSIER DE PERSONAJE PARA COHERENCIA VISUAL (FASE 2)
        character_dossier = None
        if self._should_use_character_dossier(project_info):
            logger.info("🎭 INICIANDO GENERACIÓN DE DOSSIER PARA COHERENCIA VISUAL")
            character_dossier = self._generate_character_dossier(project_info, ai_service)
            if character_dossier:
                logger.info(f"✅ Dossier generado exitosamente ({len(character_dossier)} caracteres)")
                logger.info("🎭 Coherencia visual del personaje ACTIVADA para todas las escenas")
            else:
                logger.warning("⚠️ No se pudo generar el dossier, continuando sin coherencia de personaje")

        system_prompt = prompt_obj.get("system_prompt", "")
        user_prompt_template = prompt_obj.get("user_prompt", "Generate an image for: {scene_text}")

        for i, scene in enumerate(scenes):
            # Preparar todas las variables disponibles para el template
            template_variables = {
                'scene_text': scene['text'],
                'titulo': project_info.get("titulo", ""),
                'contexto': project_info.get("contexto", ""),
                'style': image_prompt_config.get('style', '')  # Variable de estilo
            }
            
            # 🏛️ AÑADIR VARIABLES HISTÓRICAS SI ESTÁN DISPONIBLES
            historical_variables = image_prompt_config.get('historical_variables', {})
            if historical_variables:
                # 🔧 VALIDAR VARIABLES HISTÓRICAS - detectar si están vacías y usar detección automática como fallback
                valid_historical_vars = {}
                empty_vars = []
                
                for key, value in historical_variables.items():
                    if value and str(value).strip():  # Variable tiene contenido
                        valid_historical_vars[key] = value
                    else:  # Variable vacía
                        empty_vars.append(key)
                
                if valid_historical_vars:
                    template_variables.update(valid_historical_vars)
                    logger.info(f"[Escena {i+1}] 🏛️ Variables históricas válidas añadidas: {list(valid_historical_vars.keys())}")
                
                if empty_vars:
                    logger.warning(f"[Escena {i+1}] ⚠️ Variables históricas vacías detectadas: {empty_vars}")
                    logger.info(f"[Escena {i+1}] 🤖 Aplicando detección automática para variables faltantes...")
                    
                    # Detectar contexto automáticamente para variables faltantes
                    titulo = project_info.get("titulo", "")
                    auto_context = self._detect_historical_context_from_title(titulo)
                    
                    # Solo usar las variables automáticas que estaban vacías
                    filled_vars = []
                    for var in empty_vars:
                        if var in auto_context and auto_context[var]:
                            template_variables[var] = auto_context[var]
                            filled_vars.append(var)
                            logger.info(f"[Escena {i+1}] 🤖 Variable '{var}' completada automáticamente")
                    
                    if filled_vars:
                        logger.info(f"[Escena {i+1}] ✅ Variables completadas automáticamente: {filled_vars}")
                    else:
                        logger.warning(f"[Escena {i+1}] ❌ No se pudieron completar automáticamente las variables vacías")
            else:
                logger.debug(f"[Escena {i+1}] No hay variables históricas disponibles")
            
            # Obtener las variables requeridas por la plantilla
            template_vars_required = prompt_obj.get('variables', [])
            
            # 🎭 INTEGRACIÓN CON DOSSIER DE PERSONAJE (FASE 2)
            if character_dossier:
                logger.info(f"[Escena {i+1}] 🎭 APLICANDO COHERENCIA VISUAL DEL PERSONAJE")
                
                # Detectar edad del personaje en esta escena
                scene_text = scene.get('text', '')
                project_context = project_info.get('contexto', '')
                detected_age_stage = self._detect_character_age_stage(scene_text, project_context)
                
                # Extraer descripción específica del dossier
                character_description = self._extract_character_description_from_dossier(character_dossier, detected_age_stage)
                
                if character_description:
                    # Añadir la descripción del personaje como variable separada
                    template_variables['character_description'] = character_description
                    
                    logger.info(f"[Escena {i+1}] ✅ Descripción del personaje aplicada")
                    logger.info(f"[Escena {i+1}] 🎯 Edad detectada: {detected_age_stage.upper()}")
                    logger.info(f"[Escena {i+1}] 📝 Descripción: {character_description[:100]}...")
                else:
                    # Si no hay descripción específica, usar string vacío para evitar errores
                    template_variables['character_description'] = ""
                    logger.warning(f"[Escena {i+1}] ⚠️ No se pudo extraer descripción para edad: {detected_age_stage}")
            else:
                # Si no hay dossier, usar string vacío para la descripción del personaje
                template_variables['character_description'] = ""
            
            # Filtrar solo las variables que realmente necesita la plantilla
            filtered_variables = {
                var: template_variables.get(var, '') 
                for var in template_vars_required 
                if var in template_variables
            }
            
            # 🏛️ LOGGING ESPECIAL PARA PROMPT HISTÓRICO
            if prompt_obj.get('nombre') == "Escenas Fotorrealistas Históricamente Precisas":
                logger.info(f"[Escena {i+1}] 🏛️ PROMPT HISTÓRICO DETECTADO")
                logger.info(f"[Escena {i+1}] 🏛️ Variables históricas: {historical_variables}")
                logger.info(f"[Escena {i+1}] 🏛️ Variables filtradas: {filtered_variables}")
                
                # 🎭 LOGGING ESPECIAL PARA COHERENCIA DE PERSONAJE
                if character_dossier:
                    logger.info(f"[Escena {i+1}] 🎭 COHERENCIA DE PERSONAJE ACTIVA")
                    if 'character_description' in template_variables:
                        logger.info(f"[Escena {i+1}] 🎭 Descripción integrada en prompt histórico")
            
            # DEBUG: Mostrar las variables filtradas antes de formatear el user_prompt
            logger.debug(f"[Escena {i+1}] DEBUG - filtered_variables antes de formatear user_prompt: {filtered_variables}")

            try:
                user_prompt = user_prompt_template.format(**filtered_variables)
            except KeyError as e:
                logger.warning(f"[Escena {i+1}] Variable faltante en template: {e}. Usando template básico.")
                user_prompt = f"Generate an image for: {scene['text']}"
            
            generated_prompt = None
            
            # 🔍 DEBUG COMPLETO DEL PROMPT
            logger.info(f"[Escena {i+1}] =" * 80)
            logger.info(f"[Escena {i+1}] 🔍 DEBUG COMPLETO - GENERACIÓN DE PROMPT")
            logger.info(f"[Escena {i+1}] =" * 80)
            logger.info(f"[Escena {i+1}] 📋 Prompt template: {prompt_obj.get('nombre', 'Sin nombre')}")
            logger.info(f"[Escena {i+1}] 🔧 Proveedores disponibles: {provider_priority_list}")
            logger.info(f"[Escena {i+1}] 📊 Variables del template requeridas: {template_vars_required}")
            logger.info(f"[Escena {i+1}] ✅ Variables filtradas disponibles: {list(filtered_variables.keys())}")
            logger.info(f"[Escena {i+1}] 🏛️ Variables históricas pasadas: {historical_variables}")
            
            # DEBUG: Mostrar cada variable y su valor
            logger.info(f"[Escena {i+1}] 📝 VALORES DE VARIABLES:")
            for var_name, var_value in filtered_variables.items():
                logger.info(f"[Escena {i+1}]   • {var_name}: '{var_value[:100]}{'...' if len(str(var_value)) > 100 else ''}'")
            
            # DEBUG: Mostrar el system prompt completo
            logger.info(f"[Escena {i+1}] 🤖 SYSTEM PROMPT ENVIADO A GEMINI:")
            logger.info(f"[Escena {i+1}] {'-' * 60}")
            logger.info(f"[Escena {i+1}] {system_prompt}")
            logger.info(f"[Escena {i+1}] {'-' * 60}")
            
            # DEBUG: Mostrar el user prompt completo
            logger.info(f"[Escena {i+1}] 👤 USER PROMPT ENVIADO A GEMINI:")
            logger.info(f"[Escena {i+1}] {'-' * 60}")
            logger.info(f"[Escena {i+1}] {user_prompt}")
            logger.info(f"[Escena {i+1}] {'-' * 60}")
            
            for provider in provider_priority_list:
                try:
                    logger.info(f"[Escena {i+1}] Intentando generar prompt con: {provider.upper()}")
                    
                    # Usar modelos específicos si están disponibles, sino usar por defecto
                    provided_models = image_prompt_config.get('img_prompt_models', {})
                    if provider in provided_models:
                        model = provided_models[provider]
                    else:
                        # Fallback a modelos por defecto
                        model_map = {
                            'gemini': 'models/gemini-2.5-flash-lite-preview-06-17',
                            'openai': 'gpt-3.5-turbo',
                            'ollama': 'llama3.2'
                        }
                        model = model_map.get(provider, 'default')
                    
                    logger.info(f"[Escena {i+1}] 🔍 DEBUG - Usando modelo: {model}")
                    logger.info(f"[Escena {i+1}] 🔍 DEBUG - Llamando ai_service.generate_content...")
                    
                    # Añadir delay entre requests para evitar rate limits
                    if i > 0 and provider == "gemini":
                        delay = 0.5  # 500ms entre requests de Gemini
                        logger.info(f"[Escena {i+1}] ⏱️ Delay de {delay}s para evitar rate limits...")
                        import time
                        time.sleep(delay)
                    
                    generated_text = ai_service.generate_content(
                        provider=provider, 
                        model=model, 
                        system_prompt=system_prompt, 
                        user_prompt=user_prompt
                    )
                    
                    # 🔍 DEBUG COMPLETO DE LA RESPUESTA
                    logger.info(f"[Escena {i+1}] 🤖 RESPUESTA COMPLETA DE {provider.upper()}:")
                    logger.info(f"[Escena {i+1}] {'=' * 60}")
                    logger.info(f"[Escena {i+1}] Tipo: {type(generated_text)}")
                    logger.info(f"[Escena {i+1}] Longitud: {len(str(generated_text)) if generated_text else 0} caracteres")
                    logger.info(f"[Escena {i+1}] Contenido completo:")
                    logger.info(f"[Escena {i+1}] {'-' * 40}")
                    if generated_text:
                        # Mostrar respuesta completa con numeración de líneas
                        lines = str(generated_text).split('\n')
                        for line_num, line in enumerate(lines, 1):
                            logger.info(f"[Escena {i+1}] {line_num:3d}: {line}")
                    else:
                        logger.info(f"[Escena {i+1}] [RESPUESTA VACÍA O NULA]")
                    logger.info(f"[Escena {i+1}] {'-' * 40}")
                    logger.info(f"[Escena {i+1}] {'=' * 60}")
                    
                    if generated_text and "[ERROR]" not in generated_text:
                        logger.info(f"[Escena {i+1}] ✅ ÉXITO con {provider.upper()}")
                        generated_prompt = generated_text.strip()
                        break
                    else:
                        logger.warning(f"[Escena {i+1}] ❌ FALLO con {provider.upper()}")
                        logger.warning(f"[Escena {i+1}] Motivo: {'Texto vacío o nulo' if not generated_text else 'Contiene [ERROR]'}")
                except Exception as e:
                    logger.error(f"[Escena {i+1}] ❌ Fallo grave con {provider.upper()}: {e}. Intentando siguiente proveedor.")
            
            if not generated_prompt:
                logger.error(f"[Escena {i+1}] 🚨 Todos los proveedores fallaron. Usando prompt de emergencia. Texto de escena: {scene['text'][:100]}...")
                generated_prompt = f"Photorealistic, cinematic, high detail: {scene['text'][:350]}"
            
            # Asegurar que el estilo se pre-añade al prompt final
            final_style = image_prompt_config.get('style', '').strip()
            if not final_style:
                final_style = "realistic, high detail" # Estilo por defecto si no se especifica
            
            scene['image_prompt'] = f"{final_style}, {generated_prompt}"
            
            # Limpiar posibles comas dobles o espacios extra
            scene['image_prompt'] = scene['image_prompt'].replace(", ,", ",").replace("  ", " ").strip()
            if scene['image_prompt'].endswith(','):
                scene['image_prompt'] = scene['image_prompt'][:-1].strip()
            logger.info(f"[Escena {i+1}] Prompt final asignado: {scene['image_prompt'][:100]}...")

            # --- DEBUG: Guardar prompt en archivo ---
            project_id = project_info.get('id', 'unknown_project')
            project_dir = Path("projects") / project_id
            debug_file_path = project_dir / "debug_prompts.txt"
            
            try:
                project_dir.mkdir(parents=True, exist_ok=True)
                with open(debug_file_path, 'a', encoding='utf-8') as f:
                    f.write(f"--- Escena {i+1} ---\n")
                    f.write(f"### System Prompt (LLM) ###\n")
                    f.write(f"""{system_prompt}\n""")
                    f.write(f"### User Prompt (LLM) ###\n")
                    f.write(f"""{user_prompt}\n""")
                    f.write(f"### Final Image Prompt ###\n")
                    f.write(f"{scene['image_prompt']}\n\n")
                logger.info(f"[Escena {i+1}] Prompts de depuración guardados en {debug_file_path}")
            except Exception as e:
                logger.error(f"[Escena {i+1}] Error al guardar prompts de depuración en debug_prompts.txt: {e}")
            # --- FIN DEBUG ---
        
        return scenes

    # --- FUNCIÓN HEREDADA PARA COMPATIBILIDAD ---
    def _generate_prompts_for_scenes(self, scenes: List[Dict], project_info: Dict, img_prompt_config: Dict, ai_service: AIServices) -> List[Dict]:
        """Función heredada para compatibilidad con código existente."""
        return self.generate_prompts_for_scenes(scenes, project_info, img_prompt_config, ai_service)

    def generate_scenes_and_prompts_from_text(self, script_content: str, project_info: Dict, image_prompt_config: Dict, ai_service: AIServices) -> List[Dict]:
        project_id_log = project_info.get('id', 'SCENE_TEXT')
        logger.info(f"[{project_id_log}] Generating scenes and prompts from TEXT...")

        # Get segmentation settings from video_gen_config -> script_segmentation or use defaults
        script_segmentation_config = self.video_gen_config.get('script_segmentation', {})
        max_chars_per_scene = script_segmentation_config.get('max_chars_per_scene', 350)
        split_on_double_newline = script_segmentation_config.get('split_on_double_newline', True)
        
        scenes_text = []
        if split_on_double_newline:
            paragraphs = [p.strip() for p in script_content.split('\n\n') if p.strip()]
            current_scene_text = ""
            for p_idx, p_text in enumerate(paragraphs):
                if not current_scene_text: # First paragraph for this scene
                    current_scene_text = p_text
                elif len(current_scene_text) + len(p_text) + 1 < max_chars_per_scene : # +1 for space
                    current_scene_text += " " + p_text
                else: # Paragraph doesn't fit, finalize current_scene_text
                    if current_scene_text: scenes_text.append(current_scene_text)
                    current_scene_text = p_text # Start new scene with current paragraph
            if current_scene_text: scenes_text.append(current_scene_text) # Add the last accumulated scene
        
        if not scenes_text: 
             scenes_text = [script_content[i:i+max_chars_per_scene] for i in range(0, len(script_content), max_chars_per_scene)]
        
        if not scenes_text and script_content: 
            scenes_text = [script_content]

        logger.info(f"[{project_id_log}] Script divided into {len(scenes_text)} text scenes.")
        
        scenes_base = []
        placeholder_duration = self.duration_per_image 
        for i, texto in enumerate(scenes_text):
             scenes_base.append({
                 'index': i,
                 'text': texto,
                 'start': i * placeholder_duration, 
                 'end': (i + 1) * placeholder_duration, 
                 'duration': placeholder_duration, 
                 'image_prompt': '' 
             })

        scenes_with_prompts = self.generate_prompts_for_scenes(scenes_base, project_info, image_prompt_config, ai_service)
        return scenes_with_prompts


    def generate_prompts_for_timed_scenes(self, transcription_segments: List[Dict], target_duration_per_scene: float, project_info: Dict, image_prompt_config: Dict, ai_service: AIServices) -> List[Dict]:
        project_id_log = project_info.get('id', 'SCENE_TIMED')
        logger.info(f"[{project_id_log}] Generating scenes and prompts from AUDIO transcription (Target duration/scene: {target_duration_per_scene:.2f}s)...")

        if not transcription_segments:
            logger.warning(f"[{project_id_log}] No transcription segments provided. Cannot generate timed scenes.")
            return []

        timed_scenes = self._segment_transcription_by_duration(transcription_segments, target_duration_per_scene)
        if not timed_scenes:
             logger.error(f"[{project_id_log}] Failed to create timed scenes from transcription.")
             return []

        scenes_with_prompts = self.generate_prompts_for_scenes(timed_scenes, project_info, image_prompt_config, ai_service)
        
        logger.info(f"[{project_id_log}] Generated {len(scenes_with_prompts)} timed scenes with prompts.")
        return scenes_with_prompts

    def save_scenes(self, scenes_data: List[Dict], output_path_str: str, project_info: Dict) -> str:
        output_path = Path(output_path_str)
        serializable_project_info = {
            k: v for k, v in project_info.items() 
            if isinstance(v, (str, int, float, bool, list, dict, type(None)))
        }
        
        total_duration_calculated = 0.0
        if scenes_data:
            last_scene = scenes_data[-1]
            if 'end' in last_scene and isinstance(last_scene['end'], (int, float)):
                total_duration_calculated = last_scene['end']
            else: # Fallback: sum durations if 'end' is not reliable on last scene
                total_duration_calculated = sum(
                    s.get('duration', 0.0) for s in scenes_data 
                    if isinstance(s.get('duration'), (int, float))
                )
        
        data_to_save = {
            'project_info_summary': { 
                'id': serializable_project_info.get('id'),
                'titulo': serializable_project_info.get('titulo'),
                'last_modified': datetime.datetime.now().isoformat()
            },
            'scenes': scenes_data,
            'generation_settings': {
                'source_type': project_info.get('scene_generation_mode', 'unknown'),
                'default_duration_per_image_setting': self.duration_per_image,
                'calculated_total_duration': total_duration_calculated
            }
        }
        
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
            logger.info(f"Scene data saved to {output_path}")
        except TypeError as e:
            logger.error(f"TypeError during JSON serialization of scene data: {e}. Data snippet: {str(data_to_save)[:500]}", exc_info=True)
            try:
                simplified_data = {'scenes_count': len(scenes_data), 'error_type': type(e).__name__, 'error_message': str(e)}
                simplified_path = output_path.with_name(output_path.stem + "_serialization_error.json")
                with open(simplified_path, 'w', encoding='utf-8') as f_err:
                    json.dump(simplified_data, f_err, ensure_ascii=False, indent=2)
                logger.warning(f"Saved simplified error report for scene data to {simplified_path}")
            except Exception as e2:
                logger.error(f"Failed to save even a simplified error report for scene data: {e2}", exc_info=True)
        except Exception as e:
            logger.error(f"Unexpected error saving scene data to {output_path}: {e}", exc_info=True)
        
        return str(output_path)

    def _detect_historical_context_from_title(self, titulo: str) -> Dict[str, str]:
        """
        Detecta automáticamente el contexto histórico basado en el título del proyecto.
        Retorna las variables históricas apropiadas.
        """
        titulo_lower = titulo.lower().strip()
        
        # DEBUG: Mostrar proceso de detección
        logger.info(f"🔍 DEBUG - Detectando contexto histórico para: '{titulo}'")
        logger.info(f"🔍 DEBUG - Título normalizado: '{titulo_lower}'")
        
        # Base de datos de contextos históricos conocidos
        historical_contexts = {
            "san blas": {
                "periodo_historico": "Siglo IV d.C. (circa 280-316 d.C.), Imperio Romano tardío, era de las persecuciones cristianas bajo Diocleciano",
                "ubicacion": "Sebastea, Armenia histórica (actual Sivas, Turquía), región montañosa del Asia Menor bajo dominio romano",
                "contexto_cultural": "Cristianismo primitivo bajo persecución sistemática del emperador Diocleciano, comunidades cristianas clandestinas, tradición médica greco-romana, conflicto entre paganismo y cristianismo emergente"
            },
            "san blás": {
                "periodo_historico": "Siglo IV d.C. (circa 280-316 d.C.), Imperio Romano tardío, era de las persecuciones cristianas bajo Diocleciano",
                "ubicacion": "Sebastea, Armenia histórica (actual Sivas, Turquía), región montañosa del Asia Menor bajo dominio romano",
                "contexto_cultural": "Cristianismo primitivo bajo persecución sistemática del emperador Diocleciano, comunidades cristianas clandestinas, tradición médica greco-romana, conflicto entre paganismo y cristianismo emergente"
            },
            "napoleon": {
                "periodo_historico": "1796-1815, Era Napoleónica, Imperio Francés, Consulado y Primer Imperio",
                "ubicacion": "Europa occidental y central, principalmente Francia, Austria, Prusia, Rusia, península ibérica",
                "contexto_cultural": "Post-Revolución Francesa, nacionalismo europeo emergente, códigos napoleónicos, Ilustración tardía, guerras de coalición"
            },
            "maya": {
                "periodo_historico": "800-900 d.C., Período Clásico Tardío Maya, colapso de las ciudades-estado",
                "ubicacion": "Tierras bajas mayas: Petén guatemalteco, Yucatán, Belice, Chiapas, Honduras occidental",
                "contexto_cultural": "Civilización maya clásica, sistema de ciudades-estado, escritura jeroglífica, astronomía avanzada, religión politeísta, colapso ambiental"
            }
        }
        
        logger.info(f"🔍 DEBUG - Contextos históricos disponibles: {list(historical_contexts.keys())}")
        
        # Buscar coincidencias en el título
        for key, context in historical_contexts.items():
            logger.info(f"🔍 DEBUG - Probando match con '{key}'")
            if key in titulo_lower:
                logger.info(f"✅ MATCH ENCONTRADO - Contexto histórico detectado para '{titulo}': '{key}'")
                logger.info(f"✅ CONTEXTO APLICADO:")
                logger.info(f"  • periodo_historico: {context['periodo_historico']}")
                logger.info(f"  • ubicacion: {context['ubicacion']}")
                logger.info(f"  • contexto_cultural: {context['contexto_cultural']}")
                return context
            else:
                logger.debug(f"🔍 DEBUG - '{key}' no encontrado en '{titulo_lower}'")
        
        # Si no encuentra coincidencia, retornar contexto genérico
        logger.warning(f"❌ NO MATCH - No se detectó contexto histórico específico para '{titulo}'. Usando contexto genérico.")
        fallback_context = {
            "periodo_historico": "Período histórico a determinar según el contenido",
            "ubicacion": "Ubicación geográfica a determinar según el contexto",
            "contexto_cultural": "Contexto cultural a determinar según la época y región"
        }
        logger.warning(f"⚠️ CONTEXTO GENÉRICO APLICADO: {fallback_context}")
        return fallback_context

    def _should_use_historical_prompt(self, titulo: str) -> bool:
        """
        Determina si un proyecto debería usar automáticamente el prompt histórico
        basado en su título.
        """
        titulo_lower = titulo.lower().strip()
        
        # DEBUG: Mostrar título analizado
        logger.info(f"🔍 DEBUG - Analizando título para detección histórica: '{titulo}'")
        logger.info(f"🔍 DEBUG - Título normalizado: '{titulo_lower}'")
        
        # Palabras clave que indican contenido histórico/biográfico
        historical_keywords = [
            "san ", "santa ", "santo ",  # Santos
            "napoleon", "alejandro", "cesar", "cleopatra",  # Figuras históricas
            "maya", "azteca", "inca", "romano", "griego",  # Civilizaciones
            "medieval", "renacimiento", "barroco",  # Períodos
            "vida de", "biografía", "historia de"  # Indicadores biográficos
        ]
        
        logger.info(f"🔍 DEBUG - Keywords históricos a buscar: {historical_keywords}")
        
        for keyword in historical_keywords:
            if keyword in titulo_lower:
                logger.info(f"✅ MATCH ENCONTRADO - Título '{titulo}' requiere prompt histórico (keyword: '{keyword}')")
                return True
            else:
                logger.debug(f"🔍 DEBUG - Keyword '{keyword}' no encontrado en título")
        
        logger.info(f"❌ NO MATCH - Título '{titulo}' NO requiere prompt histórico automático")
        return False

    def _force_historical_prompt_if_needed(self, project_info: Dict, image_prompt_config: Dict) -> Dict:
        """
        Fuerza el uso del prompt histórico si el proyecto lo requiere,
        incluso si no fue seleccionado manualmente.
        """
        titulo = project_info.get("titulo", "")
        
        if not self._should_use_historical_prompt(titulo):
            return image_prompt_config
        
        # Verificar si ya está usando el prompt histórico
        current_prompt = image_prompt_config.get("prompt_obj", {})
        if current_prompt and current_prompt.get("nombre") == "Escenas Fotorrealistas Históricamente Precisas":
            logger.info(f"🏛️ Proyecto '{titulo}' ya usa prompt histórico correcto")
            
            # 🔧 IMPORTANTE: Incluso si ya usa el prompt histórico, verificar que tenga variables históricas
            if not image_prompt_config.get("historical_variables"):
                logger.info(f"🏛️ Prompt histórico detectado pero sin variables históricas. Aplicando detección automática...")
                historical_context = self._detect_historical_context_from_title(titulo)
                new_config = image_prompt_config.copy()
                new_config["historical_variables"] = historical_context
                return new_config
            
            return image_prompt_config
        
        # Cargar el prompt histórico desde el archivo
        try:
            import json
            
            prompts_file = Path(__file__).parent.parent / "prompts" / "imagenes_prompts.json"
            with open(prompts_file, 'r', encoding='utf-8') as f:
                all_prompts = json.load(f)
            
            # Buscar el prompt histórico
            historical_prompt = None
            for prompt in all_prompts:
                if prompt.get("nombre") == "Escenas Fotorrealistas Históricamente Precisas":
                    historical_prompt = prompt
                    break
            
            if not historical_prompt:
                logger.error("🚨 No se encontró el prompt histórico en imagenes_prompts.json")
                return image_prompt_config
            
            # Detectar contexto histórico automáticamente
            historical_context = self._detect_historical_context_from_title(titulo)
            
            # Crear nueva configuración con prompt histórico COMPLETO
            new_config = image_prompt_config.copy()
            new_config["prompt_obj"] = historical_prompt  # Configuración completa del archivo JSON
            new_config["historical_variables"] = historical_context
            
            logger.info(f"🏛️ FORZANDO prompt histórico para '{titulo}'")
            logger.info(f"🏛️ Prompt completo cargado: {historical_prompt.get('nombre')}")
            logger.info(f"🏛️ Variables requeridas: {historical_prompt.get('variables', [])}")
            logger.info(f"🏛️ Contexto aplicado: {historical_context}")
            
            return new_config
            
        except Exception as e:
            logger.error(f"❌ Error forzando prompt histórico: {e}")
            return image_prompt_config

    def _generate_character_dossier(self, project_info: Dict, ai_service: AIServices) -> Optional[str]:
        """
        Genera un dossier completo del personaje principal del proyecto.
        
        Args:
            project_info: Información del proyecto con titulo y contexto
            ai_service: Servicio de IA para generación de contenido
            
        Returns:
            str: Dossier completo del personaje con secciones por edad, o None si falla
        """
        logger.info("🎭 GENERANDO DOSSIER DE PERSONAJE PRINCIPAL")
        logger.info("=" * 60)
        
        # Verificar que tenemos la información básica necesaria
        titulo = project_info.get("titulo", "")
        contexto = project_info.get("contexto", "")
        
        if not titulo or not contexto:
            logger.warning(f"⚠️ Información insuficiente para generar dossier")
            logger.warning(f"  • Título: {'✓' if titulo else '✗'} ({titulo})")
            logger.warning(f"  • Contexto: {'✓' if contexto else '✗'} ({len(contexto)} chars)")
            return None
        
        # Cargar la plantilla de dossier
        try:
            import json
            prompts_file = Path(__file__).parent.parent / "prompts" / "imagenes_prompts.json"
            
            with open(prompts_file, 'r', encoding='utf-8') as f:
                all_prompts = json.load(f)
            
            # Buscar la plantilla de dossier
            dossier_template = None
            for prompt in all_prompts:
                if prompt.get("nombre") == "Dossier de Personaje Principal":
                    dossier_template = prompt
                    break
            
            if not dossier_template:
                logger.error("❌ No se encontró la plantilla 'Dossier de Personaje Principal'")
                return None
                
            logger.info(f"✅ Plantilla de dossier cargada exitosamente")
            
        except Exception as e:
            logger.error(f"❌ Error cargando plantilla de dossier: {e}")
            return None
        
        # Preparar variables para la plantilla
        template_variables = {
            'titulo': titulo,
            'contexto': contexto
        }
        
        # Formatear prompts con las variables
        system_prompt = dossier_template.get("system_prompt", "")
        user_prompt_template = dossier_template.get("user_prompt", "")
        
        try:
            user_prompt = user_prompt_template.format(**template_variables)
        except KeyError as e:
            logger.error(f"❌ Variable faltante en plantilla de dossier: {e}")
            return None
        
        # Configuración para generación
        provider_priority = ['gemini', 'openai', 'ollama']  # Priorizar Gemini para mejor calidad
        
        logger.info(f"🤖 GENERANDO DOSSIER:")
        logger.info(f"  • Proyecto: {titulo}")
        logger.info(f"  • Proveedores: {provider_priority}")
        logger.info(f"  • Contexto: {len(contexto)} caracteres")
        
        # DEBUG: Mostrar prompts que se enviarán
        logger.info(f"🔍 SYSTEM PROMPT PARA DOSSIER:")
        logger.info(f"{'-' * 40}")
        logger.info(f"{system_prompt}")
        logger.info(f"{'-' * 40}")
        
        logger.info(f"🔍 USER PROMPT PARA DOSSIER:")
        logger.info(f"{'-' * 40}")
        logger.info(f"{user_prompt}")
        logger.info(f"{'-' * 40}")
        
        # Intentar generar dossier con cada proveedor
        for provider in provider_priority:
            try:
                logger.info(f"🤖 Intentando generar dossier con {provider.upper()}...")
                
                # Usar modelo específico según proveedor
                model_map = {
                    'gemini': 'models/gemini-2.5-flash-lite-preview-06-17',
                    'openai': 'gpt-3.5-turbo',
                    'ollama': 'llama3.2'
                }
                model = model_map.get(provider, 'default')
                
                # Generar dossier
                dossier_content = ai_service.generate_content(
                    provider=provider,
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt
                )
                
                if dossier_content and len(str(dossier_content).strip()) > 100:
                    logger.info(f"✅ DOSSIER GENERADO EXITOSAMENTE con {provider.upper()}")
                    logger.info(f"📊 Longitud del dossier: {len(str(dossier_content))} caracteres")
                    
                    # DEBUG: Mostrar preview del dossier
                    dossier_str = str(dossier_content)
                    preview_lines = dossier_str.split('\n')[:10]  # Primeras 10 líneas
                    logger.info(f"🔍 PREVIEW DEL DOSSIER GENERADO:")
                    logger.info(f"{'=' * 50}")
                    for i, line in enumerate(preview_lines, 1):
                        logger.info(f"{i:2d}: {line}")
                    if len(dossier_str.split('\n')) > 10:
                        logger.info(f"... (y {len(dossier_str.split('\n')) - 10} líneas más)")
                    logger.info(f"{'=' * 50}")
                    
                    return dossier_str
                else:
                    logger.warning(f"⚠️ Dossier vacío o muy corto desde {provider}")
                    
            except Exception as e:
                logger.error(f"❌ Error generando dossier con {provider}: {e}")
                continue
        
        # Si llegamos aquí, todos los proveedores fallaron
        logger.error(f"❌ FALLÓ LA GENERACIÓN DE DOSSIER con todos los proveedores")
        logger.error(f"❌ Proveedores intentados: {provider_priority}")
        return None

    def _detect_character_age_stage(self, scene_text: str, project_context: str = "") -> str:
        """
        Detecta la etapa de edad del personaje principal en una escena específica.
        
        Args:
            scene_text: Texto de la escena a analizar
            project_context: Contexto adicional del proyecto
            
        Returns:
            str: Etapa de edad detectada ('infancia', 'juventud', 'adultez', 'madurez')
        """
        logger.info(f"🔍 DETECTANDO EDAD DEL PERSONAJE EN ESCENA")
        logger.info(f"📝 Texto de escena: {scene_text[:100]}...")
        
        # Normalizar texto para análisis
        text_lower = scene_text.lower().strip()
        
        # Palabras clave por etapa de vida
        age_keywords = {
            'infancia': [
                'niño', 'niña', 'infancia', 'pequeño', 'pequeña', 'hijo', 'hija',
                'crianza', 'padres', 'familia', 'hogar paterno', 'juventud temprana',
                'nacimiento', 'nacer', 'nació', 'crecer', 'criado', 'crianza',
                'años de niñez', 'desde pequeño', 'siendo niño', 'cuando era niño'
            ],
            'juventud': [
                'joven', 'juventud', 'adolescente', 'estudios', 'aprendizaje', 
                'formación', 'educación', 'maestro', 'discípulo', 'estudiante',
                'vocación', 'llamado', 'ordenación', 'seminarista', 'noviciado',
                'años de juventud', 'siendo joven', 'en su juventud', 'años mozos'
            ],
            'adultez': [
                'adulto', 'maduro', 'obispo', 'sacerdote', 'ministerio', 'pastoral',
                'comunidad', 'liderazgo', 'responsabilidad', 'cargo', 'posición',
                'médico', 'sanador', 'milagros', 'curaciones', 'servicio',
                'años de ministerio', 'siendo obispo', 'como líder', 'en la madurez'
            ],
            'madurez': [
                'anciano', 'mayor', 'vejez', 'sabiduría', 'experiencia', 'veterano',
                'persecución', 'martirio', 'sufrimiento', 'tortura', 'final',
                'últimos años', 'muerte', 'morir', 'murió', 'falleció',
                'al final de su vida', 'en sus últimos días', 'anciano venerable'
            ]
        }
        
        # Contadores de coincidencias por etapa
        age_scores = {stage: 0 for stage in age_keywords.keys()}
        
        # Buscar palabras clave y acumular puntuaciones
        for stage, keywords in age_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    age_scores[stage] += 1
                    logger.debug(f"🔍 Keyword '{keyword}' encontrada para etapa '{stage}'")
        
        # Análisis de contexto numérico (años, edades específicas)
        import re
        
        # Buscar referencias a edades específicas
        age_patterns = [
            r'(\d+)\s*años?',
            r'edad\s*de\s*(\d+)',
            r'(\d+)\s*años?\s*de\s*edad',
            r'a\s*los\s*(\d+)',
            r'cuando\s*tenía\s*(\d+)'
        ]
        
        found_ages = []
        for pattern in age_patterns:
            matches = re.findall(pattern, text_lower)
            found_ages.extend([int(age) for age in matches if age.isdigit()])
        
        # Si encontramos edades específicas, ajustar puntuaciones
        if found_ages:
            for age in found_ages:
                logger.info(f"🔢 Edad específica detectada: {age} años")
                if 0 <= age <= 12:
                    age_scores['infancia'] += 3
                elif 13 <= age <= 25:
                    age_scores['juventud'] += 3
                elif 26 <= age <= 50:
                    age_scores['adultez'] += 3
                elif age > 50:
                    age_scores['madurez'] += 3
        
        # Determinar etapa con mayor puntuación
        detected_stage = max(age_scores, key=age_scores.get)
        max_score = age_scores[detected_stage]
        
        # Si no hay puntuación clara, usar lógica de fallback
        if max_score == 0:
            logger.warning(f"⚠️ No se detectaron indicadores de edad claros")
            
            # Fallback basado en contexto general
            if any(word in text_lower for word in ['obispo', 'ministerio', 'liderazgo']):
                detected_stage = 'adultez'
            elif any(word in text_lower for word in ['persecución', 'martirio', 'muerte']):
                detected_stage = 'madurez'
            elif any(word in text_lower for word in ['estudios', 'formación', 'vocación']):
                detected_stage = 'juventud'
            else:
                detected_stage = 'adultez'  # Default para contextos neutrales
            
            logger.info(f"🔄 Usando fallback: '{detected_stage}' basado en contexto")
        
        logger.info(f"🎯 RESULTADO DETECCIÓN DE EDAD:")
        logger.info(f"  • Etapa detectada: {detected_stage.upper()}")
        logger.info(f"  • Puntuaciones: {age_scores}")
        logger.info(f"  • Edades específicas: {found_ages}")
        
        return detected_stage

    def _extract_character_description_from_dossier(self, dossier: str, age_stage: str) -> str:
        """
        Extrae la descripción específica del personaje para una etapa de edad del dossier.
        
        Args:
            dossier: Dossier completo del personaje
            age_stage: Etapa de edad ('infancia', 'juventud', 'adultez', 'madurez')
            
        Returns:
            str: Descripción específica para la etapa, o descripción genérica si no se encuentra
        """
        logger.info(f"📋 EXTRAYENDO DESCRIPCIÓN PARA ETAPA: {age_stage.upper()}")
        
        if not dossier or not age_stage:
            logger.warning("⚠️ Dossier o etapa de edad vacíos")
            return ""
        
        # Mapeo de etapas a patrones de búsqueda en el dossier
        stage_patterns = {
            'infancia': [r'\*\*INFANCIA.*?\*\*.*?(?=\*\*[A-Z]|\Z)', r'INFANCIA.*?(?=\*\*[A-Z]|\Z)'],
            'juventud': [r'\*\*JUVENTUD.*?\*\*.*?(?=\*\*[A-Z]|\Z)', r'JUVENTUD.*?(?=\*\*[A-Z]|\Z)'],
            'adultez': [r'\*\*ADULTEZ.*?\*\*.*?(?=\*\*[A-Z]|\Z)', r'ADULTEZ.*?(?=\*\*[A-Z]|\Z)'],
            'madurez': [r'\*\*MADUREZ.*?\*\*.*?(?=\*\*[A-Z]|\Z)', r'MADUREZ.*?(?=\*\*[A-Z]|\Z)', 
                       r'\*\*VEJEZ.*?\*\*.*?(?=\*\*[A-Z]|\Z)', r'VEJEZ.*?(?=\*\*[A-Z]|\Z)']
        }
        
        import re
        
        # Buscar la sección correspondiente
        patterns = stage_patterns.get(age_stage, [])
        
        for pattern in patterns:
            matches = re.findall(pattern, dossier, re.DOTALL | re.IGNORECASE)
            if matches:
                description = matches[0].strip()
                
                # Limpiar la descripción
                description = re.sub(r'\*\*[^*]+\*\*', '', description)  # Remover encabezados
                description = re.sub(r'\s+', ' ', description).strip()   # Normalizar espacios
                
                # Filtrar líneas vacías y bullets
                lines = [line.strip() for line in description.split('\n') if line.strip()]
                clean_lines = []
                
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('*') and len(line) > 10:
                        # Remover bullets y limpiar
                        line = re.sub(r'^\*\s*', '', line)
                        line = re.sub(r'^\*\*.*?\*\*\s*', '', line)
                        if line:
                            clean_lines.append(line)
                
                final_description = ' '.join(clean_lines)
                
                if final_description and len(final_description) > 50:
                    logger.info(f"✅ Descripción extraída para '{age_stage}':")
                    logger.info(f"  • Longitud: {len(final_description)} caracteres")
                    logger.info(f"  • Preview: {final_description[:150]}...")
                    return final_description
        
        # Si no se encuentra la sección específica, crear descripción genérica
        logger.warning(f"⚠️ No se encontró sección específica para '{age_stage}' en el dossier")
        
        # Extraer información general del dossier para crear descripción genérica
        generic_description = self._create_generic_description_from_dossier(dossier, age_stage)
        
        logger.info(f"🔄 Usando descripción genérica para '{age_stage}':")
        logger.info(f"  • Longitud: {len(generic_description)} caracteres")
        logger.info(f"  • Preview: {generic_description[:150]}...")
        
        return generic_description

    def _create_generic_description_from_dossier(self, dossier: str, age_stage: str) -> str:
        """
        Crea una descripción genérica basada en el contenido general del dossier.
        """
        # Extraer características físicas generales
        physical_keywords = ['cabello', 'ojos', 'complexión', 'estatura', 'rostro', 'facciones']
        clothing_keywords = ['túnica', 'vestimenta', 'manto', 'sandalias']
        
        physical_traits = []
        clothing_traits = []
        
        dossier_lower = dossier.lower()
        
        for keyword in physical_keywords:
            if keyword in dossier_lower:
                # Buscar contexto alrededor de la palabra clave
                import re
                pattern = rf'.{{0,50}}{keyword}.{{0,50}}'
                matches = re.findall(pattern, dossier_lower)
                if matches:
                    physical_traits.extend(matches)
        
        for keyword in clothing_keywords:
            if keyword in dossier_lower:
                pattern = rf'.{{0,50}}{keyword}.{{0,50}}'
                matches = re.findall(pattern, dossier_lower)
                if matches:
                    clothing_traits.extend(matches)
        
        # Construir descripción genérica
        base_description = f"Personaje en etapa de {age_stage}"
        
        if physical_traits:
            base_description += f", con {', '.join(physical_traits[:2])}"
        
        if clothing_traits:
            base_description += f", vistiendo {', '.join(clothing_traits[:2])}"
        
        return base_description

    def _should_use_character_dossier(self, project_info: Dict) -> bool:
        """
        Determina si un proyecto debería usar el sistema de dossier de personaje
        para mantener coherencia visual.
        
        Args:
            project_info: Información del proyecto
            
        Returns:
            bool: True si debe usar dossier, False caso contrario
        """
        titulo = project_info.get("titulo", "").lower().strip()
        contexto = project_info.get("contexto", "").lower().strip()
        
        # Palabras clave que indican contenido biográfico/histórico con personaje principal
        biographical_keywords = [
            "vida de", "biografía", "historia de", "san ", "santa ", "santo ",
            "napoleon", "alejandro", "cesar", "cleopatra", "martin luther",
            "teresa", "ignacio", "francisco", "juan", "maría", "josé",
            "mártir", "santo", "beato", "venerable"
        ]
        
        historical_keywords = [
            "histórico", "historia", "biografía", "documental biográfico",
            "personaje histórico", "figura histórica"
        ]
        
        # Verificar si el título o contexto sugieren contenido biográfico
        for keyword in biographical_keywords + historical_keywords:
            if keyword in titulo or keyword in contexto:
                logger.info(f"🎭 Dossier requerido - Keyword detectada: '{keyword}'")
                return True
        
        # Verificar si ya usa prompt histórico (muy probable que necesite dossier)
        if self._should_use_historical_prompt(titulo):
            logger.info("🎭 Dossier requerido - Proyecto usa prompt histórico")
            return True
        
        logger.info("🎭 Dossier NO requerido - Proyecto no parece biográfico/histórico")
        return False

    def _fix_encoding_in_segments(self, transcription_segments):
        """
        Corrige problemas de codificación de caracteres en todos los segmentos.
        """
        
        logger.info("🔤 Corrigiendo codificación de caracteres...")
        
        # Mapa de correcciones de codificación
        encoding_fixes = {
            '√°': 'á', '√©': 'é', '√≠': 'í', '√≥': 'ó', '√∫': 'ú', '√±': 'ñ',
            '√Å': 'Á', '√É': 'É', '√Í': 'Í', '√ì': 'Ó', '√ö': 'Ú', '√Ñ': 'Ñ'
        }
        
        fixed_segments = []
        fixes_applied = 0
        
        for segment in transcription_segments:
            fixed_segment = segment.copy()
            original_text = segment.get('text', '')
            fixed_text = original_text
            
            # Aplicar correcciones
            for wrong_char, correct_char in encoding_fixes.items():
                if wrong_char in fixed_text:
                    fixed_text = fixed_text.replace(wrong_char, correct_char)
                    fixes_applied += 1
            
            if fixed_text != original_text:
                fixed_segment['text'] = fixed_text
            
            fixed_segments.append(fixed_segment)
        
        if fixes_applied > 0:
            logger.info(f"✅ {fixes_applied} correcciones de codificación aplicadas")
        
        return fixed_segments

    def _fix_encoding_in_segments(self, transcription_segments):
        """
        Corrige problemas de codificación de caracteres en todos los segmentos.
        """
        
        logger.info("🔤 Corrigiendo codificación de caracteres...")
        
        # Mapa de correcciones de codificación
        encoding_fixes = {
            "√°": "á", "√©": "é", "√≠": "í", "√≥": "ó", "√∫": "ú", "√±": "ñ",
            "√Å": "Á", "√É": "É", "√Í": "Í", "√ì": "Ó", "√ö": "Ú", "√Ñ": "Ñ"
        }
        
        fixed_segments = []
        fixes_applied = 0
        
        for segment in transcription_segments:
            fixed_segment = segment.copy()
            original_text = segment.get("text", "")
            fixed_text = original_text
            
            # Aplicar correcciones
            for wrong_char, correct_char in encoding_fixes.items():
                if wrong_char in fixed_text:
                    fixed_text = fixed_text.replace(wrong_char, correct_char)
                    fixes_applied += 1
            
            if fixed_text != original_text:
                fixed_segment["text"] = fixed_text
            
            fixed_segments.append(fixed_segment)
        
        if fixes_applied > 0:
            logger.info(f"✅ {fixes_applied} correcciones de codificación aplicadas")
        
        return fixed_segments

    def _has_complete_context(self, text: str) -> bool:
        """
        Verifica si un texto tiene contexto narrativo completo.
        Evita escenas fragmentadas como "para siempre." o "pero su apariencia lo decía todo."
        """
        
        text_stripped = text.strip()
        
        if len(text_stripped) < 10:  # Muy corto
            return False
        
        # Verificar que no termine abruptamente
        abrupt_endings = [
            r'\bpero\s*\.?\s*$',           # Termina en "pero"
            r'\by\s*\.?\s*$',              # Termina en "y"  
            r'\bque\s*\.?\s*$',            # Termina en "que"
            r'\bde\s*\.?\s*$',             # Termina en "de"
            r'\bla\s*\.?\s*$',             # Termina en "la"
            r'\bel\s*\.?\s*$',             # Termina en "el"
            r'\bun\s*\.?\s*$',             # Termina en "un"
            r'\buna\s*\.?\s*$',            # Termina en "una"
            r'\bsu\s*\.?\s*$',             # Termina en "su"
        ]
        
        import re
        for pattern in abrupt_endings:
            if re.search(pattern, text_stripped.lower()):
                return False
        
        # Verificar que tenga al menos un verbo (acción)
        verbs = [
            'fue', 'era', 'está', 'estaba', 'tiene', 'tenía', 'hace', 'hacía',
            'dijo', 'dice', 'habló', 'habla', 'vivió', 'vive', 'murió', 'muere',
            'nació', 'nace', 'creó', 'crea', 'escribió', 'escribe', 'pintó', 'pinta'
        ]
        
        text_lower = text_stripped.lower()
        has_verb = any(verb in text_lower for verb in verbs)
        
        # Verificar que tenga sustantivo (sujeto/objeto)
        nouns = [
            'hombre', 'mujer', 'persona', 'vida', 'historia', 'obra', 'tiempo',
            'lugar', 'ciudad', 'casa', 'iglesia', 'rey', 'reina', 'santo', 'santa'
        ]
        
        has_noun = any(noun in text_lower for noun in nouns)
        
        # Contexto completo = tiene verbo Y sustantivo Y no termina abruptamente
        return has_verb and has_noun
    
    def _improves_context(self, current_text: str, combined_text: str) -> bool:
        """
        Verifica si combinar textos mejora el contexto narrativo.
        """
        
        # Si el texto actual ya tiene contexto completo, no combinar
        if self._has_complete_context(current_text):
            return False
        
        # Si la combinación crea contexto completo, combinar
        if self._has_complete_context(combined_text):
            return True
        
        # Si ninguno tiene contexto completo, combinar si no es demasiado largo
        if len(combined_text) < 200:  # Límite razonable
            return True
        
        return False
