import json
from pathlib import Path
from utils.video_processing import VideoProcessor
from utils.config import load_config
import logging

# Configurar logging para ver los mensajes del proceso
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def regenerate_from_transcription(project_id: str):
    """
    Regenera un video para un proyecto existente, comenzando desde la transcripción.
    Asume que project_info.json, script.txt, audio.mp3 y transcription.json ya existen.
    """
    project_folder_path = Path(f"./projects/{project_id}")
    project_info_path = project_folder_path / "project_info.json"
    transcription_path = project_folder_path / "transcription.json"
    script_path = project_folder_path / "script.txt"
    # 1. Cargar project_info existente
    if not project_info_path.exists():
        logger.error(f"Error: project_info.json no encontrado en {project_info_path}")
        return
    with open(project_info_path, 'r', encoding='utf-8') as f:
        existing_project_info = json.load(f)

    # Obtener la ruta del audio desde el project_info
    audio_path_str = existing_project_info.get("audio_path")
    if not audio_path_str:
        logger.error("Error: La clave 'audio_path' no se encontró en project_info.json")
        return
    
    # Convertir a Path y verificar existencia. Asumimos que la ruta en el JSON es relativa al root del proyecto.
    audio_path = Path(audio_path_str)
    if not audio_path.exists():
        logger.error(f"Error: El archivo de audio especificado en project_info.json no existe: {audio_path}")
        return

    # Validar que los otros archivos necesarios existan
    if not transcription_path.exists():
        logger.error(f"Error: transcription.json no encontrado en {transcription_path}")
        return
    if not script_path.exists():
        logger.error(f"Error: script.txt no encontrado en {script_path}")
        return

    # 2. Asegurarse de que las rutas en project_info sean correctas y absolutas para el procesador
    existing_project_info["base_path"] = str(project_folder_path.resolve())
    existing_project_info["script_path"] = str(script_path.resolve())
    existing_project_info["audio_path"] = str(audio_path.resolve())
    existing_project_info["transcription_path"] = str(transcription_path.resolve())

    # 3. Cargar la configuración general de la aplicación
    logger.info("Cargando configuración de la aplicación...")
    app_config = load_config()
    logger.info("Configuración de la aplicación cargada.")

    # 4. Preparar un full_config para process_single_video, usando la configuración guardada
    full_config = existing_project_info.get("config_usada", {})
    logger.info("Configuración específica del proyecto preparada.")
    
    # Asegurar que las claves principales existen para evitar errores
    full_config.setdefault("script", {})
    full_config.setdefault("audio", {})
    full_config.setdefault("scenes_config", {})
    full_config.setdefault("image", {})
    full_config.setdefault("video", {})
    full_config.setdefault("subtitles", {})

    # --- MODIFICACIÓN PARA CARGAR Y APLICAR EL PROMPT "Foto_Jona" ---
    # (Esta lógica parece útil para forzar un estilo, la mantenemos)
    try:
        logger.info("Intentando aplicar prompt 'Foto_Jona'...")
        prompts_file_path = Path("./prompts/imagenes_prompts.json")
        if prompts_file_path.exists():
            with open(prompts_file_path, 'r', encoding='utf-8') as f:
                all_image_prompts = json.load(f)
            
            jona_prompt_obj = next((p for p in all_image_prompts if p.get("nombre") == "Foto_Jona"), None)
            
            if jona_prompt_obj:
                full_config["image"]["prompt_obj"] = jona_prompt_obj
                logger.info("Prompt 'Foto_Jona' aplicado exitosamente a la configuración de imagen.")
            else:
                logger.warning("El prompt 'Foto_Jona' no se encontró en imagenes_prompts.json.")
        else:
            logger.warning(f"Archivo de prompts no encontrado en {prompts_file_path}, se usará el del project_info si existe.")

    except Exception as e:
        logger.error(f"Error al cargar o aplicar el prompt 'Foto_Jona': {e}")
    # --- FIN DE LA MODIFICACIÓN ---

    # 5. Inicializar VideoProcessor
    logger.info("Inicializando VideoProcessor...")
    processor = VideoProcessor(config=app_config)
    logger.info("VideoProcessor inicializado.")

    logger.info(f"Iniciando regeneración para el proyecto {project_id}...")
    # Llamamos al procesador con la info y config cargadas
    final_video_path = processor.process_single_video(full_config, existing_project_info)

    if final_video_path:
        logger.info(f"Regeneración completada. Video final en: {final_video_path}")
    else:
        logger.error(f"Regeneración fallida para el proyecto {project_id}.")

# --- EJEMPLO DE USO ---
if __name__ == "__main__":
    # Cambiado al ID de proyecto correcto
    project_to_regenerate = "santa_teresa_de_lisieux__70c3d055" 
    regenerate_from_transcription(project_to_regenerate)