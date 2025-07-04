#!/usr/bin/env python3
"""
Script para completar la transcripción del proyecto San Raimundo
"""
import json
import os
import sys
sys.path.append('.')

from utils.transcription_services import get_transcription_service
from utils.config import get_config

def fix_transcription():
    project_path = "projects/el_misterio_de_san_raimundo_y_el_milagro_de_cruzar__4990ace7"
    audio_file = os.path.join(project_path, "audio", "audio_fish_8604568204045335315.mp3")
    transcription_file = os.path.join(project_path, "transcription.json")
    
    print("🔧 REPARANDO TRANSCRIPCIÓN...")
    
    # Verificar que el archivo de audio existe
    if not os.path.exists(audio_file):
        print(f"❌ ERROR: No se encuentra el archivo de audio: {audio_file}")
        return False
    
    # Obtener configuración
    config = get_config()
    transcription_config = config.get('transcription', {})
    service_type = transcription_config.get('service', 'local')
    
    print(f"📋 Configuración actual:")
    print(f"  - Servicio: {service_type}")
    print(f"  - Archivo de audio: {audio_file}")
    print(f"  - Tamaño: {os.path.getsize(audio_file) / 1024 / 1024:.1f} MB")
    
    try:
        # Crear servicio de transcripción
        if service_type.lower() == 'replicate':
            print("🚀 Usando servicio Replicate...")
            transcription_service = get_transcription_service('replicate')
        else:
            print("🖥️ Usando servicio local...")
            transcription_service = get_transcription_service('local')
        
        # Función de progreso
        def progress_callback(progress, message):
            print(f"📊 {progress*100:.1f}% - {message}")
        
        # Realizar transcripción completa
        print("🎤 Iniciando transcripción completa...")
        segments, metadata = transcription_service.transcribe_audio(
            audio_file,
            language="es",
            progress_callback=progress_callback
        )
        
        # Guardar transcripción
        print("💾 Guardando transcripción...")
        transcription_service.save_transcription(
            segments, 
            metadata, 
            transcription_file
        )
        
        print(f"✅ Transcripción completada exitosamente!")
        print(f"  - Segmentos: {len(segments)}")
        print(f"  - Duración: {metadata.get('duration', 'N/A')} segundos")
        print(f"  - Idioma detectado: {metadata.get('language', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR durante la transcripción: {e}")
        return False

if __name__ == "__main__":
    success = fix_transcription()
    if not success:
        print("\n💡 SUGERENCIAS:")
        print("1. Verificar que el archivo de audio esté completo")
        print("2. Verificar la configuración de transcripción")
        print("3. Verificar que las API keys estén configuradas (si usas Replicate)")
        sys.exit(1)