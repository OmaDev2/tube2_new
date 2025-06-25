# pages/generator_utils.py
import json
import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st
from PIL import Image
import moviepy.editor as mp

class ProjectManager:
    """Gestiona operaciones comunes para proyectos de video"""
    
    AI_PROVIDERS = ["OpenAI", "Gemini", "Ollama", "Claude", "DeepSeek"]
    DEFAULT_VIDEO_DURATION = 60
    DEFAULT_MODEL = {
        "OpenAI": "gpt-4o",
        "Gemini": "gemini-pro",
        "Ollama": "llama2:7b"
    }
    
    # Rutas de proyecto
    BASE_DIR = Path("projects")
    SAMPLES_DIR = Path("samples")
    TEMPLATES_DIR = Path("templates")
    DEFAULT_MUSIC = "background_music/Yoga Style - Chris Haugen.mp3"

    def __init__(self, app_config=None):
        self.app_config = app_config or {}
        self.current_project = None
        self._ensure_directories()

    def _ensure_directories(self):
        """Asegura que existen las carpetas necesarias"""
        self.BASE_DIR.mkdir(exist_ok=True)
        self.SAMPLES_DIR.mkdir(exist_ok=True)
        self.TEMPLATES_DIR.mkdir(exist_ok=True, parents=True)

    def create_project(self, title=None, description=None, project_type="video"):
        """Crea un nuevo proyecto con estructura básica"""
        try:
            project_id = f"{title}_{uuid.uuid4().hex[:8]}" if title else f"project_{uuid.uuid4().hex}"
            project_path = self.BASE_DIR / project_id
            project_path.mkdir(exist_ok=True)
            
            # Subdirectorios del proyecto
            (project_path / "audio").mkdir(exist_ok=True)
            (project_path / "images").mkdir(exist_ok=True)
            (project_path / "video").mkdir(exist_ok=True)
            
            # Información básica del proyecto
            project_info = {
                "id": project_id,
                "title": title or "Proyecto sin título",
                "description": description or "Sin descripción",
                "created_at": datetime.now().isoformat(),
                "project_type": project_type,
                "last_modified": datetime.now().isoformat(),
                "base_path": str(project_path),
                "image_paths": [],
                "audio_path": None,
                "script_path": None,
                "transcription_path": None,
                "video_path": None,
                "status": "iniciado"
            }
            
            self.save_project_info(project_path, project_info)
            self.current_project = project_info
            return project_info
            
        except Exception as e:
            st.error(f"Error al crear proyecto: {e}")
            return None

    def save_project_info(self, path, project_info):
        """Guarda información del proyecto en JSON"""
        try:
            info_path = path / "project_info.json"
            # Convertir rutas a strings
            project_info["last_modified"] = datetime.now().isoformat()
            project_info["base_path"] = str(path)
            
            with open(info_path, "w", encoding="utf-8") as f:
                json.dump(project_info, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            st.warning(f"No se pudo guardar la información del proyecto: {e}")

    def load_project_info(self, project_id):
        """Carga información de un proyecto guardado"""
        project_path = self.BASE_DIR / project_id
        info_path = project_path / "project_info.json"
        
        if info_path.exists():
            with open(info_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def update_project_info(self, project_info):
        """Actualiza información del proyecto con cambios"""
        try:
            project_path = Path(project_info["base_path"])
            self.save_project_info(project_path, project_info)
        except Exception as e:
            st.warning(f"Error actualizando información: {e}")

    def validate_project(self, project_info):
        """Revisa que el proyecto tenga todos sus componentes"""
        if not project_info.get("project_type"):
            raise ValueError("Tipo de proyecto no especificado")
        
        if not project_info.get("title"):
            raise ValueError("El título del proyecto es requerido")
        
        # Validar que existan los principales elementos
        required_paths = [
            project_info.get("audio_path"),
            project_info.get("script_path"),
            project_info.get("video_path")
        ]
        
        missing_paths = [p for p in required_paths if not p or not Path(p).exists()]
        if missing_paths and not project_info.get("use_existing", False):
            raise ValueError(f"Faltan archivos requeridos: {missing_paths}")

    def render_model_selector(self):
        """Renderiza el selector de modelo"""
        st.title("🧠 Modelo de Inteligencia Artificial")
        col1, col2 = st.columns(2)
        
        with col1:
            provider = st.selectbox("Proveedor", self.AI_PROVIDERS, key="ai_provider")
        
        with col2:
            model = st.text_input(
                "Modelo",
                self.app_config.get("default_model", self.DEFAULT_MODEL.get(provider, "gpt-3.5-turbo")),
                key="ai_model"
            )
        
        # Selector adicional de prompts (si se tienen)
        prompt_options = ["Guion", "Imágenes", "Ambos"]
        st.selectbox(
            "Plantillas de prompts",
            prompt_options,
            format_func=lambda x: {
                "Guion": "Guion para narrativa",
                "Imágenes": "Prompts para imágenes",
                "Ambos": "Guion e imágenes"
            }.get(x, x)
        )
        
        return {
            "provider": provider,
            "model": model
        }

    def calculate_durations(self, image_paths, total_duration=None, use_auto=True):
        """Calcula la duración para cada escena"""
        if not image_paths:
            return []
        
        total_duration = total_duration or self.DEFAULT_VIDEO_DURATION
        image_count = len(image_paths)

        # Si es manual, dividimos equitativamente
        if not use_auto:
            base_duration = total_duration / image_count
            return [base_duration] * image_count
            
        # TODO: Implementar cálculo automático avanzado basado en contenido
        # Por ahora, implementación básica
        return [total_duration/image_count] * image_count

    def apply_audio(self, video_clip, project_info):
        """Aplica efectos de audio al video"""
        try:
            audio_path = Path(project_info["audio_path"])
            if not audio_path.exists():
                raise ValueError("No existe el archivo de audio")
                
            # Cargar audio
            audio_clip = mp.AudioFileClip(project_info["audio_path"])
            
            # Ajustar volumen si se necesita
            if project_info.get("tts_volume", 1.0) != 1.0:
                audio_clip = audio_clip.volumex(project_info["tts_volume"])
                
            # Si hay música de fondo, aplicar
            if project_info.get("vid_bg_music_selection"):
                music_path = Path(project_info["vid_bg_music_selection"])
                if music_path.exists():
                    bg_music = mp.AudioFileClip(music_path)
                    bg_music = bg_music.volumex(project_info.get("vid_music_volume", 0.08))
                    bg_music = bg_music.loop(duration=video_clip.duration) if project_info.get("vid_music_loop", True) else bg_music.subclip(0, video_clip.duration)
                    
                    # Aplicar crossfade entre la música y el audio del narrador
                    bg_music = bg_music.set_start(0)
                    final_audio = mp.CompositeAudioClip([audio_clip, bg_music]).set_duration(video_clip.duration)
                else:
                    st.warning(f"No se encontró la pista de música: {music_path}")
                    final_audio = audio_clip
            else:
                final_audio = audio_clip
            
            # Aplicar fades
            if project_info.get("vid_fade_in", 0) > 0:
                final_audio = final_audio.fadein(project_info["vid_fade_in"])
            if project_info.get("vid_fade_out", 0) > 0:
                final_audio = final_audio.fadeout(project_info["vid_fade_out"])
                
            return video_clip.set_audio(final_audio)
        
        except Exception as e:
            st.warning(f"No se pudo aplicar el audio: {e}")
            return video_clip

    def process_video(self, project_info, image_paths, video_path):
        """Genera el video final usando las imágenes y audio"""
        try:
            # Validar información del proyecto
            self.validate_project(project_info)
            
            # Aplicar configuración de imágenes
            images_config = {
                "folder": project_info["base_path"],
                "paths": image_paths,
                "duration": project_info["duration"],
                "transition": project_info.get("transition", "fade"),
                "transition_duration": project_info.get("transition_duration", 1.0),
                "resolution": project_info.get("resolution", "1920x1080")
            }
            
            # Crear video desde imágenes
            st.info("Creando video desde imágenes...")

            # Aquí iría el video_service.create_video_from_images
            
            # Aplicar efectos de video
            if project_info.get("vid_overlays"):
                st.info("Aplicando efectos de video...")
                for overlay in project_info["vid_overlays"]:
                    st.info(f"Aplicando overlay: {overlay['name']}")
                    # Aquí iría overlay_service.apply(overlay)
            
            # Aplicar audio
            if project_info.get("audio_path"):
                st.info("Aplicando audio...")
                # Aquí iría el método apply_audio
                
                # Guardar video procesado
                processed_path = video_path.with_suffix(f".processed{video_path.suffix}")
                st.info(f"Guardando video procesado: {processed_path}")
                # Aquí iría el código para guardar el video final
            
            return video_path
            
        except Exception as e:
            project_info["status"] = "failed"
            project_info["error"] = str(e)
            st.error(f"Error en generación de video: {e}")
            return None

    def generate_project_from_text(self, input_text, project_info):
        """Genera un proyecto desde texto plano usando IA"""
        try:
            # Generar guion desde texto
            st.info("Generando guion desde texto...")
            # Aquí iría self.ai_service.generate_script
            
            # Dividir en escenas para imágenes
            st.info("Creando descripciones para imágenes...")
            # Aquí iría project_info["image_prompts"] = self.ai_service.split_into_scenes
            
            # Guardar script final
            script_path = Path(project_info["base_path"]) / "script.txt"
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(input_text)  # Simulando guion generado
                
            project_info["script_path"] = str(script_path)
            return project_info
            
        except Exception as e:
            st.error(f"Error generando proyecto desde texto: {e}")
            return None

    def render_project_loader(self):
        """Render para seleccionar proyecto existente"""
        st.markdown("### 🔍 Cargar Proyecto Existente")
        project_dirs = [d for d in self.BASE_DIR.iterdir() if d.is_dir()]
        
        if not project_dirs:
            st.info("No hay proyectos guardados disponibles")
            return None
        
        # Crear un selector con información legible
        project_options = {
            d.name: d for d in project_dirs
        }
        
        selected_project = st.selectbox(
            "Selecciona un proyecto", 
            options=list(project_options.keys())
        )
        
        if selected_project:
            selected_path = project_options[selected_project]
            try:
                # Cargar información del proyecto
                with open(selected_path / "project_info.json", "r", encoding="utf-8") as f:
                    project_data = json.load(f)
                
                st.session_state.loaded_project = project_data
                return project_data
            except Exception:
                st.error("No se pudo cargar el proyecto")
                return None
        return None

# Funciones de utilidad para interfaz de usuario
def format_duration(seconds):
    """Formatea duración para mostrar al usuario"""
    return f"{int(seconds // 60)}:{seconds % 60:02d}"

def format_path_size(path, digits=2):
    """Formatea tamaño de archivo para UI"""
    if path and path.exists():
        return f"{path.stat().st_size / (10**6):.{digits}f} MB"
    return "0.00 MB"

def display_file_info(path, name):
    """Muestra información de archivo en UI"""
    col1, col2 = st.columns(2)
    with col1:
        st.text(f"{name}: {format_path_size(path)}")
        st.text(f"Ubicación: {path}")
    with col2:
        if path:
            st.code(open(path).read()[:200] + "...", language="json")