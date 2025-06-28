#!/usr/bin/env python3
"""
🎬 Demo Video Realista con Efectos
=================================

Genera un video de muestra usando duraciones realistas (12-15 segundos por imagen)
como se usaría en producción real.

Uso:
    python demo_video_realista.py
"""

import sys
from pathlib import Path
from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip

# Añadir el directorio raíz al path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from utils.efectos import EfectosVideo

def crear_demo_realista():
    """Crea un video demo con efectos usando duraciones realistas."""
    
    # Configuración
    images_dir = Path("projects/san_blas__625f3d33/images")
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "demo_video_realista.mp4"
    
    # Obtener lista de imágenes
    image_files = sorted([
        f for f in images_dir.iterdir() 
        if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']
    ])[:8]  # Usar solo 8 imágenes para el demo
    
    if not image_files:
        print(f"❌ No se encontraron imágenes en {images_dir}")
        return
    
    # Configuración de efectos para demo realista
    secuencia_efectos = [
        {
            "imagen": image_files[0],
            "efecto": "kenburns",
            "params": {"zoom_start": 1.0, "zoom_end": 1.4, "pan_start": (0.2, 0.1), "pan_end": (0.8, 0.6)},
            "duracion": 14.0,
            "descripcion": "Ken Burns suave - zoom y paneo elegante"
        },
        {
            "imagen": image_files[1],
            "efecto": "zoom_in",
            "params": {"zoom_factor": 1.3},
            "duracion": 12.0,
            "descripcion": "Zoom in sutil para crear profundidad"
        },
        {
            "imagen": image_files[2],
            "efecto": "pan_left",
            "params": {"zoom_factor": 1.25, "distance": 0.3},
            "duracion": 13.0,
            "descripcion": "Paneo izquierda para seguir la narrativa"
        },
        {
            "imagen": image_files[3],
            "efecto": "fade_in",
            "params": {"duration": 2.5},
            "duracion": 11.0,
            "descripcion": "Fade in dramático"
        },
        {
            "imagen": image_files[4],
            "efecto": "pan_right",
            "params": {"zoom_factor": 1.35, "distance": 0.25},
            "duracion": 15.0,
            "descripcion": "Paneo derecha con zoom ligero"
        },
        {
            "imagen": image_files[5],
            "efecto": "zoom_out",
            "params": {"zoom_factor": 1.6},
            "duracion": 12.5,
            "descripcion": "Zoom out revelador"
        },
        {
            "imagen": image_files[6],
            "efecto": "kenburns",
            "params": {"zoom_start": 1.3, "zoom_end": 1.1, "pan_start": (0.7, 0.3), "pan_end": (0.3, 0.7)},
            "duracion": 14.5,
            "descripcion": "Ken Burns inverso - zoom out con paneo"
        },
        {
            "imagen": image_files[7],
            "efecto": "fade_out",
            "params": {"duration": 3.0},
            "duracion": 13.0,
            "descripcion": "Fade out final elegante"
        }
    ]
    
    print("🎬 CREANDO VIDEO DEMO REALISTA")
    print("=" * 50)
    print(f"📁 Imágenes: {len(secuencia_efectos)} seleccionadas")
    print(f"⏱️ Duración total estimada: {sum(s['duracion'] for s in secuencia_efectos):.1f} segundos")
    print(f"📁 Guardando en: {output_path}")
    print("")
    
    clips = []
    
    for i, config in enumerate(secuencia_efectos, 1):
        print(f"📸 Procesando clip {i}/{len(secuencia_efectos)}: {config['imagen'].name}")
        print(f"   ✨ Efecto: {config['efecto']}")
        print(f"   📝 {config['descripcion']}")
        print(f"   ⏱️ Duración: {config['duracion']}s")
        
        try:
            # Crear clip base
            clip = ImageClip(str(config['imagen'])).set_duration(config['duracion']).set_fps(24)
            
            # Aplicar efecto
            clip_con_efecto = EfectosVideo.apply_effect(clip, config['efecto'], **config['params'])
            
            clips.append(clip_con_efecto)
            print(f"   ✅ Clip procesado exitosamente")
            
        except Exception as e:
            print(f"   ❌ Error procesando clip: {e}")
            # Usar clip sin efecto como fallback
            clip_sin_efecto = ImageClip(str(config['imagen'])).set_duration(config['duracion']).set_fps(24)
            clips.append(clip_sin_efecto)
            print(f"   ⚠️ Usando clip sin efecto como fallback")
        
        print("")
    
    if not clips:
        print("❌ No se pudo procesar ningún clip")
        return
    
    print("🔗 Concatenando clips...")
    try:
        # Concatenar todos los clips
        video_final = concatenate_videoclips(clips, method="compose")
        
        print("💾 Guardando video final...")
        # Guardar el video
        video_final.write_videofile(
            str(output_path),
            fps=24,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            verbose=False,
            logger=None
        )
        
        # Limpiar memoria
        for clip in clips:
            clip.close()
        video_final.close()
        
        print("")
        print("🎉 ¡VIDEO DEMO CREADO EXITOSAMENTE!")
        print("=" * 50)
        print(f"📁 Archivo: {output_path}")
        print(f"⏱️ Duración final: {sum(s['duracion'] for s in secuencia_efectos):.1f} segundos")
        print(f"🎬 Clips procesados: {len(clips)}")
        print(f"📏 Resolución: 1920x1080 @ 24fps")
        print("")
        print("💡 Este video muestra cómo se ven los efectos con duraciones realistas")
        print("   similares a las que se usarían en un video de producción real.")
        
    except Exception as e:
        print(f"❌ Error creando video final: {e}")
        return

def main():
    """Función principal."""
    print("🎬 DEMO VIDEO REALISTA - EFECTOS EN DURACIONES DE PRODUCCIÓN")
    print("=" * 60)
    print("")
    
    crear_demo_realista()

if __name__ == "__main__":
    main() 