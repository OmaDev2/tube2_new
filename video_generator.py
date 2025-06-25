# video_generator.py
import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from datetime import datetime

import moviepy.editor as mp
import numpy as np

from utils.config import load_config
from utils.ai_services import AIServices
from utils.scene_generator import SceneGenerator
from utils.subtitle_utils import create_subtitle_clips
from utils.audio_services import generate_edge_tts_audio
from utils.video_services import VideoServices
from utils.transcription_services import TranscriptionService

# Configuración básica del logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class VideoBuilder:
    """
    Clase principal para construir y procesar videos con IA y recursos personalizados
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Inicializa VideoBuilder con configuración opcional
        
        Args:
            config: Configuración para el generador de videos
        """
        self.config = config or load_config()
        self._init_services()

    def _init_services(self):
        """Inicializa todos los servicios necesarios una sola vez"""
        self.scene_generator = SceneGenerator()
        self.video_service = VideoServices()
        self.ai_service = AIServices()
        self.transcription_service = TranscriptionService()
        
        # Rutas importantes
        self.projects_path = Path(self.config.get("projects_folder", "projects"))
        self.output_path = Path(self.config.get("output_folder", "output"))
        self.templates_path = Path(self.config.get("templates_folder", "templates"))

    def build_video_from_text(self, text: str, config: Dict) -> Path:
        """
        Construye un video completo desde texto
        
        Args:
            text: Texto de entrada para generar el video
            config: Configuración para este video
        
        Returns:
            Ruta al video resultante
        """
        try:
            # Crear proyecto
            project = self.create_video_project(text, config)
            
            # Generar partes del video
            script_provided = "script" in config
            audio_provided = "audio_path" in config
            
            if not script_provided:
                project = self.generate_script(project, config)
            
            if not audio_provided:
                project = self.generate_audio(project, config)
                
            project = self.generate_images(project, config)
            return self.assemble_video(project, config)
            
        except Exception as e:
            logger.error(f"Fallo al construir video: {e}", exc_info=True)
            raise

    def create_video_project(self, content: Union[str, Path], config: Dict) -> Dict:
        """
        Crea un nuevo proyecto de video con estructura base
        
        Args:
            content: Contenido para el proyecto (texto o ruta)
            config: Configuración para este proyecto
            
        Returns:
            Información del proyecto
        """
        # Determinar el título del proyecto
        title = config.get("title")
        if not title and isinstance(content, str) and len(content) > 20:
            title = content[:50].strip() + "..." if len(content) > 50 else content
        
        # Crear directorio base
        project_id = f"{title.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        project_path = self.projects_path / project_id
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Estructura básica del proyecto
        project_info = {
            "id": project_id,
            "title": title,
            "description": config.get("description", "Sin descripción"),
            "content": str(content)[:100] + "..." if isinstance(content, str) else str(content),
            "created_at": datetime.now().isoformat(),
            "status": "iniciando",
            "base_path": str(project_path),
            "content_type": config.get("content_type", "text"),
            "use_existing": config.get("use_existing", False),
            "source": config.get("source", "manual"),
            "script_prompts": config.get("script_prompts"),
            "image_prompts": config.get("image_prompts")
        }
        
        # Subdirectorios
        for subfolder in ["audio", "images", "video"]:
            (project_path / subfolder).mkdir(exist_ok=True)
        
        # Guardar info del proyecto
        self._save_project_info(project_path, project_info)
        logger.info(f"Proyecto creado en {project_path}")
        return project_info

    def _save_project_info(self, folder: Path, project_info: Dict):
        """Guarda información del proyecto en JSON"""
        try:
            with open(folder / "project_info.json", 'w', encoding='utf-8') as f:
                json.dump(project_info, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"No se pudo guardar la información del proyecto: {e}")

    def generate_script(self, project_info: Dict, config: Dict) -> Dict:
        """
        Genera un guion a partir del contexto usando IA
        
        Args:
            project_info: Información del proyecto
            config: Configuración para este proceso
            
        Returns:
            Información del proyecto actualizada
        """
        try:
            script_path = Path(project_info["base_path"]) / "script.txt"
            
            # Si ya existe y se permite usarlo, devolver
            if project_info.get("use_existing") and script_path.exists():
                logger.info(f"Usando guion existente: {script_path}")
                with open(script_path, "r", encoding="utf-8") as f:
                    project_info["script"] = f.read()
                return project_info
            
            # Usar el modo del proyecto (desde session_state o config)
            script_mode = config.get("script_mode", "IA")
            project_info["script_mode"] = script_mode
            
            # Para modo manual, usar texto directamente
            if script_mode == "Manual":
                manual_script = config.get("manual_script")
                if not manual_script:
                    raise ValueError("Falta el guion manual para este proyecto")
                
                with open(script_path, "w", encoding="utf-8") as f:
                    f.write(manual_script)
                
                project_info["script_path"] = str(script_path)
                project_info["script_size"] = len(manual_script)
                project_info["script_source"] = "manual"
                project_info["script"] = manual_script
                return project_info
            
            # Para modo IA, usar el prompt seleccionado
            prompt_obj = config.get("script_prompt_obj")
            if not prompt_obj:
                raise ValueError("Falta la plantilla de prompt para generar guion")
            
            # Construir prompt con variables
            user_prompt = prompt_obj.get("user_prompt", "")
            user_prompt = user_prompt.format(
                titulo=project_info["titulo"],
                contexto=project_info.get("contexto", "")
            )
            
            # Generar contenido con IA
            generated_script = self.ai_service.generate_content(
                provider=config.get("provider_ia", "OpenAI"),
                model=config.get("model_ia", "gpt-3.5-turbo"),
                prompt=user_prompt
            )
            
            # Guardar el guion generado
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(generated_script)
            
            # Actualizar info del proyecto
            project_info["script_path"] = str(script_path)
            project_info["script_size"] = len(generated_script)
            project_info["script_source"] = "generated"
            project_info["script_prompt_used"] = prompt_obj.get("nombre", "none")
            project_info["script"] = generated_script
            
            return project_info
        
        except Exception as e:
            logger.error(f"Error generando guion: {e}")
            raise

    def generate_audio(self, project_info: Dict, config: Dict) -> Dict:
        """
        Genera audio a partir del guion usando TTS
        
        Args:
            project_info: Información del proyecto
            config: Configuración para este proceso
            
        Returns:
            Información del proyecto actualizada
        """
        try:
            audio_path = Path(project_info["base_path"]) / "audio_final.mp3"
            
            # Si ya existe y se permite usarlo, devolver
            if project_info.get("use_existing") and audio_path.exists():
                logger.info(f"Usando audio existente: {audio_path}")
                project_info["audio_path"] = str(audio_path)
                return project_info
            
            # Load script content
            with open(project_info["script_path"], "r", encoding="utf-8") as f:
                script_content = f.read()
            
            # Split into chunks for EdgeTTS (max 1000 chars)
            chunks = [script_content[i:i+999] for i in range(0, len(script_content), 999)]
            audio_files = []
            
            # Generate audio for each chunk
            for idx, chunk in enumerate(chunks):
                chunk_file = Path(project_info["base_path"]) / "audio" / f"audio_part{idx}.mp3"
                audio_files.append(chunk_file)
                
                # Only generate if file doesn't exist yet
                if not chunk_file.exists() or idx == 0:
                    logger.info(f"Generando audio para parte {idx+1}...")
                    generate_edge_tts_audio(
                        text=chunk,
                        voice=config.get("tts_voice", "es-ES-AlvaroNeural"),
                        rate=f"{config.get('tts_speed_percent', -5):+d}%",
                        pitch=f"{config.get('tts_pitch_hz', -5):+d}Hz",
                        volume=f"{config.get('tts_volume', 1.0):.2f}",
                        output_file=chunk_file
                    )
            
            # Combine all chunks into single audio file
            if audio_files:
                combined = self.video_service.combine_audio(audio_files)
                if combined is not None:
                    combined.write_audiofile(str(audio_path), codec="mp3")
                    
                # Clean up intermediate files
                for file in audio_files:
                    if file.exists() and file != audio_path:
                        file.unlink()
            
            # Update project info
            project_info["audio_path"] = str(audio_path)
            project_info["audio_length"] = mp.AudioFileClip(str(audio_path)).duration
            project_info["audio_source"] = "edge_tts"
            
            return project_info
        
        except Exception as e:
            logger.error(f"Error generando audio: {e}")
            raise

    def generate_images(self, project_info: Dict, config: Dict) -> Dict:
        """
        Genera imágenes para cada escena del guion
        
        Args:
            project_info: Información del proyecto
            config: Configuración para este proceso
            
        Returns:
            Información del proyecto actualizada
        """
        try:
            # Check if using existing images
            existing_images = project_info.get("image_paths", [])
            if project_info.get("use_existing") and existing_images:
                logger.info(f"Usando {len(existing_images)} imágenes existentes")
                return project_info
            
            # Load script content
            with open(project_info["script_path"], "r", encoding="utf-8") as f:
                script_content = f.read()
            
            # Generate scene structure
            scenes = self.scene_generator.split_scene_descriptions(
                text=script_content,
                scenes_min_words=150
            )
            
            # --- AÑADIR ESTA LÍNEA DE DEBUG ---
            logger.info(f"Número de escenas generadas: {len(scenes)}")
            if not scenes:
                logger.warning("No se generó ninguna escena a partir del guion. Revisa el contenido del script y la lógica de SceneGenerator.")
            # ------------------------------------
            
            # Update project info with scene count
            project_info["scene_count"] = len(scenes)
            scenes_path = Path(project_info["base_path"]) / "scenes.json"
            project_info["scenes_path"] = str(scenes_path)
            
            # Save scenes metadata
            with open(scenes_path, "w", encoding="utf-8") as f:
                json.dump(scenes, f, indent=2, ensure_ascii=False)
            
            # Generate images for each scene
            image_paths = []
            for idx, scene in enumerate(scenes):
                # Build image request from prompt
                image_request = self._build_image_request(config, scene)
                image_path = Path(project_info["base_path"]) / "images" / f"scene_{idx:03d}.webp"
                
                # Only generate if not exists
                if not image_path.exists():
                    logger.info(f"Generando imagen para escena {idx+1}: {scene['title']}")
                    image_path = self._generate_single_image(config, image_request, image_path)
                
                if image_path and image_path.exists():
                    image_paths.append(str(image_path))
            
            # Update project info
            project_info["image_paths"] = image_paths
            project_info["images_generated"] = True
            
            return project_info
        
        except Exception as e:
            logger.error(f"Error generando imágenes: {e}")
            raise

    def _build_image_request(self, config: Dict, scene: Dict) -> Dict:
        """Construye la solicitud de imagen usando el prompt seleccionado"""
        prompt_obj = config.get("image_prompt_obj", {})
        
        # Variables para el prompt
        template_vars = {
            "scene_text": scene["description"],
            "titulo": config.get("title", ""),
            "contexto": config.get("context", "")
        }
        
        # Construir usando plantilla
        if prompt_obj.get("prompt_type") == "full":
            user_prompt = prompt_obj.get("user_prompt", "").format(**template_vars)
        else:
            # Por defecto, simplemente combinar texto básico
            user_prompt = f"{scene['description']}. {config.get('img_style', '')}"
        
        return {
            "prompt": user_prompt,
            "negative_prompt": "low quality, blurry, cartoonish, \"\"\"",  # Filter out quotes
            "model": config.get("img_model", "black-forest-labs/flux-schnell"),
            "aspect_ratio": config.get("img_aspect_ratio", "1:1")
        }

    def _generate_single_image(self, config: Dict, request: Dict, output_path: Path) -> Optional[Path]:
        """Genera una imagen usando el API seleccionado"""
        try:
            # --- AÑADE ESTE LOG PARA VER QUÉ SE ENVÍA ---
            logger.info(f"Enviando solicitud de imagen al proveedor {config.get('img_provider', 'Replicate')} con el prompt: '{request['prompt'][:100]}...'")
            # -------------------------------------------

            output = self.ai_service.generate_image(
                provider=config.get("img_provider", "Replicate"),
                prompt=request["prompt"],
                negative_prompt=request.get("negative_prompt", ""),
                model=request["model"],
                aspect_ratio=request.get("aspect_ratio", "1:1"),
                output_format=config.get("img_output_format", "webp"),
                output_quality=config.get("img_output_quality", 85)
            )

            # --- AÑADE ESTE LOG PARA VER QUÉ SE RECIBE ---
            logger.info(f"Respuesta recibida de la API de imagen: {output}")
            # --------------------------------------------
            
            if output:
                # --- LÓGICA MEJORADA PARA MANEJAR RESPUESTAS ---
                if isinstance(output, str):
                    if output.startswith('http://') or output.startswith('https://'):
                        # Es una URL, descarguemos la imagen
                        logger.info(f"Respuesta es una URL. Descargando imagen desde {output}")
                        import requests
                        response = requests.get(output)
                        response.raise_for_status() # Lanza un error si la descarga falla
                        image_path = output_path
                        with open(image_path, 'wb') as f:
                            f.write(response.content)
                        return image_path
                    elif os.path.isfile(output):
                        # Es una ruta de archivo local
                        image_path = output_path.with_suffix(Path(output).suffix)
                        os.rename(output, image_path)
                        return image_path
                elif hasattr(output, 'save'):
                    # Es un objeto de imagen (ej. PIL)
                    image_path = output_path
                    output.save(image_path)
                    return image_path
                
                # Si llegamos aquí, el formato no es soportado
                raise ValueError(f"Formato de salida no soportado o ruta no válida: {output}")
            
            return None
        
        except Exception as e:
            logger.error(f"Error generando imagen con prompt '{request['prompt'][:100]}...': {e}", exc_info=True)
            raise

    def assemble_video(self, project_info: Dict, config: Dict) -> Path:
        """
        Combina todas las partes para crear el video final
        
        Args:
            project_info: Información del proyecto
            config: Configuración para este proceso
            
        Returns:
            Ruta al video final
        """
        try:
            # Paths
            video_path = Path(project_info["base_path"]) / "video" / "final_video.mp4"
            audio_path = Path(project_info["audio_path"])
            image_paths = [Path(p) for p in project_info["image_paths"]]
            
            # Calcular duración de cada escena
            scene_durations = self._calculate_scene_durations(
                image_paths, 
                audio_path, 
                config.get("vid_duration", 60)
            )
            
            # Crear video desde imágenes
            logger.info("Creando video desde imágenes...")
            video_clip = self.video_service.create_video_from_images(
                image_paths=image_paths,
                durations=scene_durations,
                resolution=config.get("vid_resolution", "1920x1080"),
                transition=config.get("vid_transition", "fade"),
                transition_duration=config.get("vid_transition_duration", 1.0)
            )
            
            # Aplicar audio
            if audio_path.exists():
                logger.info("Aplicando audio al video...")
                audio_clip = mp.AudioFileClip(str(audio_path))
                
                # Ajustar volumen si se necesita
                if config.get("tts_volume", 1.0) != 1.0:
                    audio_clip = audio_clip.volumex(config["tts_volume"])
                    
                # Si hay música de fondo, aplicar
                if config.get("vid_bg_music_selection"):
                    music_path = Path(config["vid_bg_music_selection"])
                    if music_path.exists():
                        bg_music = mp.AudioFileClip(str(music_path))
                        bg_music = bg_music.volumex(config.get("vid_music_volume", 0.08))
                        bg_music = bg_music.loop(duration=video_clip.duration) if config.get("vid_music_loop", True) else bg_music.subclip(0, video_clip.duration)
                        
                        # Aplicar crossfade entre la música y el audio del narrador
                        bg_music = bg_music.set_start(0)
                        final_audio = mp.CompositeAudioClip([audio_clip, bg_music]).set_duration(video_clip.duration)
                    else:
                        logger.warning(f"No se encontró la pista de música: {music_path}")
                        final_audio = audio_clip
                else:
                    final_audio = audio_clip
                
                # Aplicar fades
                if config.get("vid_fade_in", 0) > 0:
                    final_audio = final_audio.fadein(config["vid_fade_in"])
                if config.get("vid_fade_out", 0) > 0:
                    final_audio = final_audio.fadeout(config["vid_fade_out"])
                    
                video_clip = video_clip.set_audio(final_audio)
            
            # Aplicar efectos de video
            if config.get("vid_overlays"):
                logger.info("Aplicando efectos de video...")
                for overlay in config["vid_overlays"]:
                    logger.info(f"Aplicando overlay: {overlay['name']}")
                    video_clip = self.video_service.apply_overlay(
                        video_clip, 
                        overlay["path"], 
                        overlay.get("opacity", 0.3),
                        overlay.get("position", "center"),
                        overlay.get("loop", True)
                    )
            
            # Aplicar subtítulos
            if config.get("vid_subtitles", False):
                logger.info("Añadiendo subtítulos...")
                subtitle_clips = create_subtitle_clips(
                    srt_file=Path(project_info["base_path"]) / "subtitles.srt",
                    video_width=video_clip.w,
                    font=config.get("vid_subtitle_font", "Arial"),
                    fontsize=config.get("vid_subtitle_fontsize", 24),
                    color=config.get("vid_subtitle_color", "white"),
                    outline_color=config.get("vid_subtitle_outline_color", "black"),
                    position=config.get("vid_subtitle_position", "bottom")
                )
                video_clip = self.video_service.add_subtitles(video_clip, subtitle_clips)
            
            # Guardar video final
            logger.info(f"Guardando video final: {video_path}")
            video_clip.write_videofile(
                str(video_path),
                fps=24,
                codec=config.get("vid_codec", "libx264"),
                audio_codec=config.get("vid_audio_codec", "aac"),
                bitrate=config.get("vid_bitrate", "5000k"),
                audio_bitrate=config.get("vid_audio_bitrate", "192k"),
                preset=config.get("vid_preset", "fast"),
                threads=config.get("vid_threads", 4)
            )
            
            # Actualizar info del proyecto
            project_info["video_path"] = str(video_path)
            project_info["video_length"] = video_clip.duration
            project_info["status"] = "completado"
            self._save_project_info(Path(project_info["base_path"]), project_info)
            
            return video_path
        
        except Exception as e:
            logger.error(f"Error ensamblando video: {e}")
            project_info["status"] = "fallido"
            project_info["error"] = str(e)
            self._save_project_info(Path(project_info["base_path"]), project_info)
            raise

    def _calculate_scene_durations(self, image_paths: List[Path], audio_path: Path, total_duration: float) -> List[float]:
        """Calcula la duración para cada escena"""
        if not image_paths:
            return []
        
        # Si hay audio, sincronizar con él
        if audio_path.exists():
            audio_clip = mp.AudioFileClip(str(audio_path))
            total_duration = audio_clip.duration
        
        # Dividir equitativamente
        image_count = len(image_paths)
        return [total_duration/image_count] * image_count

    def process_batch(self, projects: List[Dict], batch_config: Dict) -> List[Dict]:
        """
        Procesa una lista de proyectos secuencialmente
        
        Args:
            projects: Lista de proyectos a procesar
            batch_config: Configuración para el procesamiento en lote
            
        Returns:
            Lista de proyectos procesados
        """
        processed_projects = []
        
        for i, project in enumerate(projects):
            try:
                logger.info(f"Procesando proyecto {i+1}/{len(projects)}: {project.get('title', 'Sin título')}")
                project_config = {**batch_config, **project}
                video_path = self.build_video_from_text(project.get("content", ""), project_config)
                project["video_path"] = str(video_path)
                project["status"] = "completado"
            except Exception as e:
                logger.error(f"Error procesando proyecto {project.get('title')}: {e}")
                project["status"] = "fallido"
                project["error"] = str(e)
            finally:
                processed_projects.append(project)
        
        return processed_projects