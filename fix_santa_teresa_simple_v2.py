#!/usr/bin/env python3
"""
Script simple para arreglar el video de Santa Teresa de Ávila
Versión 2 - Simplificada
"""

import os
import sys
import json
import subprocess

def load_scenes(project_dir):
    """Cargar escenas desde scenes.json"""
    scenes_file = os.path.join(project_dir, "scenes.json")
    with open(scenes_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        return data.get('scenes', data) if isinstance(data, dict) else data

def get_audio_file(project_dir):
    """Obtener archivo de audio"""
    audio_dir = os.path.join(project_dir, "audio")
    for file in os.listdir(audio_dir):
        if file.endswith('.mp3'):
            return os.path.join(audio_dir, file)
    raise FileNotFoundError("No se encontró archivo de audio")

def get_image_files(project_dir):
    """Obtener lista de archivos de imagen ordenados"""
    images_dir = os.path.join(project_dir, "images")
    image_files = []
    for file in sorted(os.listdir(images_dir)):
        if file.endswith('.webp'):
            # Usar ruta absoluta completa
            full_path = os.path.abspath(os.path.join(images_dir, file))
            image_files.append(full_path)
    return image_files

def create_video_simple(project_dir, output_file="video_output.mp4"):
    """Crear video usando FFmpeg con rutas absolutas"""
    
    print("🔍 Analizando proyecto...")
    
    # Cargar datos
    scenes = load_scenes(project_dir)
    audio_file = get_audio_file(project_dir)
    image_files = get_image_files(project_dir)
    
    print(f"📊 Estadísticas:")
    print(f"   - Escenas en scenes.json: {len(scenes)}")
    print(f"   - Imágenes encontradas: {len(image_files)}")
    print(f"   - Audio: {os.path.basename(audio_file)}")
    
    if len(scenes) != len(image_files):
        print(f"⚠️  ADVERTENCIA: Número de escenas ({len(scenes)}) no coincide con imágenes ({len(image_files)})")
        print("   Usando el número menor para evitar errores...")
        num_scenes = min(len(scenes), len(image_files))
    else:
        num_scenes = len(scenes)
    
    # Crear archivo de lista de imágenes para FFmpeg
    concat_file = os.path.join(project_dir, "concat_fixed.txt")
    
    print(f"📝 Generando lista de concatenación...")
    
    with open(concat_file, 'w', encoding='utf-8') as f:
        for i in range(num_scenes):
            if i < len(image_files):
                # Calcular duración de la escena
                scene = scenes[i]
                duration = scene.get('duration', 2.0)  # Fallback a 2 segundos
                
                # Asegurar que la duración sea positiva
                if duration <= 0:
                    print(f"⚠️  Duración inválida en escena {i}: {duration}, usando 2.0s")
                    duration = 2.0
                
                # Usar rutas absolutas
                f.write(f"file '{image_files[i]}'\n")
                f.write(f"duration {duration}\n")
        
        # Agregar la última imagen una vez más (FFmpeg requiere esto)
        if image_files and num_scenes > 0:
            f.write(f"file '{image_files[num_scenes-1]}'\n")
    
    # Crear comando FFmpeg con rutas absolutas
    output_path = os.path.join(os.getcwd(), output_file)
    
    cmd = [
        'ffmpeg',
        '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_file,
        '-i', audio_file,
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-shortest',
        '-pix_fmt', 'yuv420p',
        output_path
    ]

    print(f"🎬 Comando FFmpeg:")
    print(f"   {' '.join(cmd)}")
    
    print(f"📁 Archivos:")
    print(f"   - Concat: {concat_file}")
    print(f"   - Audio: {audio_file}")
    print(f"   - Output: {output_path}")
    
    try:
        print("🚀 Ejecutando FFmpeg...")
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ Video generado exitosamente: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en FFmpeg:")
        print(f"   Código de salida: {e.returncode}")
        print(f"   Stderr: {e.stderr}")
        return None

def main():
    project_dir = "projects/santa_teresa_de_ávila__e23a5a4a"
    
    if not os.path.exists(project_dir):
        print(f"❌ No se encontró el proyecto: {project_dir}")
        sys.exit(1)
    
    print("🎯 Generador de Video Simple - Santa Teresa de Ávila")
    print("=" * 50)
    
    output_file = create_video_simple(project_dir)
    
    if output_file:
        print(f"\n🎉 ¡Proceso completado!")
        print(f"📹 Video generado: {output_file}")
    else:
        print(f"\n⚠️  Proceso no completado")

if __name__ == "__main__":
    main()