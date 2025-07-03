#!/usr/bin/env python3
"""
Script para re-ensamblar el video de Santa Teresa de Ávila
Usando todos los componentes ya generados (audio, imágenes, scenes.json)
"""

import json
import os
import subprocess
import sys
from pathlib import Path

def load_scenes(project_dir):
    """Cargar scenes.json"""
    scenes_path = os.path.join(project_dir, "scenes.json")
    with open(scenes_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('scenes', [])

def get_audio_file(project_dir):
    """Encontrar el archivo de audio"""
    audio_dir = os.path.join(project_dir, "audio")
    audio_files = [f for f in os.listdir(audio_dir) if f.endswith('.mp3')]
    if not audio_files:
        raise FileNotFoundError("No se encontró archivo de audio MP3")
    return os.path.join(audio_dir, audio_files[0])

def get_image_files(project_dir):
    """Obtener lista de imágenes ordenadas"""
    images_dir = os.path.join(project_dir, "images")
    image_files = []
    for i in range(1000):
        webp_file = f"scene_{i:03d}.webp"
        webp_path = os.path.join(images_dir, webp_file)
        if os.path.exists(webp_path):
            image_files.append(webp_path)
        elif i > 0:
            break
    return sorted(image_files)

def create_video_script(project_dir, output_file="video_output.mp4"):
    """Crear script de FFmpeg para ensamblar el video"""
    
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
    concat_file = os.path.join(project_dir, "concat_list.txt")
    
    print(f"📝 Generando lista de concatenación...")
    
    with open(concat_file, 'w', encoding='utf-8') as f:
        for i in range(num_scenes):
            if i < len(image_files):
                # Calcular duración de la escena
                scene = scenes[i]
                duration = scene.get('duration', 2.0)  # Fallback a 2 segundos
                
                # Asegurar que la duración sea positiva
                if duration <= 0:
                    duration = 2.0
                
                # Usar solo el nombre del archivo (relativo a la carpeta images)
                image_filename = os.path.basename(image_files[i])
                f.write(f"file '{image_filename}'\n")
                f.write(f"duration {duration}\n")
        
        # Agregar la última imagen una vez más (FFmpeg requiere esto)
        if image_files:
            f.write(f"file '{image_files[-1]}'\n")
    
    # Al ejecutar FFmpeg, cambiar a la carpeta de imágenes y usar rutas relativas
    images_dir = os.path.join(project_dir, "images")
    concat_file_rel = os.path.relpath(concat_file, images_dir)
    audio_file_rel = os.path.relpath(audio_file, images_dir)
    output_path_rel = os.path.relpath(output_file, images_dir)
    
    print(f"📁 Rutas calculadas:")
    print(f"   - Directorio de trabajo: {images_dir}")
    print(f"   - Concat file: {concat_file_rel}")
    print(f"   - Audio file: {audio_file_rel}")
    print(f"   - Output file: {output_path_rel}")

    cmd = [
        'ffmpeg',
        '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_file_rel,
        '-i', audio_file_rel,
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-shortest',
        '-pix_fmt', 'yuv420p',
        output_path_rel
    ]

    print(f"🎬 Comando FFmpeg generado:")
    print(f"   {' '.join(cmd)}")
    ejecutar = input("¿Ejecutar FFmpeg ahora? (s/n): ").strip().lower()
    if ejecutar == 's':
        original_dir = os.getcwd()
        os.chdir(images_dir)
        try:
            subprocess.run(cmd, check=True)
            print(f"✅ Video generado: {output_path_rel}")
        finally:
            os.chdir(original_dir)
    else:
        print("📋 Comando FFmpeg generado pero no ejecutado")
        print(f"   Puedes ejecutarlo manualmente:")
        print(f"   {' '.join(cmd)}")

def main():
    project_dir = "projects/santa_teresa_de_ávila__e23a5a4a"
    
    if not os.path.exists(project_dir):
        print(f"❌ No se encontró el proyecto: {project_dir}")
        sys.exit(1)
    
    print("🎯 Re-ensamblador de Video - Santa Teresa de Ávila")
    print("=" * 50)
    
    try:
        # Generar comando FFmpeg
        create_video_script(project_dir)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()