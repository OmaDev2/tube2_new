# utils/video_processing.py
import os
import tempfile
from moviepy.editor import (
    VideoFileClip, ImageClip, CompositeVideoClip,
    concatenate_videoclips, AudioFileClip, CompositeAudioClip,
    concatenate_audioclips
)
from moviepy.video.fx.all import loop
import numpy as np
import subprocess
from pathlib import Path
import random
import string
import shutil
import uuid
import logging
from datetime import datetime
import yaml
import json
from typing import Dict, List, Optional

# --- AÑADIR PROJECT_ROOT ---
# Definir la ruta raíz del proyecto para construir rutas absolutas y robustas
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# --------------------

# --- Importaciones Directas de Servicios ---
try:
    from utils.ai_services import AIServices
    from utils.audio_services import AudioServices
    from utils.scene_generator import SceneGenerator
    from utils.video_services import VideoServices
    from utils.subtitle_utils import split_subtitle_segments
    from utils.transcription_services import TranscriptionService, get_transcription_service
    from utils.content_optimizer import ContentOptimizer
except ImportError as e:
    logging.critical(f"FALLO CRÍTICO AL IMPORTAR SERVICIOS: {e}. La aplicación no puede continuar.", exc_info=True)
    raise RuntimeError(f"Error importando módulo necesario: {e}") from e
# --- Fin Importaciones ---

# Configuración logging
logger = logging.getLogger(__name__)

class VideoProcessor:
    def __init__(self, config: Optional[Dict] = None):
        """Inicializa el procesador de video con configuración opcional."""
        self.void_config = config or self._load_void_config()
        self.tts_config = self._load_tts_config()
        self.transcription_config = self._load_transcription_config()
        self.overlay_config = self._load_overlay_config()
        self.video_gen_config = self.void_config.get('video_generation', {})
        
        # Configurar directorios
        self.projects_path = Path(self.video_gen_config.get('paths', {}).get('projects_dir', 'projects'))
        self.output_dir = Path(self.video_gen_config.get('paths', {}).get('output_dir', 'output'))
        self.background_music_path = Path(self.video_gen_config.get('paths', {}).get('background_music_dir', 'background_music'))
        
        self._setup_directories()
        self._initialize_services()
    
    def _load_void_config(self) -> Dict:
        try:
            root_dir = Path(__file__).resolve().parent.parent 
            voidrules_path = root_dir / ".voidrules"
            with open(voidrules_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.info(f"Configuración cargada desde {voidrules_path}")
                return config
        except FileNotFoundError:
            logger.warning(".voidrules no encontrado, usando defaults.")
            return {
                'video_generation': {
                    'quality': {'resolution': '1920x1080', 'bitrate': '5000k', 'audio_bitrate': '192k'},
                    'paths': {'projects_dir': 'projects', 'assets': 'overlays', 'output_dir': 'output', 'background_music_dir': 'background_music'},
                    'audio': {'default_voice': 'es-ES-AlvaroNeural'},
                    'subtitles': {'font': 'Arial', 'font_size': 24, 'color': '#FFFFFF'}
                }
            }
        except Exception as e:
            logger.error(f"Error cargando .voidrules: {e}", exc_info=True)
            return {}
    
    def _load_tts_config(self) -> Dict:
        """Carga la configuración de TTS desde config.yaml"""
        try:
            from utils.config import load_config
            config = load_config()
            tts_config = config.get('tts', {})
            logger.info(f"Configuración TTS cargada: {tts_config.get('default_provider', 'edge')}")
            return tts_config
        except Exception as e:
            logger.warning(f"Error cargando configuración TTS: {e}")
            return {
                'default_provider': 'fish',
                'edge': {
                    'default_voice': 'es-ES-AlvaroNeural',
                    'default_rate': '+0%',
                    'default_pitch': '+0Hz'
                },
                'fish_audio': {
                    'api_key': None,
                    'default_model': 'speech-1.6',
                    'default_format': 'mp3',
                    'default_mp3_bitrate': 128,
                    'default_normalize': True,
                    'default_latency': 'normal',
                    'reference_id': None
                }
            }
    
    def _load_transcription_config(self) -> Dict:
        """Carga la configuración de transcripción desde config.yaml"""
        try:
            from utils.config import load_config
            config = load_config()
            transcription_config = config.get('transcription', {})
            logger.info(f"Configuración de transcripción cargada: {transcription_config.get('service_type', 'local')}")
            return transcription_config
        except Exception as e:
            logger.warning(f"Error cargando configuración de transcripción: {e}")
    
    def _load_overlay_config(self) -> Dict:
        """Carga la configuración de overlays desde config.yaml"""
        try:
            from utils.config import load_config
            config = load_config()
            overlays_config = config.get('video_generation', {}).get('effects', {}).get('overlays', [{}])
            default_opacity = overlays_config[0].get('opacity', 0.3) if overlays_config else 0.3
            logger.info(f"Configuración de overlays cargada: opacidad por defecto {default_opacity}")
            return {'default_opacity': default_opacity}
        except Exception as e:
            logger.warning(f"Error cargando configuración de overlays: {e}")
            return {'default_opacity': 0.3}
    
    def _setup_directories(self):
        self.projects_path.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        self.background_music_path.mkdir(exist_ok=True)
    
    def _initialize_services(self):
        self.ai_service = AIServices() 
        logger.info(f"AIServices inicializado - Cliente Replicate: {self.ai_service.replicate_client is not None}")
        logger.info(f"AIServices token: {self.ai_service.replicate_token[:10] if self.ai_service.replicate_token else 'None'}...")
        self.audio_service = AudioServices() 
        self.scene_generator = SceneGenerator(config=self.void_config)
        logger.info(f"SceneGenerator inicializado: {self.scene_generator is not None}") 
        self.video_service = VideoServices() 
        
        # Inicializar servicio de transcripción según configuración
        transcription_type = self.transcription_config.get('service_type', 'local')
        logger.info(f"Configurando servicio de transcripción: {transcription_type}")
        
        if transcription_type == 'replicate':
            # Usar Replicate para transcripción
            replicate_token = self.ai_service.replicate_token
            if not replicate_token:
                logger.warning("No se encontró token de Replicate, usando transcripción local")
                self.transcription_service = get_transcription_service('local')
            else:
                # Obtener configuración específica de Replicate
                replicate_config = self.transcription_config.get('replicate', {})
                self.transcription_service = get_transcription_service('replicate', api_token=replicate_token)
                logger.info(f"TranscriptionService inicializado con Replicate - Idioma: {replicate_config.get('default_language', 'es')}")
        else:
            # Usar transcripción local
            local_config = self.transcription_config.get('local', {})
            self.transcription_service = get_transcription_service(
                'local',
                model_size=local_config.get('model_size', 'medium'),
                device=local_config.get('device', 'cpu'),
                compute_type=local_config.get('compute_type', 'int8')
            )
            logger.info(f"TranscriptionService inicializado con Whisper local - Modelo: {local_config.get('model_size', 'medium')}")
        
        # ContentOptimizer se inicializa con valores por defecto, se configurará dinámicamente
        self.content_optimizer = ContentOptimizer(self.ai_service)
        logger.info("Servicios inicializados.")

    def _save_project_info(self, folder: Path, project_info: Dict):
        try:
            info_path = folder / "project_info.json"
            project_info["last_modified"] = datetime.now().isoformat()
            serializable_info = json.loads(json.dumps(project_info, default=str))
            with open(info_path, 'w', encoding='utf-8') as f:
                json.dump(serializable_info, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"No se pudo guardar info del proyecto {folder}: {e}")

    def _setup_single_project(self, full_config: Dict) -> Dict:
        title = full_config.get('titulo', 'VideoSinTitulo')
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '_', '-')).rstrip()
        slug = safe_title.lower().replace(" ", "_")[:50] 
        project_id = f"{slug}__{uuid.uuid4().hex[:8]}"
        project_folder = self.projects_path / project_id
        project_folder.mkdir(parents=True, exist_ok=True)
        (project_folder / "audio").mkdir(exist_ok=True)
        (project_folder / "images").mkdir(exist_ok=True)
        (project_folder / "video").mkdir(exist_ok=True)
        project_info = {
             "id": project_id, "titulo": title,
             "contexto": full_config.get("contexto", ""),
             "fecha_creacion": datetime.now().isoformat(),
             "project_folder": str(project_folder), "base_path": str(project_folder),
             "status": "iniciado", "error_message": None, 
             "script_path": None, "audio_path": None, "transcription_path": None,
             "scenes_path": None, "image_paths": [],
             "final_video_path": None, "subtitled_video_path": None,
             "config_usada": {k:v for k,v in full_config.items() if k != 'script' or v.get('mode') != 'Proporcionar Manualmente'}
        }
        self._save_project_info(project_folder, project_info)
        logger.info(f"Directorio proyecto configurado: {project_folder}")
        return project_info

    def process_single_video(self, full_config: Dict, existing_project_info: Optional[Dict] = None) -> Optional[Path]:
        project_info = {} 
        base_video_clip_obj = None
        final_video_clip = None
        script_content = "" 
        
        try:
            if existing_project_info:
                project_info = existing_project_info
                base_path = Path(project_info["base_path"])
                project_id = project_info["id"]
                logger.info(f"[{project_id}] Reanudando procesamiento para proyecto existente: {project_info['titulo']}")
            else:
                project_info = self._setup_single_project(full_config)
                base_path = Path(project_info["base_path"])
                project_id = project_info["id"]
                logger.info(f"[{project_id}] Iniciando nuevo proyecto: {project_info['titulo']}")
            logger.info(f"[{project_id}] Iniciando: {project_info['titulo']}")

            # --- 1. Script --- 
            script_config_ui = full_config.get("script", {})
            script_mode = script_config_ui.get("mode", "Generar con IA")
            logger.info(f"[{project_id}] Guion (Modo: {script_mode})...")
            
            script_path_str = project_info.get("script_path")
            if script_path_str and Path(script_path_str).exists():
                script_content = Path(script_path_str).read_text(encoding='utf-8')
                logger.info(f"[{project_id}] Guion cargado desde archivo existente: {script_path_str}")
            else:
                if script_mode == "Proporcionar Manualmente":
                    script_content = script_config_ui.get("manual_script", "")
                    if not script_content: raise ValueError("Guion manual vacío.")
                    script_path = base_path / "script.txt"
                    script_path.write_text(script_content, encoding='utf-8')
                    project_info["script_path"] = str(script_path)
                    project_info["script_source"] = "manual"
                else: 
                    prompt_obj = script_config_ui.get('prompt_obj')
                    if not prompt_obj: raise ValueError("Plantilla guion no encontrada.")
                    user_prompt = prompt_obj.get("user_prompt", "").format(
                        titulo=project_info.get("titulo", ""), 
                        contexto=project_info.get("contexto", "")
                    )
                    system_prompt = prompt_obj.get("system_prompt", "")
                    script_content = self.ai_service.generate_content(
                        provider=script_config_ui.get('provider', 'openai').lower(), 
                        model=script_config_ui.get('model', 'gpt-3.5-turbo'),
                        system_prompt=system_prompt, user_prompt=user_prompt
                    )
                    if not script_content or "[ERROR]" in script_content: raise RuntimeError(f"Fallo guion IA: {script_content}")
                    script_path = base_path / "script.txt"
                    script_path.write_text(script_content, encoding='utf-8')
                    project_info["script_path"] = str(script_path)
                    project_info["script_source"] = "ia"
            project_info["status"] = "script_ok"; self._save_project_info(base_path, project_info)

            # --- 2. Audio (TTS) --- 
            logger.info(f"[{project_id}] Audio TTS...")
            audio_config_ui = full_config.get("audio", {}) # Necesario para _apply_audio después
            tts_settings = {k: v for k, v in audio_config_ui.items() if k.startswith('tts_')}
            
            audio_path_generated = project_info.get("audio_path")
            if audio_path_generated and Path(audio_path_generated).exists():
                try:
                    with AudioFileClip(audio_path_generated) as temp_audio_clip:
                        project_info["audio_duration"] = temp_audio_clip.duration
                    if project_info["audio_duration"] is None or project_info["audio_duration"] <= 0:
                        raise ValueError("La duración del audio TTS cargado es inválida.")
                    logger.info(f"[{project_id}] Audio cargado desde archivo existente: {audio_path_generated} ({project_info['audio_duration']:.2f}s)")
                except Exception as e_adur:
                    logger.error(f"[{project_id}] Error cargando duración del audio TTS {audio_path_generated}: {e_adur}")
                    raise RuntimeError(f"Fallo crítico al cargar audio TTS: {e_adur}")
            else:
                # Obtener configuración de TTS
                tts_provider = tts_settings.get('tts_provider', 'fish')
                from utils.audio_services import generate_tts_audio
                
                if tts_provider == 'edge':
                    # Configuración para Edge TTS
                    audio_path_generated = generate_tts_audio(
                        text=script_content,
                        tts_provider='edge',
                        voice=tts_settings.get('tts_voice', self.video_gen_config.get('audio',{}).get('default_voice','es-ES-AlvaroNeural')),
                        rate=f"{tts_settings.get('tts_speed_percent', 0):+d}%",
                        pitch=f"{tts_settings.get('tts_pitch_hz', 0):+d}Hz",
                        output_dir=str(base_path / "audio")
                    )
                elif tts_provider == 'fish':
                    # Configuración para Fish Audio
                    fish_config = self.tts_config.get('fish_audio', {})
                    audio_path_generated = generate_tts_audio(
                        text=script_content,
                        tts_provider='fish',
                        output_dir=str(base_path / "audio"),
                        fish_api_key=fish_config.get('api_key'),
                        fish_reference_id=fish_config.get('reference_id'),
                        fish_model=tts_settings.get('tts_fish_model', fish_config.get('default_model', 'speech-1.6')),
                        fish_format=tts_settings.get('tts_fish_format', fish_config.get('default_format', 'mp3')),
                        fish_mp3_bitrate=tts_settings.get('tts_fish_bitrate', fish_config.get('default_mp3_bitrate', 128)),
                        fish_normalize=tts_settings.get('tts_fish_normalize', fish_config.get('default_normalize', True)),
                        fish_latency=tts_settings.get('tts_fish_latency', fish_config.get('default_latency', 'normal'))
                    )
                else:
                    raise ValueError(f"Proveedor TTS no soportado: {tts_provider}")
                    
                if not audio_path_generated or not Path(audio_path_generated).exists(): 
                    raise RuntimeError("Fallo audio TTS: No se generó el archivo o no se encontró.")
                project_info["audio_path"] = audio_path_generated
                try:
                    with AudioFileClip(audio_path_generated) as temp_audio_clip: # Asegurar cierre
                        project_info["audio_duration"] = temp_audio_clip.duration
                    if project_info["audio_duration"] is None or project_info["audio_duration"] <=0:
                        raise ValueError("La duración del audio TTS es inválida.")
                except Exception as e_adur:
                    logger.error(f"[{project_id}] Error obteniendo duración del audio TTS {audio_path_generated}: {e_adur}")
                    raise RuntimeError(f"Fallo crítico al procesar duración de audio TTS: {e_adur}")

                logger.info(f"[{project_id}] Audio generado: {audio_path_generated} ({project_info['audio_duration']:.2f}s)")
            project_info["status"] = "audio_ok"; self._save_project_info(base_path, project_info)

            # --- 3. Transcripción (SIEMPRE la generamos ahora si no existe, para segmentar por tiempo) ---
            logger.info(f"[{project_id}] Preparando transcripción...")
            transcription_path_str = project_info.get("transcription_path")
            segments = [] 
            if not transcription_path_str or not Path(transcription_path_str).exists():
                logger.info(f"[{project_id}] Generando transcripción...")
                try:
                    if not project_info.get("audio_path"): raise RuntimeError("Audio no encontrado para transcripción.")
                    trans_result = self.transcription_service.transcribe_audio(project_info["audio_path"])
                    if not trans_result: raise RuntimeError("Transcripción falló o devolvió None.")
                    segments, _ = trans_result 
                    if segments is None: segments = [] # Asegurar que es una lista
                    trans_path = base_path / "transcription.json"
                    self.transcription_service.save_transcription(segments, {}, str(trans_path))
                    project_info["transcription_path"] = str(trans_path)
                    logger.info(f"[{project_id}] Transcripción guardada: {trans_path}")
                    self._save_project_info(base_path, project_info) 
                except Exception as trans_e: 
                    logger.error(f"[{project_id}] Fallo transcripción: {trans_e}", exc_info=True)
                    segments = [] 
            else:
                try: 
                    with open(transcription_path_str, 'r', encoding='utf-8') as f_trans:
                        transcription_data = json.load(f_trans)
                    segments = transcription_data.get('segments', [])
                    if segments is None: segments = []
                    logger.info(f"[{project_id}] Transcripción cargada desde archivo existente: {transcription_path_str}")
                except Exception as load_e: 
                    logger.error(f"[{project_id}] Fallo carga transcripción desde {transcription_path_str}: {load_e}", exc_info=True)
                    segments = []
            
            project_info["status"] = "transcription_ok"; self._save_project_info(base_path, project_info)

            # --- 4. Scenes & Image Prompts (Lógica condicional) --- 
            logger.info(f"[{project_id}] Generando escenas y prompts...")
            if self.scene_generator is None: self.scene_generator = SceneGenerator(config=self.void_config) 

            scenes_config = full_config.get("scenes_config", {})
            image_prompt_config = full_config.get("image", {})

            # Lógica para reanudar la generación de escenas
            scenes_path = base_path / "scenes.json"
            if scenes_path.exists():
                try:
                    with open(scenes_path, 'r', encoding='utf-8') as f:
                        scenes_json = json.load(f)
                    # Extraer la lista de escenas del JSON completo
                    scenes_data = scenes_json.get('scenes', [])
                    logger.info(f"[{project_id}] Se encontraron {len(scenes_data)} escenas existentes. Se continuará desde la última.")
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"[{project_id}] No se pudo leer scenes.json ({e}), se regenerarán todas las escenas.")
                    scenes_data = []
            else:
                scenes_data = []

            # Si no hay escenas, generarlas desde el principio
            if not scenes_data:
                 scenes_data = self.scene_generator.generate_scenes_from_script(
                    script_content=script_content,
                    transcription_segments=segments,
                    mode=scenes_config.get("segmentation_mode", "Por Párrafos (Híbrido)"),
                    project_info=project_info,
                    image_prompt_config=image_prompt_config,
                    ai_service=self.ai_service
                )

            # Lógica para reanudar la generación de prompts
            if not all(s.get('image_prompt') for s in scenes_data):
                logger.info(f"[{project_id}] Faltan prompts de imagen, generando...")
                scenes_data = self.scene_generator.generate_image_prompts_for_scenes(
                    scenes=scenes_data,
                    project_info=project_info,
                    image_prompt_config=image_prompt_config,
                    ai_service=self.ai_service
                )
        
            scenes_path = self.scene_generator.save_scenes(scenes_data, str(scenes_path), project_info)
            #self._save_scenes(base_path, scenes_data)
            project_info["scenes_path"] = str(scenes_path)
            project_info["image_prompts"] = [s.get('image_prompt', '[PROMPT FALTANTE]') for s in scenes_data]
            project_info["status"] = "scenes_ok"; self._save_project_info(base_path, project_info)

            # --- 5. Images --- 
            logger.info(f"[{project_id}] Iniciando generación de imágenes...")
            # Lógica para reanudar la generación de imágenes
            images_path = base_path / "images"
            images_path.mkdir(exist_ok=True)
            existing_images = [f.stem for f in images_path.glob("scene_*.webp")]

            image_paths = []
            for i, scene in enumerate(scenes_data):
                scene_name = f"scene_{i:03d}"
                image_path = images_path / f"{scene_name}.webp"
                
                if scene_name in existing_images and image_path.exists():
                    logger.info(f"[{project_id}] La imagen para la escena {i+1} ya existe. Saltando.")
                    image_paths.append(str(image_path))
                    continue

                logger.info(f"[{project_id}] Generando imagen para la escena {i+1}/{len(scenes_data)}...")
                try:
                    generated_path = self.image_generator.generate_image(
                        prompt=scene.get("image_prompt"),
                        output_path=str(image_path),
                        config=image_prompt_config
                    )
                    if generated_path:
                        image_paths.append(generated_path)
                        scene["image_path"] = generated_path
                    else:
                        logger.error(f"[{project_id}] Falló la generación de imagen para la escena {i+1}. Prompt: {scene.get('image_prompt')}")
                        # Opcional: añadir una imagen placeholder para no detener el proceso
                        # image_paths.append(str(self.assets_dir / "placeholder.webp"))

                except Exception as img_e:
                    logger.error(f"[{project_id}] Excepción al generar imagen para la escena {i+1}: {img_e}")
            
            project_info["image_paths"] = image_paths
            if len(image_paths) != len(scenes_data):
                 raise ValueError("No se generaron imágenes válidas para todas las escenas.")
            logger.info(f"[{project_id}] {len(project_info['image_paths'])} imágenes generadas y válidas.")
            project_info["status"] = "images_ok"; self._save_project_info(base_path, project_info)

            # --- 6. Video Assembly con Sincronización por Transcripción --- 
            logger.info(f"[{project_id}] Ensamblando video base con sincronización de audio...")
            video_config_ui = full_config.get("video", {})
            
            # --- INICIO DEL CÓDIGO CORREGIDO ---
            scene_durations = []
            num_images = len(project_info["image_paths"])
            # Usar la duración total del audio para el cálculo final
            total_audio_duration = project_info.get('audio_duration', 0)

            # DEBUG: Log de datos de entrada
            logger.info(f"[{project_id}] === DEBUG DURACIONES ===")
            logger.info(f"[{project_id}] Número de escenas: {len(scenes_data)}")
            logger.info(f"[{project_id}] Número de imágenes: {num_images}")
            logger.info(f"[{project_id}] Duración total audio: {total_audio_duration:.3f}s")

            if scenes_data:
                logger.info(f"[{project_id}] Rango timestamps escenas:")
                for i, scene in enumerate(scenes_data[:5]):  # Solo las primeras 5
                    logger.info(f"[{project_id}]   Escena {i}: start={scene.get('start', 'N/A'):.3f}s, end={scene.get('end', 'N/A'):.3f}s")

            # **MÉTODO 1: El ideal. Calcular duraciones usando los 'start' de las escenas para incluir silencios.**
            if scenes_data and all(s.get('start') is not None for s in scenes_data) and len(scenes_data) == num_images and total_audio_duration > 0:
                logger.info(f"[{project_id}] Calculando duraciones de escena para sincronizar con audio (incluyendo silencios).")
                
                # Ordenar las escenas por tiempo de inicio para asegurar el cálculo correcto
                scenes_data.sort(key=lambda s: s['start'])
                
                for i, scene in enumerate(scenes_data):
                    current_scene_start = scene['start']
                    
                    if i < len(scenes_data) - 1:
                        # La duración de esta escena es el tiempo desde que empieza hasta que empieza la siguiente.
                        next_scene_start = scenes_data[i+1]['start']
                        duration = next_scene_start - current_scene_start
                    else:
                        # Es la última escena, su duración se extiende hasta el final del audio.
                        # Asegurarse de que current_scene_start no exceda total_audio_duration
                        effective_start = min(current_scene_start, total_audio_duration)
                        duration = total_audio_duration - effective_start
                    
                    # Comprobación de seguridad para evitar duraciones negativas o cero
                    if duration <= 0: # Si es cero o negativo, significa que la escena no tiene duración real de audio
                        logger.warning(f"[{project_id}] Duración calculada no positiva ({duration:.2f}s) para escena {i}. Estableciendo a 0.1s para evitar errores de FFmpeg y mantener sincronización.")
                        duration = 0.1 # Un valor mínimo para que FFmpeg no falle, pero que no desincronice mucho
                    
                    scene_durations.append(duration)
                
                # Opcional: añadir un poco de tiempo extra al final si se desea (yo lo quitaría para una sincronización perfecta)
                # if scene_durations:
                #     scene_durations[-1] += 1.0

                logger.info(f"[{project_id}] Duraciones por escena calculadas para sincronización: {[f'{d:.2f}s' for d in scene_durations]}")
                total_video_duration = sum(scene_durations)
                logger.info(f"[{project_id}] Duración total del video calculada: {total_video_duration:.2f}s. Duración del audio: {total_audio_duration:.2f}s.")
                
                # SECCIÓN CORREGIDA - Ajuste seguro de duraciones
                total_video_duration = sum(scene_durations)
                logger.info(f"[{project_id}] Duración total del video calculada: {total_video_duration:.2f}s. Duración del audio: {total_audio_duration:.2f}s.")

                # Si la diferencia es notable, ajustar de forma segura
                if abs(total_video_duration - total_audio_duration) > 0.1:
                    diff = total_audio_duration - total_video_duration
                    logger.info(f"[{project_id}] Diferencia detectada: {diff:.2f}s. Ajustando duraciones de forma segura...")
                    
                    if diff > 0:
                        # El video es más corto que el audio - añadir tiempo a la última escena
                        scene_durations[-1] += diff
                        logger.info(f"[{project_id}] Añadidos {diff:.2f}s a la última escena.")
                    else:
                        # El video es más largo que el audio - reducir duraciones proporcionalmente
                        # para evitar duraciones negativas
                        excess_time = abs(diff)
                        logger.info(f"[{project_id}] Video {excess_time:.2f}s más largo que audio. Reduciendo proporcionalmente...")
                        
                        # Calcular cuánto se puede reducir de cada escena sin volverla negativa
                        min_duration = 0.5  # Duración mínima por escena
                        reducible_time = 0.0
                        for duration in scene_durations:
                            if duration > min_duration:
                                reducible_time += (duration - min_duration)
                        
                        if reducible_time >= excess_time:
                            # Se puede reducir proporcionalmente
                            reduction_factor = excess_time / reducible_time
                            for i in range(len(scene_durations)):
                                if scene_durations[i] > min_duration:
                                    reducible = scene_durations[i] - min_duration
                                    reduction = reducible * reduction_factor
                                    scene_durations[i] -= reduction
                            logger.info(f"[{project_id}] Duraciones reducidas proporcionalmente (factor: {reduction_factor:.3f})")
                        else:
                            # No se puede reducir lo suficiente - usar distribución uniforme
                            logger.warning(f"[{project_id}] No se puede reducir {excess_time:.2f}s sin duraciones negativas. Usando distribución uniforme.")
                            avg_duration = total_audio_duration / len(scene_durations)
                            scene_durations = [max(avg_duration, 0.5) for _ in scene_durations]
                            
                            # Ajustar la última para que coincida exactamente
                            current_total = sum(scene_durations[:-1])
                            scene_durations[-1] = max(total_audio_duration - current_total, 0.5)
                            logger.info(f"[{project_id}] Aplicada distribución uniforme de {avg_duration:.2f}s por escena")

                # VALIDACIÓN FINAL - Asegurar que no hay duraciones negativas o cero
                for i, duration in enumerate(scene_durations):
                    if duration <= 0:
                        logger.error(f"[{project_id}] ¡DURACIÓN INVÁLIDA DETECTADA! Escena {i}: {duration:.3f}s")
                        scene_durations[i] = 0.5  # Valor mínimo de seguridad
                        logger.warning(f"[{project_id}] Escena {i} corregida a 0.5s")

                # Log final para verificación
                final_total = sum(scene_durations)
                logger.info(f"[{project_id}] DURACIONES FINALES:")
                logger.info(f"[{project_id}] Total calculado: {final_total:.2f}s")
                logger.info(f"[{project_id}] Audio original: {total_audio_duration:.2f}s")
                logger.info(f"[{project_id}] Diferencia final: {abs(final_total - total_audio_duration):.3f}s")
                logger.info(f"[{project_id}] Rango duraciones: {min(scene_durations):.2f}s - {max(scene_durations):.2f}s")

                # Verificación final de seguridad
                if any(d <= 0 for d in scene_durations):
                    logger.error(f"[{project_id}] ¡ERROR CRÍTICO! Aún hay duraciones <= 0 después de las correcciones")
                    raise ValueError("Se detectaron duraciones negativas o cero después de todas las correcciones")

                # --- INICIO DEL NUEVO BLOQUE DE CÓDIGO DE COMPENSACIÓN DE TRANSICIONES ---
                # Ahora, pre-compensamos la duración que se perderá por las transiciones.
                transition_duration = video_config_ui.get('transition_duration', 0)
                transition_type = video_config_ui.get('transition_type', 'none')

                # Solo aplicar compensación si la transición es de tipo fundido/disolución
                is_crossfade_transition = transition_type.lower() in ['dissolve', 'fade']

                if num_images > 1 and transition_duration > 0 and is_crossfade_transition:
                    time_lost_to_transitions = (num_images - 1) * transition_duration
                    logger.info(f"[{project_id}] Compensando {time_lost_to_transitions:.2f}s que se perderán por {num_images - 1} transiciones de '{transition_type}'.")
                    
                    # Creamos una copia para no modificar la original mientras iteramos
                    compensated_durations = list(scene_durations)
                    # Añadimos la duración de la transición a cada clip EXCEPTO el último,
                    # ya que el último no tiene una transición de salida que le acorte.
                    for i in range(len(compensated_durations) - 1):
                        compensated_durations[i] += transition_duration
                    
                    # La duración total de los clips fuente ahora debería ser correcta para que, 
                    # DESPUÉS de aplicar las transiciones, el vídeo final tenga la duración del audio.
                    original_total = sum(scene_durations)
                    compensated_total = sum(compensated_durations)
                    logger.info(f"[{project_id}] La suma de duraciones original era {original_total:.2f}s. La suma compensada es {compensated_total:.2f}s.")
                    
                    # Usamos las duraciones compensadas para crear el vídeo.
                    scene_durations = compensated_durations
                # --- FIN DEL NUEVO BLOQUE DE CÓDIGO DE COMPENSACIÓN DE TRANSICIONES ---

            # **MÉTODO 2: Fallback (el resto del código se mantiene igual)**
            elif segments and len(segments) > 0:
                logger.warning(f"[{project_id}] No se pudieron usar los timestamps de las escenas. Usando distribución uniforme basada en duración total del audio.")
                
                # La lógica de fallback existente...
                if num_images > 0 and total_audio_duration > 0:
                    duration_per_image = total_audio_duration / num_images
                    scene_durations = [duration_per_image] * num_images
                    
                    if scene_durations:
                        scene_durations[-1] += 1.0
                        logger.info(f"[{project_id}] Añadido 1 segundo extra a la última imagen para suavizar el final")
                    
                    logger.info(f"[{project_id}] Distribución uniforme: {duration_per_image:.2f}s por imagen")
                else:
                    raise ValueError("No hay imágenes o duración de audio para sincronizar")
            # --- FIN DEL CÓDIGO CORREGIDO ---
            
            # **MÉTODO 3: Último fallback**
            else:
                logger.warning(f"[{project_id}] No hay segmentos de transcripción, usando duraciones de fallback")
                
                # Intentar usar duración del audio del project_info
                audio_duration = project_info.get('audio_duration', 0)
                if audio_duration > 0 and num_images > 0:
                    duration_per_image = audio_duration / num_images
                    scene_durations = [duration_per_image] * num_images
                    logger.info(f"[{project_id}] Fallback: distribución uniforme {duration_per_image:.2f}s por imagen (total: {audio_duration:.2f}s)")
                else:
                    # Último fallback: duración fija
                    default_duration = video_config_ui.get('duration_per_image_manual', 10.0)
                    scene_durations = [default_duration] * num_images
                    logger.warning(f"[{project_id}] Último fallback: duración fija de {default_duration}s por imagen")
                
                # Añadir 1 segundo extra al final
                if scene_durations:
                    scene_durations[-1] += 1.0
                    logger.info(f"[{project_id}] Añadido 1 segundo extra a la última imagen para suavizar el final")
            
            if not scene_durations:
                raise ValueError("No se pudieron determinar duraciones para las escenas")


            # Preparar efectos por clip si están configurados
            effects_per_clip = None
            effects_ui = video_config_ui.get('effects', [])
            if effects_ui:
                effects_per_clip = self._distribute_effects_per_clip(effects_ui, len(project_info["image_paths"]))
                logger.info(f"[{project_id}] Efectos distribuidos por clip: {len(effects_per_clip)} clips con efectos")
            
            # Preparar overlays por clip si están configurados
            overlays_per_clip = None
            overlays_ui = video_config_ui.get('overlays', [])
            if overlays_ui:
                overlays_per_clip = self._distribute_overlays_per_clip(overlays_ui, len(project_info["image_paths"]))
                logger.info(f"[{project_id}] Overlays distribuidos por clip: {len(overlays_per_clip)} clips con overlays")
            
            base_video_path = self.video_service.create_video_from_images(
                 images=project_info["image_paths"], 
                 scene_durations=scene_durations, 
                 transition_duration=video_config_ui.get('transition_duration', 1.0),
                 transition_type=video_config_ui.get('transition_type', 'fade'),
                 effects_per_clip=effects_per_clip,
                 overlays_per_clip=overlays_per_clip)
            
            if not base_video_path or not Path(base_video_path).exists(): 
                raise RuntimeError("Fallo creación video base (sin audio).")
            logger.info(f"[{project_id}] Video base (sin audio) ensamblado: {base_video_path}")
            project_info["status"] = "base_video_ok"; self._save_project_info(base_path, project_info)

            # --- 7. Post-processing (Audio, Effects, Subs) --- 
            base_video_clip_obj = VideoFileClip(base_video_path) # Cargar el video SIN audio
            final_video_clip = base_video_clip_obj # Iniciar con el clip base
            
            logger.info(f"[{project_id}] Aplicando audio principal (TTS)...")
            # Usar la variable audio_config_ui que ya contiene full_config.get("audio", {})
            logger.info(f"[{project_id}] DEBUG ANTES DE _apply_audio: audio_config_ui = {audio_config_ui}")
            final_video_clip = self._apply_audio(final_video_clip, project_info, audio_config_ui)
            project_info["status"] = "post_audio_ok"; self._save_project_info(base_path, project_info)
            
            logger.info(f"[{project_id}] Aplicando efectos/overlays finales...")
            # NOTA: Los overlays YA están aplicados en el video base por clip individual
            # Solo aplicar efectos globales (fade in/out) aquí, NO overlays
            final_video_clip = self._apply_effects_overlays(final_video_clip, project_info, video_config_ui, skip_overlays=True)
            project_info["status"] = "post_effects_ok"; self._save_project_info(base_path, project_info)

            # --- Subtitles --- 
            subtitles_config_ui = full_config.get("subtitles", {})
            project_info["subtitled_video_generated"] = False # Resetear
            if subtitles_config_ui.get("enable", True):
                logger.info(f"[{project_id}] Procesando subtítulos...")
                # 'segments' ya debería estar cargada desde el paso de Transcripción
                if not segments: # Si falló la carga/generación de segmentos antes
                    logger.warning(f"[{project_id}] No hay segmentos de transcripción disponibles para subtítulos.")
                else:
                    try:
                        # Usar los 'segments' ya disponibles
                        split_segments_for_subs = split_subtitle_segments(segments, max_words=subtitles_config_ui.get('max_words', 7))
                        
                        # Obtener config de subtítulos de .voidrules como fallback
                        font_conf_void = self.video_gen_config.get('subtitles', {})
                        
                        # Obtener fade_out_duration para sincronizar subtítulos
                        fade_out_duration = video_config_ui.get('fade_out', 0)
                        
                        subtitled_clip_candidate = self.video_service.add_hardcoded_subtitles(
                            video_clip=final_video_clip, 
                            segments=split_segments_for_subs,
                            font=subtitles_config_ui.get('font', font_conf_void.get('font', 'Arial')),
                            font_size=subtitles_config_ui.get('size', font_conf_void.get('font_size', 24)),
                            color=subtitles_config_ui.get('color', font_conf_void.get('font_color', '#FFFFFF')),
                            stroke_color=subtitles_config_ui.get('stroke_color', font_conf_void.get('outline_color', '#000000')),
                            stroke_width=subtitles_config_ui.get('stroke_width', font_conf_void.get('stroke_width', 1.5)), # Ajustado default
                            position=subtitles_config_ui.get('position', font_conf_void.get('position', 'bottom')),
                            fade_out_duration=fade_out_duration  # NUEVO: Sincronizar fade out con video
                        )
                        if subtitled_clip_candidate:
                             # Antes de asignar, cerrar el anterior si es diferente y no es el base_video_clip_obj
                             if final_video_clip and final_video_clip is not subtitled_clip_candidate and final_video_clip is not base_video_clip_obj:
                                 try: final_video_clip.close()
                                 except: pass
                             final_video_clip = subtitled_clip_candidate
                             project_info["subtitled_video_generated"] = True 
                             logger.info(f"[{project_id}] Subtítulos añadidos al video.")
                        else: 
                            logger.warning(f"[{project_id}] Fallo al añadir subtítulos (add_hardcoded_subtitles devolvió None).")
                    except Exception as sub_err: 
                        logger.error(f"[{project_id}] Error durante el proceso de subtitulado: {sub_err}", exc_info=True)
            else: 
                logger.info(f"[{project_id}] Subtítulos deshabilitados por configuración.")
            project_info["status"] = "post_subtitles_ok"; self._save_project_info(base_path, project_info)


            # --- 8. Final Save ---
            logger.info(f"[{project_id}] Guardando video final...")
            output_filename = f"{project_id}_final{'_subtitled' if project_info.get('subtitled_video_generated') else ''}.mp4"
            final_video_path = base_path / "video" / output_filename

            try:
                # 1. Preparar rutas de los componentes
                temp_video_path = base_path / "video" / f"{project_id}_temp_video.mp4"
                tts_audio_path = project_info.get('audio_path')
                
                # Esta es la clave: obtener la ruta de la música procesada desde project_info
                processed_music_path = project_info.get("temp_background_music_path")

                if not final_video_clip:
                    raise ValueError("El clip de video final es None. No se puede guardar.")
                
                # 2. Guardar el clip de video SIN NINGÚN AUDIO
                logger.info(f"[{project_id}] Guardando componente de video sin audio en: {temp_video_path}")
                final_video_clip.without_audio().write_videofile(
                    str(temp_video_path),
                    fps=24,
                    codec='libx264',
                    preset='medium',
                    logger=None,  # Usar None para evitar barras de progreso en los logs
                    threads=os.cpu_count() or 2
                )
                
                # 3. Construir el comando FFmpeg para combinar todo
                ffmpeg_cmd = ['ffmpeg', '-y']  # -y para sobrescribir el archivo de salida si existe
                
                # Input 0: Video
                ffmpeg_cmd.extend(['-i', str(temp_video_path)])
                
                # Input 1: Audio TTS
                if not tts_audio_path or not Path(tts_audio_path).exists():
                    raise FileNotFoundError("El archivo de audio TTS no se encontró para la mezcla final.")
                ffmpeg_cmd.extend(['-i', str(tts_audio_path)])

                # Lógica de combinación de audio
                if processed_music_path and Path(processed_music_path).exists():
                    # --- CASO CON MÚSICA DE FONDO ---
                    logger.info(f"[{project_id}] Combinando video, TTS y música de fondo con FFmpeg.")
                    
                    # Input 2: Música de fondo
                    ffmpeg_cmd.extend(['-i', str(processed_music_path)])
                    
                    # Filtro para mezclar los dos audios: TTS (stream 1) y Música (stream 2)
                    # 'amix' mezcla los audios. 'duration=first' hace que la mezcla dure lo que el primer audio (TTS).
                    # 'dropout_transition=3' ayuda a suavizar el final si los audios no tienen la misma longitud.
                    ffmpeg_cmd.extend(['-filter_complex', '[1:a][2:a]amix=inputs=2:duration=first:dropout_transition=3[aout]'])
                    
                    # Mapear los streams de salida
                    ffmpeg_cmd.extend(['-map', '0:v:0'])    # Video del input 0
                    ffmpeg_cmd.extend(['-map', '[aout]'])  # El audio mezclado que creamos
                    
                else:
                    # --- CASO SIN MÚSICA DE FONDO ---
                    logger.info(f"[{project_id}] Combinando video y audio TTS con FFmpeg.")
                    # Mapear los streams de salida
                    ffmpeg_cmd.extend(['-map', '0:v:0'])  # Video del input 0
                    ffmpeg_cmd.extend(['-map', '1:a:0'])  # Audio del input 1 (TTS)

                # Configuración de códecs y de salida final
                quality_settings = self.video_gen_config.get('quality', {})
                audio_bitrate = quality_settings.get('audio_bitrate', '192k')
                
                ffmpeg_cmd.extend([
                    '-c:v', 'copy',          # Copia el stream de video sin recodificar (muy rápido)
                    '-c:a', 'aac',           # Codifica el audio a AAC (muy compatible)
                    '-b:a', audio_bitrate,   # Bitrate del audio
                    str(final_video_path)
                ])

                # 4. Ejecutar el comando FFmpeg
                logger.info(f"[{project_id}] Ejecutando comando FFmpeg: {' '.join(ffmpeg_cmd)}")
                result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, check=True)
                logger.info(f"[{project_id}] FFmpeg stdout: {result.stdout}")
                if result.stderr:
                    logger.info(f"[{project_id}] FFmpeg stderr: {result.stderr}")

                logger.info(f"[{project_id}] Video final guardado exitosamente en: {final_video_path}")

                # 5. Actualizar la información del proyecto
                if project_info.get("subtitled_video_generated"): 
                    project_info["subtitled_video_path"] = str(final_video_path)
                else: 
                    project_info["final_video_path"] = str(final_video_path)
                project_info["status"] = "completado"
                self._save_project_info(base_path, project_info)

            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                logger.error(f"[{project_id}] Error crítico durante el guardado con FFmpeg: {e}", exc_info=True)
                if isinstance(e, subprocess.CalledProcessError):
                    logger.error(f"[{project_id}] Salida de error de FFmpeg: {e.stderr}")
                project_info["status"] = "error_guardado"
                project_info["error_message"] = str(e)
                self._save_project_info(base_path, project_info)
                return None  # Devolver None para indicar fallo
            except Exception as e_write:
                logger.error(f"[{project_id}] Error inesperado durante el guardado: {e_write}", exc_info=True)
                project_info["status"] = "error_guardado_inesperado"
                project_info["error_message"] = str(e_write)
                self._save_project_info(base_path, project_info)
                return None
            finally:
                # 6. Limpieza de archivos temporales
                if 'temp_video_path' in locals():
                    temp_video_path.unlink(missing_ok=True)
                if processed_music_path and Path(processed_music_path).exists():
                    Path(processed_music_path).unlink(missing_ok=True)
                logger.info(f"[{project_id}] Limpieza de archivos temporales finalizada.") 
            
            # --- GENERAR CONTENIDO OPTIMIZADO (OPCIONAL) ---
            if full_config.get('generate_optimized_content', False):
                logger.info(f"[{project_id}] Generando contenido optimizado para YouTube...")
                try:
                    optimized_content = self.content_optimizer.generate_optimized_content(project_info, full_config)
                    if optimized_content:
                        txt_path, json_path = self.content_optimizer.save_optimized_content(optimized_content, base_path)
                        if txt_path and json_path:
                            project_info["content_optimization_txt"] = str(txt_path)
                            project_info["content_optimization_json"] = str(json_path)
                            logger.info(f"[{project_id}] Contenido optimizado generado exitosamente")
                        else:
                            logger.warning(f"[{project_id}] Error guardando contenido optimizado")
                    else:
                        logger.warning(f"[{project_id}] No se pudo generar contenido optimizado")
                except Exception as opt_error:
                    logger.error(f"[{project_id}] Error generando contenido optimizado: {opt_error}")
                    # Continuar sin contenido optimizado, no es crítico
            
            return final_video_path

        except Exception as e:
            logger.error(f"[{project_info.get('id', 'UNKNOWN')}] Error procesando video: {e}", exc_info=True)
            if project_info and project_info.get("base_path"): # Asegurar que project_info y base_path existen
                project_info["status"] = f"error_en_{project_info.get('status','desconocido')}"
                project_info["error_message"] = str(e)
                self._save_project_info(Path(project_info["base_path"]), project_info)
            # No relanzar si queremos que la app maneje el error de forma más controlada en la UI
            # raise # Comentado para permitir que la UI muestre el error
            return None # Devolver None en caso de error para que la UI sepa
        finally:
            # Cerrar clips de MoviePy para liberar recursos
            if base_video_clip_obj: 
                try: base_video_clip_obj.close()
                except Exception as e_cls: logger.debug(f"Excepción al cerrar base_video_clip_obj: {e_cls}")
            
            # final_video_clip puede ser el mismo que base_video_clip_obj o uno nuevo (con subs, etc.)
            # Solo cerrar si es diferente y no es None
            if final_video_clip and final_video_clip is not base_video_clip_obj: 
                try: final_video_clip.close()
                except Exception as e_cls: logger.debug(f"Excepción al cerrar final_video_clip: {e_cls}")
            
            # Limpieza de archivos temporales ya no necesaria con el nuevo manejo de audio


            if project_info.get("status") != "completado": 
                logger.warning(f"[{project_info.get('id', 'UNKNOWN')}] Proceso no completado, estado: {project_info.get('status')}")
                return None # Devuelve None si no se completó
        
            return final_video_path

    # --- Métodos Auxiliares --- 

    def _apply_audio(self, video_clip: VideoFileClip, project_info: Dict, audio_config_ui: Dict) -> VideoFileClip:
        """
        Aplica el audio TTS y prepara la música de fondo para el guardado final.
        Utiliza rutas absolutas para mayor robustez.
        """
        from moviepy.editor import AudioFileClip, concatenate_audioclips
        
        project_id = project_info.get('id', 'AUDIO')
        logger.info(f"[{project_id}] Iniciando _apply_audio...")
        
        tts_path = project_info.get('audio_path')
        if not tts_path or not os.path.exists(tts_path):
            logger.warning(f"[{project_id}] No hay TTS path válido. Devolviendo clip original.")
            return video_clip

        try:
            # Cargar el audio TTS y aplicar volumen
            tts_audio_clip = AudioFileClip(tts_path)
            logger.info(f"[{project_id}] TTS cargado ({tts_audio_clip.duration:.2f}s)")
            tts_volume = audio_config_ui.get('tts_volume', 1.0)
            if tts_volume != 1.0:
                tts_audio_clip = tts_audio_clip.volumex(tts_volume)
                logger.info(f"[{project_id}] Volumen TTS ajustado a {tts_volume}")

            # Aplicar solo el audio TTS al clip por ahora. La música se gestionará en el guardado.
            new_video_clip = video_clip.set_audio(tts_audio_clip)
            
            # --- LÓGICA DE MÚSICA DE FONDO MEJORADA ---
            relative_music_path = audio_config_ui.get('bg_music_selection')
            
            # Siempre inicializamos la ruta de música temporal a None
            project_info["temp_background_music_path"] = None

            if relative_music_path and relative_music_path != "**Ninguna**":
                # Construir la ruta absoluta usando PROJECT_ROOT
                absolute_music_path = PROJECT_ROOT / relative_music_path
                logger.info(f"[{project_id}] Ruta de música relativa seleccionada: '{relative_music_path}'")
                logger.info(f"[{project_id}] Intentando cargar desde ruta absoluta: '{absolute_music_path}'")

                if not absolute_music_path.exists():
                    logger.error(f"[{project_id}] ¡¡ERROR CRÍTICO!! El archivo de música NO EXISTE en la ruta absoluta: {absolute_music_path}")
                    # El proceso continuará sin música, pero el error es claro.
                else:
                    try:
                        logger.info(f"[{project_id}] Archivo de música encontrado. Procesando...")
                        
                        bg_music_clip = AudioFileClip(str(absolute_music_path))
                        
                        music_volume = audio_config_ui.get('music_volume', 0.06)
                        bg_music_clip = bg_music_clip.volumex(music_volume)
                        
                        video_duration = video_clip.duration
                        music_loop = audio_config_ui.get('music_loop', True)
                        
                        if music_loop and bg_music_clip.duration < video_duration:
                            loops_needed = int(video_duration / bg_music_clip.duration) + 1
                            looped_clips = [bg_music_clip] * loops_needed
                            bg_music_clip = concatenate_audioclips(looped_clips).subclip(0, video_duration)
                            logger.info(f"[{project_id}] Música en loop para {video_duration:.2f}s")
                        elif bg_music_clip.duration > video_duration:
                            bg_music_clip = bg_music_clip.subclip(0, video_duration)
                            logger.info(f"[{project_id}] Música cortada a {video_duration:.2f}s")

                        # Guardar música procesada para usarla después con FFmpeg
                        temp_dir = PROJECT_ROOT / "temp"
                        temp_dir.mkdir(exist_ok=True)
                        temp_music_path = temp_dir / f"processed_music_{project_id}.mp3"
                        
                        bg_music_clip.write_audiofile(str(temp_music_path), logger=None, codec='mp3')
                        
                        if not temp_music_path.exists():
                            raise RuntimeError(f"No se pudo crear archivo temporal de música: {temp_music_path}")

                        logger.info(f"[{project_id}] Música procesada guardada en: {temp_music_path}")
                        
                        # Marcar que hay música de fondo para que el proceso de guardado lo sepa
                        project_info["temp_background_music_path"] = str(temp_music_path)
                        
                        bg_music_clip.close()

                    except Exception as music_error:
                        logger.error(f"[{project_id}] Error procesando el archivo de música '{absolute_music_path}': {music_error}. Se continuará sin ella.", exc_info=True)
            else:
                logger.info(f"[{project_id}] No se ha seleccionado música de fondo o la ruta está vacía.")

            return new_video_clip

        except Exception as e:
            logger.error(f"[{project_id}] Error crítico en _apply_audio: {e}", exc_info=True)
            return video_clip

    def _apply_effects_overlays(self, video_clip: CompositeVideoClip, project_info: Dict, video_config_ui: Dict, skip_overlays: bool = False) -> CompositeVideoClip:
        project_id = project_info.get('id', 'EFFECTS')
        logger.info(f"[{project_id}] Aplicando efectos/overlays...") 
        final_clip = video_clip
        opened_overlays = [] 
        
        overlays_ui = video_config_ui.get('overlays', [])
        if overlays_ui and not skip_overlays:
             overlays_config_void = self.video_gen_config.get('effects', {}).get('overlays', [])
             overlay_map = {Path(o['name']).name: o for o in overlays_config_void if isinstance(o, dict) and 'name' in o}
             logger.info(f"[{project_id}] Overlays UI: {overlays_ui}")
             logger.debug(f"[{project_id}] Overlays config: {overlay_map}")
             clips_for_composition = [final_clip]
        elif overlays_ui and skip_overlays:
             logger.info(f"[{project_id}] Overlays detectados pero SALTADOS (ya aplicados en video base): {len(overlays_ui)} overlay(s)")
        else:
             logger.info(f"[{project_id}] No hay overlays configurados.") 

        if overlays_ui and not skip_overlays:
             for overlay_ui_info in overlays_ui:
                 # overlay_ui_info es una tupla: (nombre, opacidad, tiempo_inicio, duración)
                 if isinstance(overlay_ui_info, tuple) and len(overlay_ui_info) >= 2:
                     overlay_name = overlay_ui_info[0]
                     ui_opacity = overlay_ui_info[1]
                 elif isinstance(overlay_ui_info, str):
                     overlay_name = overlay_ui_info
                     ui_opacity = self.overlay_config.get('default_opacity', 0.3)
                 elif isinstance(overlay_ui_info, dict):
                     overlay_name = overlay_ui_info.get('name')
                     ui_opacity = overlay_ui_info.get('opacity', self.overlay_config.get('default_opacity', 0.3))
                 else:
                     logger.warning(f"[{project_id}] Formato de overlay no reconocido: {type(overlay_ui_info)} - {overlay_ui_info}")
                     continue
                     
                 if not overlay_name: continue
                 overlay_file_name = Path(overlay_name).name # Usar solo nombre de archivo para buscar en mapa
                 overlay_settings = overlay_map.get(overlay_file_name)
                 
                 opacity, pos, should_loop = ui_opacity, 'center', True 
                 overlay_path = self.assets_dir / overlay_file_name 

                 if overlay_settings:
                      overlay_path_cfg = Path(overlay_settings['name'])
                      if overlay_path_cfg.is_absolute() and overlay_path_cfg.exists(): overlay_path = overlay_path_cfg
                      elif (self.assets_dir / overlay_path_cfg.name).exists(): overlay_path = self.assets_dir / overlay_path_cfg.name
                      else: logger.error(f"Overlay no encontrado: {overlay_settings['name']} ni en assets {overlay_path}"); continue
                      opacity = overlay_settings.get('opacity', opacity)
                      pos = overlay_settings.get('position', pos)
                      should_loop = overlay_settings.get('loop', should_loop)
                 elif not overlay_path.exists(): logger.error(f"Overlay (sin config) no encontrado: {overlay_path}"); continue
                      
                 logger.info(f"Aplicando overlay: {overlay_path.name} (Op:{opacity}, Pos:{pos}, Loop:{should_loop})")
                 try:
                    # Verificar si es video o imagen
                    is_video_overlay = overlay_path.suffix.lower() in [".mp4", ".webm", ".mov"]
                    if is_video_overlay:
                         # Cargar el overlay de video
                         overlay_clip_obj = VideoFileClip(str(overlay_path), has_mask=True).set_opacity(opacity)
                         
                         # Obtener la duración del video principal
                         video_duration = final_clip.duration
                         
                         logger.info(f"Overlay {overlay_path.name}: duración original {overlay_clip_obj.duration:.2f}s, video principal: {video_duration:.2f}s")
                         
                         if should_loop and overlay_clip_obj.duration < video_duration:
                             # Aplicar loop si es necesario y el overlay es más corto
                             overlay_clip_obj = loop(overlay_clip_obj, duration=video_duration)
                             logger.info(f"Overlay {overlay_path.name} en loop para {video_duration:.2f}s")
                         
                         # Asegurarse de que el overlay tenga exactamente la duración del video principal
                         # Esto es crucial para evitar que MoviePy intente leer más allá.
                         if overlay_clip_obj.duration > video_duration:
                             overlay_clip_obj = overlay_clip_obj.subclip(0, video_duration)
                             logger.info(f"Overlay {overlay_path.name} cortado a la duración del video principal ({video_duration:.2f}s)")
                         elif overlay_clip_obj.duration < video_duration:
                             # Si por alguna razón (ej. no loop y más corto) sigue siendo más corto, extenderlo
                             # Esto es un fallback, la lógica de loop debería manejarlo.
                             overlay_clip_obj = overlay_clip_obj.set_duration(video_duration)
                             logger.info(f"Overlay {overlay_path.name} extendido a la duración del video principal ({video_duration:.2f}s)")
                    else: 
                         # Asumir imagen
                         overlay_clip_obj = ImageClip(str(overlay_path), ismask=True).set_opacity(opacity)
                         overlay_clip_obj = overlay_clip_obj.set_duration(final_clip.duration)
                         should_loop = False  # Las imágenes no necesitan loop
                         
                    opened_overlays.append(overlay_clip_obj)
                    overlay_clip_obj = overlay_clip_obj.set_position(pos).set_start(0)
                    clips_for_composition.append(overlay_clip_obj)
                 except Exception as e: logger.error(f"Error aplicando overlay {overlay_path.name}: {e}", exc_info=True)
             
             if len(clips_for_composition) > 1:
                 logger.debug(f"Componiendo {len(clips_for_composition)} clips...")
                 final_clip = CompositeVideoClip(clips_for_composition, use_bgclip=True)
             
             for ov_clip in opened_overlays: 
                 try: ov_clip.close() 
                 except: pass

        # --- Los efectos se aplican por clip individual durante la creación del video base ---
        # Los overlays se aplican aquí al video completo o también por clip según configuración
        logger.info(f"[{project_id}] Efectos aplicados por clip individual. Overlays aplicados al video completo.")
            
        fade_in = video_config_ui.get('fade_in', 0)
        fade_out = video_config_ui.get('fade_out', 0)
        if fade_in > 0: final_clip = final_clip.fadein(duration=fade_in); logger.debug(f"Fade In: {fade_in}s")
        if fade_out > 0: final_clip = final_clip.fadeout(duration=fade_out); logger.debug(f"Fade Out: {fade_out}s")

        return final_clip

    def _distribute_effects_per_clip(self, effects_ui: List[tuple], num_clips: int) -> List[Optional[List[tuple]]]:
        """
        Distribuye los efectos seleccionados entre los clips disponibles.
        
        Por ejemplo, si tienes efectos [zoom_in, zoom_out] y 4 clips:
        - Clip 1: zoom_in
        - Clip 2: zoom_out  
        - Clip 3: zoom_in
        - Clip 4: zoom_out
        """
        if not effects_ui or num_clips <= 0:
            return None
            
        effects_per_clip = []
        
        for i in range(num_clips):
            if effects_ui:
                # Ciclar entre los efectos disponibles
                effect_index = i % len(effects_ui)
                selected_effect = effects_ui[effect_index]
                
                # Cada clip tendrá una lista con un solo efecto
                effects_per_clip.append([selected_effect])
            else:
                effects_per_clip.append(None)
        
        return effects_per_clip

    def _distribute_overlays_per_clip(self, overlays_ui: List[tuple], num_clips: int) -> List[Optional[List[tuple]]]:
        """
        Distribuye los overlays seleccionados entre los clips disponibles.
        
        Por ejemplo, si tienes overlays [sunlight-lens.webm, super8.webm] y 4 clips:
        - Clip 1: sunlight-lens.webm
        - Clip 2: super8.webm  
        - Clip 3: sunlight-lens.webm
        - Clip 4: super8.webm
        """
        if not overlays_ui or num_clips <= 0:
            return None
            
        overlays_per_clip = []
        
        for i in range(num_clips):
            if overlays_ui:
                # Ciclar entre los overlays disponibles
                overlay_index = i % len(overlays_ui)
                selected_overlay = overlays_ui[overlay_index]
                
                # Cada clip tendrá una lista con un solo overlay
                overlays_per_clip.append([selected_overlay])
            else:
                overlays_per_clip.append(None)
        
        return overlays_per_clip
