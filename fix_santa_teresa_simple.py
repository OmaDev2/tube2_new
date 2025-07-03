#!/usr/bin/env python3
"""
Script simple para arreglar el video de Santa Teresa de Ávila
"""

import json
import os
import subprocess

def main():
    project_dir = "projects/santa_teresa_de_ávila__e23a5a4a"
    
    print("🔍 Analizando proyecto...")
    
    # Cargar scenes.json
    scenes_path = os.path.join(project_dir, "scenes.json")
    with open(scenes_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    scenes = data.get('scenes', [])
    
    # Encontrar audio
    audio_dir = os.path.join(project_dir, "audio")
    audio_files = [f for f in os.listdir(audio_dir) if f.endswith('.mp3')]
    audio_file = os.path.join(audio_dir, audio_files[0]) if audio_files else None
    
    # Encontrar imágenes
    images_dir = os.path.join(project_dir, "images")
    image_files = []
    for i in range(1000):
        webp_file = f"scene_{i:03d}.webp"
        webp_path = os.path.join(images_dir, webp_file)
        if os.path.exists(webp_path):
            image_files.append(webp_path)
        elif i > 0:
            break
    
    print(f"📊 Estadísticas:")
    print(f"   - Escenas: {len(scenes)}")
    print(f"   - Imágenes: {len(image_files)}")
    print(f"   - Audio: {os.path.basename(audio_file) if audio_file else 'No encontrado'}")
    
    if not audio_file:
        print("❌ No se encontró archivo de audio")
        return
    
    if len(image_files) == 0:
        print("❌ No se encontraron imágenes")
        return
    
    # Crear archivo de concatenación
    concat_file = os.path.join(project_dir, "concat_fixed.txt")
    
    print("📝 Generando lista de concatenación...")
    
    with open(concat_file, 'w', encoding='utf-8') as f:
        for i, image_file in enumerate(image_files):
            if i < len(scenes):
                scene = scenes[i]
                duration = max(scene.get('duration', 2.0), 1.0)
            else:
                duration = 2.0
            
            # Usar solo el nombre del archivo, no la ruta completa
            image_filename = os.path.basename(image_file)
            f.write(f"file '{image_filename}'\n")
            f.write(f"duration {duration}\n")
        
        # Agregar última imagen
        f.write(f"file '{os.path.basename(image_files[-1])}'\n")
    
    # Comando FFmpeg (ejecutar desde el directorio de imágenes)
    output_path = os.path.join(project_dir, "video_fixed.mp4")
    images_dir = os.path.join(project_dir, "images")
    
    cmd = [
        'ffmpeg',
        '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', concat_file,
        '-i', audio_file,
        '-c:v', 'libx264',
        '-preset', 'fast',
        '-crf', '25',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-shortest',
        '-pix_fmt', 'yuv420p',
        output_path
    ]
    
    print("🚀 Ejecutando FFmpeg...")
    print(f"   Comando: {' '.join(cmd)}")
    print(f"   Ejecutando desde: {images_dir}")
    
    try:
        # Cambiar al directorio de imágenes para que FFmpeg encuentre los archivos
        original_dir = os.getcwd()
        os.chdir(images_dir)
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Volver al directorio original
        os.chdir(original_dir)
        
        print("✅ Video generado exitosamente!")
        print(f"   Archivo: {output_path}")
        
        # Limpiar archivo temporal
        os.remove(concat_file)
        print(f"   Archivo temporal eliminado")
        
    except subprocess.CalledProcessError as e:
        # Volver al directorio original en caso de error
        os.chdir(original_dir)
        print(f"❌ Error al ejecutar FFmpeg:")
        print(f"   {e.stderr}")
    except Exception as e:
        # Volver al directorio original en caso de error
        os.chdir(original_dir)
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 