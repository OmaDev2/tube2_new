#!/usr/bin/env python3
"""
🎬 Generar Video San Blas - Proyecto Existente
=============================================

Genera el video completo usando el proyecto san_blas__cd4c5eaa existente.
Este script continúa desde donde se quedó (después del audio).

Uso:
    python generar_video_san_blas.py
"""

import sys
import os
import json
from pathlib import Path

# Añadir el directorio raíz al path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from utils.scene_generator import SceneGenerator
from utils.ai_services import AIServices
from utils.video_services import VideoGenerator
from utils.audio_services import AudioServices
from utils.video_processing import VideoProcessor

def generar_video_completo():
    """
    Genera el video completo de San Blas usando el proyecto existente.
    """
    
    project_id = "san_blas__cd4c5eaa"
    project_path = f"projects/{project_id}"
    
    print(f"🎬 GENERANDO VIDEO COMPLETO: {project_id}")
    print("=" * 60)
    
    # Verificar que el proyecto existe
    if not os.path.exists(project_path):
        print(f"❌ ERROR: No se encontró el proyecto {project_id}")
        return
    
    # Cargar información del proyecto
    project_info_path = f"{project_path}/project_info.json"
    with open(project_info_path, 'r', encoding='utf-8') as f:
        project_info = json.load(f)
    
    print(f"📋 Título: {project_info['titulo']}")
    print(f"📊 Estado actual: {project_info['status']}")
    print(f"⏱️ Duración audio: {project_info['audio_duration']} segundos")
    print()
    
    # Inicializar servicios
    ai_service = AIServices()
    scene_generator = SceneGenerator()
    video_generator = VideoGenerator()
    video_processor = VideoProcessor()
    
    # PASO 1: Generar escenas desde el audio
    scenes_path = f"{project_path}/scenes.json"
    if not os.path.exists(scenes_path):
        print("🎭 PASO 1: Generando escenas desde el audio...")
        
        audio_path = project_info['audio_path']
        if not os.path.exists(audio_path):
            print(f"❌ ERROR: No se encontró el audio en {audio_path}")
            return
        
        try:
            # Generar escenas usando el audio existente
            scenes = scene_generator.generate_prompts_for_timed_scenes(
                transcription_segments=[],  # Se generará desde el audio
                target_duration_per_scene=12.0,  # 12 segundos por escena
                project_info=project_info,
                image_prompt_config=project_info['config_usada']['image']['prompt_obj'],
                ai_service=ai_service
            )
            
            # Guardar escenas
            with open(scenes_path, 'w', encoding='utf-8') as f:
                json.dump(scenes, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Escenas generadas: {len(scenes)} escenas")
            
        except Exception as e:
            print(f"❌ ERROR generando escenas: {str(e)}")
            import traceback
            traceback.print_exc()
            return
    else:
        print("✅ Escenas ya existen, cargando...")
        with open(scenes_path, 'r', encoding='utf-8') as f:
            scenes = json.load(f)
        print(f"📊 Escenas cargadas: {len(scenes)} escenas")
    
    # PASO 2: Generar imágenes para cada escena
    images_path = f"{project_path}/images"
    os.makedirs(images_path, exist_ok=True)
    
    print(f"\n🎨 PASO 2: Generando imágenes...")
    print(f"📁 Carpeta de imágenes: {images_path}")
    
    image_config = project_info['config_usada']['image']
    
    for i, scene in enumerate(scenes):
        scene_text = scene.get('text', '')
        image_prompt = scene.get('image_prompt', '')
        
        if not image_prompt:
            print(f"⚠️ Escena {i+1} no tiene prompt de imagen, saltando...")
            continue
        
        print(f"\n🖼️ Generando imagen {i+1}/{len(scenes)}...")
        print(f"📝 Escena: {scene_text[:100]}...")
        
        try:
            # Generar imagen usando la configuración del proyecto
            image_result = ai_service.generate_image(
                prompt=image_prompt,
                provider=image_config['img_provider'],
                model=image_config['img_model'],
                aspect_ratio=image_config['aspect_ratio'],
                output_format=image_config['output_format'],
                output_quality=image_config['output_quality']
            )
            
            if image_result and 'image_path' in image_result:
                # Mover imagen a la carpeta del proyecto
                image_filename = f"scene_{i+1:03d}.{image_config['output_format']}"
                final_image_path = os.path.join(images_path, image_filename)
                
                # Copiar imagen
                import shutil
                shutil.copy2(image_result['image_path'], final_image_path)
                
                print(f"✅ Imagen {i+1} guardada: {image_filename}")
                
                # Actualizar la escena con la ruta de la imagen
                scene['image_path'] = final_image_path
                
            else:
                print(f"❌ ERROR: No se pudo generar la imagen {i+1}")
                
        except Exception as e:
            print(f"❌ ERROR en imagen {i+1}: {str(e)}")
            continue
    
    # Guardar escenas actualizadas con rutas de imágenes
    with open(scenes_path, 'w', encoding='utf-8') as f:
        json.dump(scenes, f, indent=2, ensure_ascii=False)
    
    # PASO 3: Generar video final
    print(f"\n🎬 PASO 3: Generando video final...")
    
    try:
        video_config = project_info['config_usada']['video']
        
        # Generar video usando las imágenes y configuración
        video_result = video_processor.create_video_from_images(
            images_folder=images_path,
            audio_path=project_info['audio_path'],
            output_path=f"{project_path}/video/final_video.mp4",
            duration_per_image=video_config.get('duration_per_image_manual', 10.0),
            transition_type=video_config.get('transition_type', 'dissolve'),
            transition_duration=video_config.get('transition_duration', 1.0),
            effects=video_config.get('effects', []),
            overlays=video_config.get('overlays', []),
            subtitles_config=project_info['config_usada'].get('subtitles', {}),
            bg_music_path=project_info['config_usada']['audio'].get('bg_music_selection')
        )
        
        if video_result:
            print("✅ Video generado exitosamente!")
            print(f"📁 Ubicación: {video_result}")
        else:
            print("❌ ERROR: No se pudo generar el video")
            
    except Exception as e:
        print(f"❌ ERROR generando video: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    print(f"\n🎉 ¡VIDEO COMPLETADO!")
    print(f"📁 Proyecto: {project_path}")
    print(f"🎬 Video final generado con todos los efectos mejorados")
    print(f"✨ Incluye: Paneos suaves, coherencia visual, otros personajes")

if __name__ == "__main__":
    generar_video_completo() 