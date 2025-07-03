#!/usr/bin/env python3
"""
Script de prueba para re-ensamblar el video de Santa Teresa de Ávila
Procesa solo las primeras 15 imágenes con efectos, overlays, transiciones y fades
"""

import os
import json
import subprocess
import shutil
from glob import glob

PROJECT_DIR = "projects/santa_teresa_de_ávila__e23a5a4a"
IMAGES_DIR = os.path.join(PROJECT_DIR, "images")
AUDIO_DIR = os.path.join(PROJECT_DIR, "audio")
OUTPUT_VIDEO = os.path.join(PROJECT_DIR, "video_test_15_scenes.mp4")
TEMP_DIR = os.path.join(PROJECT_DIR, "temp_video_test")
OVERLAY_PATH = "/Users/olga/video_tube2 copia/overlays/1-sparkes_vonv_lossy.webm"
MUSIC_DIR = "background_music"
MAX_SCENES = 15  # Solo procesar las primeras 15 escenas

os.makedirs(TEMP_DIR, exist_ok=True)

def load_scenes():
    with open(os.path.join(PROJECT_DIR, "scenes.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["scenes"][:MAX_SCENES]  # Solo las primeras 15

def get_audio_file():
    files = [f for f in os.listdir(AUDIO_DIR) if f.endswith(".mp3")]
    if not files:
        raise FileNotFoundError("No se encontró archivo de audio MP3")
    return os.path.join(AUDIO_DIR, files[0])

def get_image_files():
    files = []
    for i in range(MAX_SCENES):  # Solo las primeras 15
        fname = f"scene_{i:03d}.webp"
        fpath = os.path.join(IMAGES_DIR, fname)
        if os.path.exists(fpath):
            files.append(fpath)
        else:
            break
    return files

def get_music_file():
    files = glob(os.path.join(MUSIC_DIR, "*.mp3"))
    return files[0] if files else None

def apply_effects_to_images(image_files, scenes):
    temp_images = []
    effects = ["zoom_in", "zoom_out", "pan_right", "pan_left", "pan_up", "pan_down"]
    
    print(f"🎬 Procesando {len(image_files)} imágenes con efectos (PRUEBA)...")
    
    for idx, (img, scene) in enumerate(zip(image_files, scenes)):
        out_img = os.path.join(TEMP_DIR, f"scene_{idx:03d}.mp4")
        duration = max(scene.get("duration", 2.0), 1.0)
        effect = effects[idx % len(effects)]
        
        print(f"   Procesando escena {idx+1}/{len(image_files)}: {effect}")
        
        # Efectos reales con FFmpeg
        if effect == "zoom_in":
            vf = f"zoompan=z='min(zoom+0.002,1.3)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720,fps=25"
        elif effect == "zoom_out":
            vf = f"zoompan=z='max(zoom-0.002,0.8)':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720,fps=25"
        elif effect == "pan_right":
            vf = f"crop=iw*0.8:ih:iw*0.1:0,scale=1280:720,fps=25"
        elif effect == "pan_left":
            vf = f"crop=iw*0.8:ih:iw*0.1:0,scale=1280:720,fps=25"
        elif effect == "pan_up":
            vf = f"crop=iw:ih*0.8:0:ih*0.1,scale=1280:720,fps=25"
        elif effect == "pan_down":
            vf = f"crop=iw:ih*0.8:0:ih*0.1,scale=1280:720,fps=25"
        else:
            vf = "scale=1280:720,fps=25"
        
        # Comando base
        cmd = [
            'ffmpeg', '-y',
            '-loop', '1',
            '-t', str(duration),
            '-i', img,
            '-vf', vf,
            '-c:v', 'libx264',
            '-preset', 'ultrafast',  # Más rápido para pruebas
            '-crf', '28',  # Calidad ligeramente menor para pruebas
            '-pix_fmt', 'yuv420p',
            out_img
        ]
        
        # Añadir overlay si existe
        if os.path.exists(OVERLAY_PATH):
            print(f"     + Añadiendo overlay con opacidad 0.25...")
            cmd = [
                'ffmpeg', '-y',
                '-loop', '1',
                '-t', str(duration),
                '-i', img,
                '-t', str(duration),
                '-i', OVERLAY_PATH,
                '-filter_complex', f"[0:v]{vf}[v0];[1:v]format=rgba,colorchannelmixer=aa=0.25[overlay];[v0][overlay]overlay=W-w-20:H-h-20",
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '28',
                '-pix_fmt', 'yuv420p',
                out_img
            ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True)
            temp_images.append(out_img)
        except subprocess.CalledProcessError as e:
            print(f"❌ Error procesando escena {idx}: {e}")
            # Fallback sin efectos
            cmd_fallback = [
                'ffmpeg', '-y',
                '-loop', '1',
                '-t', str(duration),
                '-i', img,
                '-vf', 'scale=1280:720,fps=25',
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-crf', '28',
                '-pix_fmt', 'yuv420p',
                out_img
            ]
            subprocess.run(cmd_fallback, check=True, capture_output=True)
            temp_images.append(out_img)
    
    return temp_images

def create_transition_video(temp_images, scenes):
    """Crear video con transiciones dissolve entre escenas"""
    print("🎭 Aplicando transiciones dissolve entre escenas...")
    
    # Crear archivo de filtros complejos para transiciones
    filter_file = os.path.join(TEMP_DIR, "transitions.txt")
    
    with open(filter_file, "w", encoding="utf-8") as f:
        f.write("# Transiciones dissolve entre escenas (PRUEBA)\n")
        
        # Primera escena con fade in
        f.write(f"[0:v]fade=t=in:st=0:d=1[v0];\n")
        
        # Escenas intermedias con transiciones
        for i in range(1, len(temp_images)):
            prev_idx = i - 1
            curr_idx = i
            
            # Fade out de la escena anterior
            f.write(f"[{prev_idx}:v]fade=t=out:st={scenes[prev_idx].get('duration', 2.0)-1}:d=1[v{prev_idx}f];\n")
            
            # Fade in de la escena actual
            f.write(f"[{curr_idx}:v]fade=t=in:st=0:d=1[v{curr_idx}f];\n")
            
            # Transición dissolve entre las dos escenas
            if i == 1:
                f.write(f"[v{prev_idx}f][v{curr_idx}f]xfade=transition=fade:duration=1:offset={scenes[prev_idx].get('duration', 2.0)-1}[v{curr_idx}];\n")
            else:
                f.write(f"[v{prev_idx}][v{curr_idx}f]xfade=transition=fade:duration=1:offset={scenes[prev_idx].get('duration', 2.0)-1}[v{curr_idx}];\n")
        
        # Última escena con fade out
        last_idx = len(temp_images) - 1
        f.write(f"[v{last_idx}]fade=t=out:st={scenes[last_idx].get('duration', 2.0)-1}:d=1[vfinal];\n")
    
    # Crear lista de inputs para FFmpeg
    input_args = []
    for img in temp_images:
        input_args.extend(['-i', img])
    
    # Comando FFmpeg con transiciones
    transition_video = os.path.join(TEMP_DIR, "video_with_transitions.mp4")
    
    cmd = [
        'ffmpeg', '-y'
    ] + input_args + [
        '-filter_complex_script', filter_file,
        '-map', '[vfinal]',
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-crf', '28',
        '-pix_fmt', 'yuv420p',
        transition_video
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print("✅ Transiciones aplicadas correctamente")
        return transition_video
    except subprocess.CalledProcessError as e:
        print(f"❌ Error aplicando transiciones: {e}")
        # Fallback: concatenar sin transiciones
        return create_concat_file(temp_images, scenes)

def create_concat_file(temp_images, scenes):
    concat_path = os.path.join(TEMP_DIR, "concat.txt")
    with open(concat_path, "w", encoding="utf-8") as f:
        for i, img in enumerate(temp_images):
            duration = max(scenes[i].get("duration", 2.0), 1.0)
            f.write(f"file '{img}'\n")
            f.write(f"duration {duration}\n")
        f.write(f"file '{temp_images[-1]}'\n")
    return concat_path

def assemble_video(video_input, audio_file, music_file):
    # Mezclar música de fondo si existe
    final_audio = os.path.join(TEMP_DIR, "audio_mix.mp3")
    if music_file:
        # Mezclar música bajando volumen a 0.06
        cmd = [
            'ffmpeg', '-y',
            '-i', audio_file,
            '-i', music_file,
            '-filter_complex', '[1:a]volume=0.06[a1];[0:a][a1]amix=inputs=2:duration=first:dropout_transition=2',
            '-c:a', 'aac',
            '-b:a', '128k',
            final_audio
        ]
        subprocess.run(cmd, check=True)
        audio_input = final_audio
    else:
        audio_input = audio_file
    
    # Ensamblar video final con fades de entrada y salida
    print("🎬 Aplicando fades de entrada y salida al video final...")
    
    # Obtener duración del video
    duration_cmd = [
        'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', 
        '-of', 'csv=p=0', video_input
    ]
    result = subprocess.run(duration_cmd, capture_output=True, text=True)
    video_duration = float(result.stdout.strip())
    
    # Aplicar fades de entrada y salida
    final_video = os.path.join(TEMP_DIR, "video_with_fades.mp4")
    fade_cmd = [
        'ffmpeg', '-y',
        '-i', video_input,
        '-vf', f'fade=t=in:st=0:d=2,fade=t=out:st={video_duration-2}:d=2',
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-crf', '28',
        '-pix_fmt', 'yuv420p',
        final_video
    ]
    subprocess.run(fade_cmd, check=True)
    
    # Ensamblar video final con audio
    cmd = [
        'ffmpeg', '-y',
        '-i', final_video,
        '-i', audio_input,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-shortest',
        OUTPUT_VIDEO
    ]
    subprocess.run(cmd, check=True)

def main():
    print("🧪 INICIANDO PRUEBA CON PRIMERAS 15 ESCENAS")
    print("🔍 Analizando proyecto...")
    scenes = load_scenes()
    image_files = get_image_files()
    audio_file = get_audio_file()
    music_file = get_music_file()
    print(f"   - Escenas: {len(scenes)} (de 15 máximo)")
    print(f"   - Imágenes: {len(image_files)}")
    print(f"   - Audio: {os.path.basename(audio_file)}")
    print(f"   - Música: {os.path.basename(music_file) if music_file else 'No'}")
    print(f"   - Overlay: {'Sí' if os.path.exists(OVERLAY_PATH) else 'No'}")
    
    print("🎬 Aplicando efectos a imágenes...")
    temp_images = apply_effects_to_images(image_files, scenes)
    
    print("🎭 Aplicando transiciones dissolve...")
    video_with_transitions = create_transition_video(temp_images, scenes)
    
    print("🎼 Ensamblando video final...")
    assemble_video(video_with_transitions, audio_file, music_file)
    
    print(f"✅ Video de prueba generado: {OUTPUT_VIDEO}")
    print("🧪 PRUEBA COMPLETADA - Revisa el resultado antes de procesar todas las escenas")
    # Limpiar temporales
    shutil.rmtree(TEMP_DIR)
    print("🧹 Archivos temporales eliminados.")

if __name__ == "__main__":
    main() 