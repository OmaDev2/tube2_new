#!/usr/bin/env python3
"""
🚀 Prueba Rápida de Efectos
===========================

Script simple para probar un efecto específico rápidamente.

Uso:
    python prueba_efecto_rapida.py <efecto> [imagen_numero]
    
Ejemplos:
    python prueba_efecto_rapida.py kenburns
    python prueba_efecto_rapida.py zoom_in 5
    python prueba_efecto_rapida.py shake 10
"""

import sys
import random
from pathlib import Path
from moviepy.editor import ImageClip

# Añadir el directorio raíz al path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from utils.efectos import EfectosVideo

def main():
    # Configuración
    images_dir = Path("projects/san_blas__625f3d33/images")
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)
    
    # Verificar argumentos
    if len(sys.argv) < 2:
        print("❌ Uso: python prueba_efecto_rapida.py <efecto> [imagen_numero]")
        print("\n🎬 Efectos disponibles:")
        efectos = ["zoom_in", "zoom_out", "pan_left", "pan_right", "pan_up", "pan_down", 
                  "kenburns", "shake", "fade_in", "fade_out", "mirror_x", "mirror_y", "rotate_180"]
        for i, efecto in enumerate(efectos):
            print(f"  {i+1:2d}. {efecto}")
        return
    
    efecto_name = sys.argv[1]
    
    # Obtener lista de imágenes
    image_files = sorted([
        f for f in images_dir.iterdir() 
        if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']
    ])
    
    if not image_files:
        print(f"❌ No se encontraron imágenes en {images_dir}")
        return
    
    # Seleccionar imagen
    if len(sys.argv) >= 3:
        try:
            img_index = int(sys.argv[2])
            if img_index < 0 or img_index >= len(image_files):
                print(f"❌ Número de imagen inválido. Debe ser entre 0 y {len(image_files)-1}")
                return
            image_path = image_files[img_index]
        except ValueError:
            print("❌ El número de imagen debe ser un entero")
            return
    else:
        image_path = random.choice(image_files)
    
    # Configuraciones de efectos
    params_config = {
        "zoom_in": {"zoom_factor": 1.6},
        "zoom_out": {"zoom_factor": 2.0},
        "pan_left": {"zoom_factor": 1.4, "distance": 0.4},
        "pan_right": {"zoom_factor": 1.4, "distance": 0.4},
        "pan_up": {"zoom_factor": 1.4},
        "pan_down": {"zoom_factor": 1.4},
        "kenburns": {"zoom_start": 1.0, "zoom_end": 1.6, "pan_start": (0.0, 0.0), "pan_end": (0.4, 0.3)},
        "shake": {"intensity": 10, "zoom_factor": 1.3},
        "fade_in": {"duration": 4.0},
        "fade_out": {"duration": 4.0},
        "mirror_x": {},
        "mirror_y": {},
        "rotate_180": {}
    }
    
    if efecto_name not in params_config:
        print(f"❌ Efecto '{efecto_name}' no reconocido")
        print("🎬 Efectos disponibles:", list(params_config.keys()))
        return
    
    # Crear video
    output_path = output_dir / f"prueba_{efecto_name}_{image_path.stem}.mp4"
    
    print(f"🎬 Aplicando efecto '{efecto_name}' a {image_path.name}")
    print(f"📁 Guardando en: {output_path}")
    
    try:
        # Crear clip
        clip = ImageClip(str(image_path)).set_duration(15.0).set_fps(24)
        
        # Aplicar efecto
        params = params_config[efecto_name]
        clip_con_efecto = EfectosVideo.apply_effect(clip, efecto_name, **params)
        
        # Guardar
        clip_con_efecto.write_videofile(
            str(output_path),
            fps=24,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            verbose=False,
            logger=None
        )
        
        # Limpiar
        clip.close()
        clip_con_efecto.close()
        
        print(f"✅ Video creado exitosamente: {output_path}")
        print(f"🎥 Duración: 15 segundos")
        print(f"📊 Parámetros usados: {params}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main() 