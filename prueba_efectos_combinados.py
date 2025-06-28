#!/usr/bin/env python3
"""
Script de prueba para los nuevos efectos combinados:
- shake_zoom_combo: Shake inicial + zoom in/out
- shake_kenburns_combo: Shake inicial + Ken Burns

Uso:
    python prueba_efectos_combinados.py [efecto]
    
Ejemplos:
    python prueba_efectos_combinados.py shake_zoom_combo
    python prueba_efectos_combinados.py shake_kenburns_combo
    python prueba_efectos_combinados.py ambos
"""

import sys
import os
from moviepy.editor import ImageClip, concatenate_videoclips
from pathlib import Path

# Añadir el directorio actual al path para importar utils
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.efectos import EfectosVideo

def prueba_shake_zoom_combo():
    """Prueba el efecto shake_zoom_combo"""
    print("🌪️🔍 Probando efecto shake_zoom_combo...")
    
    # Usar la primera imagen disponible
    imagen_path = "projects/san_blas__625f3d33/images/scene_001.webp"
    if not os.path.exists(imagen_path):
        print(f"❌ No se encontró la imagen: {imagen_path}")
        return None
    
    # Crear clip de imagen con duración de 12 segundos
    clip = ImageClip(imagen_path, duration=12)
    
    # Aplicar efecto shake_zoom_combo
    # - 2 segundos de shake inicial
    # - Luego zoom in (60% = 6 segundos) y zoom out (40% = 4 segundos)
    clip_con_efecto = EfectosVideo.shake_zoom_combo(
        clip,
        shake_duration=2.0,        # 2 segundos de shake
        intensity=10,              # Intensidad moderada
        zoom_factor_shake=1.15,    # Zoom del shake
        zoom_in_factor=1.5,        # Zoom in hasta 1.5x
        zoom_out_factor=1.8        # Zoom out hasta 1.8x
    )
    
    # Guardar el video
    output_path = "test_output/shake_zoom_combo_test.mp4"
    os.makedirs("test_output", exist_ok=True)
    
    print("💾 Generando video...")
    clip_con_efecto.write_videofile(
        output_path,
        fps=30,
        codec='libx264',
        audio_codec='aac'
    )
    
    print(f"✅ Video guardado: {output_path}")
    return output_path

def prueba_shake_kenburns_combo():
    """Prueba el efecto shake_kenburns_combo"""
    print("🌪️🎬 Probando efecto shake_kenburns_combo...")
    
    # Usar la segunda imagen disponible
    imagen_path = "projects/san_blas__625f3d33/images/scene_002.webp"
    if not os.path.exists(imagen_path):
        print(f"❌ No se encontró la imagen: {imagen_path}")
        return None
    
    # Crear clip de imagen con duración de 12 segundos
    clip = ImageClip(imagen_path, duration=12)
    
    # Aplicar efecto shake_kenburns_combo
    # - 1.5 segundos de shake inicial
    # - Luego Ken Burns suave por 10.5 segundos
    clip_con_efecto = EfectosVideo.shake_kenburns_combo(
        clip,
        shake_duration=1.5,                    # 1.5 segundos de shake
        intensity=12,                          # Intensidad del shake
        zoom_factor_shake=1.12,               # Zoom del shake
        kenburns_zoom_start=1.0,              # Zoom inicial Ken Burns
        kenburns_zoom_end=1.6,                # Zoom final Ken Burns
        kenburns_pan_start=(0.1, 0.1),       # Paneo desde esquina sup-izq
        kenburns_pan_end=(0.8, 0.7)          # Paneo hacia esquina inf-der
    )
    
    # Guardar el video
    output_path = "test_output/shake_kenburns_combo_test.mp4"
    os.makedirs("test_output", exist_ok=True)
    
    print("💾 Generando video...")
    clip_con_efecto.write_videofile(
        output_path,
        fps=30,
        codec='libx264',
        audio_codec='aac'
    )
    
    print(f"✅ Video guardado: {output_path}")
    return output_path

def crear_video_comparativo():
    """Crea un video que muestra ambos efectos consecutivamente"""
    print("🎬 Creando video comparativo con ambos efectos...")
    
    videos_generados = []
    
    # Generar video con shake_zoom_combo
    video1 = prueba_shake_zoom_combo()
    if video1:
        videos_generados.append(video1)
    
    # Generar video con shake_kenburns_combo  
    video2 = prueba_shake_kenburns_combo()
    if video2:
        videos_generados.append(video2)
    
    if len(videos_generados) == 2:
        # Crear video combinado
        from moviepy.editor import VideoFileClip
        
        clip1 = VideoFileClip(videos_generados[0])
        clip2 = VideoFileClip(videos_generados[1])
        
        # Añadir títulos con texto
        from moviepy.editor import TextClip, CompositeVideoClip
        
        title1 = TextClip("Shake + Zoom Combo", fontsize=50, color='white', font='Arial-Bold')
        title1 = title1.set_position(('center', 50)).set_duration(3).set_start(0)
        
        title2 = TextClip("Shake + Ken Burns Combo", fontsize=50, color='white', font='Arial-Bold')
        title2 = title2.set_position(('center', 50)).set_duration(3).set_start(12)
        
        # Combinar clips
        video_final = concatenate_videoclips([clip1, clip2])
        video_con_titulos = CompositeVideoClip([video_final, title1, title2])
        
        output_path = "test_output/efectos_combinados_comparativo.mp4"
        print("💾 Generando video comparativo...")
        video_con_titulos.write_videofile(
            output_path,
            fps=30,
            codec='libx264',
            audio_codec='aac'
        )
        
        print(f"✅ Video comparativo guardado: {output_path}")
        print(f"📊 Duración total: {video_final.duration} segundos")
        
        # Limpiar recursos
        clip1.close()
        clip2.close()
        video_con_titulos.close()

def main():
    if len(sys.argv) < 2:
        print("📋 Uso: python prueba_efectos_combinados.py [efecto]")
        print("   Opciones:")
        print("   - shake_zoom_combo")
        print("   - shake_kenburns_combo") 
        print("   - ambos")
        return
    
    efecto = sys.argv[1].lower()
    
    # Verificar que existe el directorio de imágenes
    if not os.path.exists("projects/san_blas__625f3d33/images"):
        print("❌ No se encontró el directorio de imágenes: projects/san_blas__625f3d33/images")
        print("💡 Asegúrate de que tienes un proyecto con imágenes para probar")
        return
    
    if efecto == "shake_zoom_combo":
        prueba_shake_zoom_combo()
        
    elif efecto == "shake_kenburns_combo":
        prueba_shake_kenburns_combo()
        
    elif efecto == "ambos":
        crear_video_comparativo()
        
    else:
        print(f"❌ Efecto desconocido: {efecto}")
        print("💡 Usa: shake_zoom_combo, shake_kenburns_combo, o ambos")

if __name__ == "__main__":
    main() 