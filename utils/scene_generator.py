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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- NUEVA CONSTANTE ---
# Si una escena dura más que esto (en segundos), se subdividirá para mantener el dinamismo.
MAX_SCENE_DURATION = 15.0

class SceneGenerator:
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._load_void_config()
        self.video_gen_config = self.config.get('video_generation', {})
        # AIServices ahora se pasará como argumento donde se necesite
        # para evitar inicializarlo si no se usa.
        # self.ai_service = AIServices() 
        self.duration_per_image = self.video_gen_config.get('timing', {}).get('default_duration_per_image', 10.0)
        logger.info(f"SceneGenerator inicializado con duración/imagen base: {self.duration_per_image:.2f}s")

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
                
                timed_scenes.append({
                    'index': scene_idx,
                    'text': scene_text_final.strip(),
                    'start': current_scene_start_time,
                    'end': scene_end_time,
                    'duration': current_scene_accumulated_duration
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

    def _align_paragraphs_to_transcription(self, paragraphs: List[str], transcription_segments: List[Dict]) -> List[Dict]:
        """Alinea los párrafos del guión con los timestamps de la transcripción."""
        scenes = []
        full_transcript_text = " ".join([seg['text'].strip() for seg in transcription_segments])
        last_found_pos = 0

        for i, paragraph in enumerate(paragraphs):
            # Buscar el inicio del párrafo en la transcripción
            # Usamos las primeras ~10 palabras para una búsqueda más fiable
            search_text = " ".join(paragraph.split()[:10])
            start_char_pos = full_transcript_text.find(search_text, last_found_pos)

            if start_char_pos == -1:
                logger.warning(f"No se pudo alinear el párrafo {i + 1}. Omitiendo.")
                continue

            end_char_pos = start_char_pos + len(paragraph)
            last_found_pos = end_char_pos # Actualizar para la siguiente búsqueda

            # Encontrar los tiempos de inicio y fin para este rango de caracteres
            scene_start_time, scene_end_time = -1, -1
            current_char_count = 0
            for seg in transcription_segments:
                seg_len = len(seg['text'].strip()) + 1
                if current_char_count >= start_char_pos and scene_start_time == -1:
                    scene_start_time = seg['start']
                if current_char_count >= end_char_pos and scene_start_time != -1:
                    scene_end_time = seg['end']
                    break
                current_char_count += seg_len
            
            # Si el bucle termina, el tiempo final es el del último segmento
            if scene_end_time == -1 and scene_start_time != -1:
                scene_end_time = transcription_segments[-1]['end']

            if scene_start_time != -1 and scene_end_time > scene_start_time:
                scenes.append({
                    "index": len(scenes),
                    "text": paragraph,
                    "start": scene_start_time,
                    "end": scene_end_time,
                    "duration": scene_end_time - scene_start_time
                })
        return scenes
    
    def generate_scenes_from_script(self, script_content: str, transcription_segments: List[Dict], mode: str) -> List[Dict]:
        """Genera escenas con el nuevo modo híbrido por párrafos."""
        logger.info(f"Generando escenas con modo: '{mode}'...")
        
        if mode == "Por Párrafos (Híbrido)":
            # --- LÓGICA POR PÁRRAFOS (HÍBRIDA) ---
            paragraphs = self._segment_script_by_paragraphs(script_content)
            timed_scenes = self._align_paragraphs_to_transcription(paragraphs, transcription_segments)
            
            final_scenes = []
            for scene in timed_scenes:
                if scene['duration'] > MAX_SCENE_DURATION:
                    logger.info(f"Escena {scene['index']} es muy larga ({scene['duration']:.1f}s > {MAX_SCENE_DURATION}s). Subdividiendo.")
                    num_sub_scenes = round(scene['duration'] / (MAX_SCENE_DURATION - 5)) # Apuntar a escenas de ~20s
                    if num_sub_scenes < 2: num_sub_scenes = 2
                    
                    sub_scene_duration = scene['duration'] / num_sub_scenes
                    
                    for j in range(num_sub_scenes):
                        sub_start_time = scene['start'] + (j * sub_scene_duration)
                        sub_end_time = sub_start_time + sub_scene_duration
                        
                        sub_text_parts = []
                        for seg in transcription_segments:
                            if seg['start'] >= sub_start_time and seg['end'] <= sub_end_time:
                                sub_text_parts.append(seg['text'].strip())
                        
                        if not sub_text_parts: continue
                        
                        final_scenes.append({
                            "index": len(final_scenes),
                            "text": " ".join(sub_text_parts),
                            "start": sub_start_time,
                            "end": sub_end_time,
                            "duration": sub_end_time - sub_start_time
                        })
                else:
                    final_scenes.append(scene)
            
            logger.info(f"Segmentación por párrafos resultó en {len(final_scenes)} escenas finales.")
            return final_scenes
        
        else:
            # Fallback a métodos anteriores
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
        prompt_obj = image_prompt_config.get('prompt_obj')
        provider_priority_list = image_prompt_config.get('img_prompt_providers_priority', ['gemini'])
        
        if not prompt_obj:
            logger.warning("No se proporcionó plantilla de prompt. Usando fallback simple.")
            for scene in scenes:
                scene['image_prompt'] = f"Photorealistic, cinematic: {scene.get('text', '')[:350]}"
            return scenes

        system_prompt = prompt_obj.get("system_prompt", "")
        user_prompt_template = prompt_obj.get("user_prompt", "Generate an image for: {scene_text}")

        for i, scene in enumerate(scenes):
            user_prompt = user_prompt_template.format(
                scene_text=scene['text'], 
                titulo=project_info.get("titulo", ""), 
                contexto=project_info.get("contexto", "")
            )
            
            generated_prompt = None
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
                    
                    generated_text = ai_service.generate_content(
                        provider=provider, 
                        model=model, 
                        system_prompt=system_prompt, 
                        user_prompt=user_prompt
                    )
                    
                    if generated_text and "[ERROR]" not in generated_text:
                        logger.info(f"[Escena {i+1}] ✅ Éxito con {provider.upper()}.")
                        generated_prompt = generated_text.strip()
                        break
                    else:
                        logger.warning(f"[Escena {i+1}] ⚠️ Fallo leve con {provider.upper()}. Intentando siguiente proveedor.")
                except Exception as e:
                    logger.error(f"[Escena {i+1}] ❌ Fallo grave con {provider.upper()}: {e}. Intentando siguiente proveedor.")
            
            if not generated_prompt:
                logger.error(f"[Escena {i+1}] 🚨 Todos los proveedores fallaron. Usando prompt de emergencia.")
                scene['image_prompt'] = f"Photorealistic, cinematic, high detail: {scene['text'][:350]}"
            else:
                scene['image_prompt'] = generated_prompt
        
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
