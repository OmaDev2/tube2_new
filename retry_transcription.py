
import os
import logging
from pathlib import Path
from utils.transcription_services import get_transcription_service
from utils.ai_services import AIServices

# Configuración básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def retry_transcription_for_project():
    """
    Este script reintenta la transcripción para un proyecto específico
    donde el proceso de transcripción falló inicialmente.
    """
    project_id = "santa_teresa_de_lisieux__b980cc27"
    audio_filename = "audio_fish_4051771947239318890.mp3"
    
    # Construir las rutas absolutas
    base_dir = Path("/Users/olga/video_tube2 copia")
    project_dir = base_dir / "projects" / project_id
    audio_path = project_dir / "audio" / audio_filename
    output_path = project_dir / "transcription.json"

    logging.info(f"Iniciando reintento de transcripción para el proyecto: {project_id}")
    logging.info(f"Ruta del audio: {audio_path}")
    logging.info(f"Ruta de salida para la transcripción: {output_path}")

    if not audio_path.exists():
        logging.error(f"No se encontró el archivo de audio. Asegúrate de que la ruta es correcta: {audio_path}")
        return

    try:
        # --- Inicializar servicios ---
        logging.info("Inicializando servicios necesarios...")
        # Necesitamos AIServices para obtener el token de Replicate de forma segura
        ai_service = AIServices()
        replicate_token = ai_service.replicate_token

        if not replicate_token:
            logging.error("No se pudo encontrar el token de Replicate. Verifica la configuración.")
            return

        # Obtener el servicio de transcripción de Replicate
        transcription_service = get_transcription_service('replicate', api_token=replicate_token)
        logging.info("Servicio de transcripción de Replicate inicializado.")

        # --- Ejecutar transcripción ---
        logging.info("Iniciando la llamada a la API de Replicate. Esto puede tardar varios minutos para un audio de 47 minutos...")
        
        segments, metadata = transcription_service.transcribe_audio(
            audio_path=str(audio_path),
            language="es",
            timestamp="chunk" # 'chunk' es más robusto para archivos largos
        )

        if not segments:
            logging.error("La transcripción no devolvió segmentos. La API pudo haber fallado o el audio está en silencio.")
            logging.error(f"Metadatos recibidos: {metadata}")
            return

        logging.info(f"Transcripción completada. Se recibieron {len(segments)} segmentos.")

        # --- Guardar la transcripción ---
        logging.info(f"Guardando la transcripción en {output_path}...")
        transcription_service.save_transcription(segments, metadata, str(output_path))
        logging.info("¡Transcripción guardada exitosamente!")
        
        # --- Actualizar project_info.json ---
        project_info_path = project_dir / "project_info.json"
        if project_info_path.exists():
            import json
            with open(project_info_path, 'r+', encoding='utf-8') as f:
                project_info = json.load(f)
                project_info['transcription_path'] = str(output_path)
                project_info['status'] = 'transcription_ok' # Actualizar estado
                f.seek(0)
                json.dump(project_info, f, indent=2, ensure_ascii=False)
                f.truncate()
            logging.info("El archivo project_info.json ha sido actualizado.")

    except Exception as e:
        logging.error(f"Ocurrió un error durante el proceso de transcripción: {e}", exc_info=True)

if __name__ == "__main__":
    retry_transcription_for_project()
