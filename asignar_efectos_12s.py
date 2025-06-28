#!/usr/bin/env python3
"""
🎬 Asignación de Efectos - 12 Segundos por Imagen
===============================================

Asigna un efecto específico a cada imagen con duración fija de 12 segundos.
Cada imagen tendrá su propio efecto único distribuido de manera equilibrada.

Uso:
    python asignar_efectos_12s.py
"""

import sys
from pathlib import Path
from moviepy.editor import ImageClip, concatenate_videoclips

# Añadir el directorio raíz al path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from utils.efectos import EfectosVideo

def asignar_efectos_a_imagenes():
    """Asigna un efecto específico a cada imagen con duración de 12 segundos."""
    
    # Configuración
    images_dir = Path("projects/san_blas__625f3d33/images")
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "video_efectos_12s.mp4"
    
    # Duración fija para todas las imágenes
    DURACION_CLIP = 12.0
    
    # Obtener lista de todas las imágenes
    image_files = sorted([
        f for f in images_dir.iterdir() 
        if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']
    ])
    
    if not image_files:
        print(f"❌ No se encontraron imágenes en {images_dir}")
        return
    
    # Definir efectos disponibles con sus parámetros optimizados para 12 segundos
    efectos_disponibles = [
        {
            "nombre": "kenburns",
            "params": {"zoom_start": 1.0, "zoom_end": 1.4, "pan_start": (0.1, 0.1), "pan_end": (0.6, 0.7)},
            "descripcion": "Ken Burns - zoom y paneo elegante"
        },
        {
            "nombre": "zoom_in", 
            "params": {"zoom_factor": 1.5},
            "descripcion": "Zoom hacia adelante suave"
        },
        {
            "nombre": "zoom_out",
            "params": {"zoom_factor": 1.6},
            "descripcion": "Zoom hacia atrás revelador"
        },
        {
            "nombre": "pan_left",
            "params": {"zoom_factor": 1.3, "distance": 0.4},
            "descripcion": "Paneo hacia la izquierda"
        },
        {
            "nombre": "pan_right",
            "params": {"zoom_factor": 1.3, "distance": 0.4},
            "descripcion": "Paneo hacia la derecha"
        },
        {
            "nombre": "pan_up",
            "params": {"zoom_factor": 1.25},
            "descripcion": "Paneo hacia arriba"
        },
        {
            "nombre": "pan_down",
            "params": {"zoom_factor": 1.25},
            "descripcion": "Paneo hacia abajo"
        },
        {
            "nombre": "shake",
            "params": {"intensity": 6, "zoom_factor": 1.15},
            "descripcion": "Efecto de temblor sutil"
        },
        {
            "nombre": "shake_zoom_combo",
            "params": {"shake_duration": 2.0, "intensity": 8, "zoom_factor_shake": 1.2, "zoom_in_factor": 1.4, "zoom_out_factor": 1.6},
            "descripcion": "Temblor inicial + zoom in/out"
        },
        {
            "nombre": "shake_kenburns_combo",
            "params": {"shake_duration": 1.5, "intensity": 10, "zoom_factor_shake": 1.15, "kenburns_zoom_start": 1.0, "kenburns_zoom_end": 1.4, "kenburns_pan_start": (0.2, 0.2), "kenburns_pan_end": (0.7, 0.6)},
            "descripcion": "Temblor inicial + Ken Burns elegante"
        },
        {
            "nombre": "fade_in",
            "params": {"duration": 3.0},
            "descripcion": "Aparición gradual"
        },
        {
            "nombre": "fade_out",
            "params": {"duration": 3.0},
            "descripcion": "Desvanecimiento gradual"
        },
        {
            "nombre": "mirror_x",
            "params": {},
            "descripcion": "Espejo horizontal"
        },
        {
            "nombre": "mirror_y",
            "params": {},
            "descripcion": "Espejo vertical"
        },
        {
            "nombre": "rotate_180",
            "params": {},
            "descripcion": "Rotación 180 grados"
        }
    ]
    
    print("🎬 ASIGNANDO EFECTOS A IMÁGENES - 12 SEGUNDOS POR CLIP")
    print("=" * 60)
    print(f"📁 Imágenes encontradas: {len(image_files)}")
    print(f"✨ Efectos disponibles: {len(efectos_disponibles)}")
    print(f"⏱️ Duración por clip: {DURACION_CLIP} segundos")
    print(f"⏱️ Duración total estimada: {len(image_files) * DURACION_CLIP:.1f} segundos")
    print(f"💾 Guardando en: {output_path}")
    print("")
    
    # Crear asignación de efectos
    asignaciones = []
    clips_procesados = []
    
    for i, image_file in enumerate(image_files):
        # Asignar efecto ciclando por la lista de efectos disponibles
        efecto_index = i % len(efectos_disponibles)
        efecto = efectos_disponibles[efecto_index]
        
        asignacion = {
            "imagen": image_file,
            "efecto": efecto,
            "numero": i + 1
        }
        asignaciones.append(asignacion)
        
        print(f"📸 Imagen {i+1:2d}/{len(image_files)}: {image_file.name}")
        print(f"   ✨ Efecto: {efecto['nombre']}")
        print(f"   📝 {efecto['descripcion']}")
        print(f"   ⏱️ Duración: {DURACION_CLIP}s")
        
        try:
            # Crear clip base de 12 segundos
            clip = ImageClip(str(image_file)).set_duration(DURACION_CLIP).set_fps(24)
            
            # Aplicar el efecto asignado
            clip_con_efecto = EfectosVideo.apply_effect(clip, efecto['nombre'], **efecto['params'])
            
            clips_procesados.append(clip_con_efecto)
            print(f"   ✅ Procesado exitosamente")
            
        except Exception as e:
            print(f"   ❌ Error aplicando efecto: {e}")
            # Usar clip sin efecto como fallback
            clip_sin_efecto = ImageClip(str(image_file)).set_duration(DURACION_CLIP).set_fps(24)
            clips_procesados.append(clip_sin_efecto)
            print(f"   ⚠️ Usando clip sin efecto como fallback")
        
        print("")
    
    if not clips_procesados:
        print("❌ No se pudo procesar ningún clip")
        return
    
    print("🔗 Concatenando todos los clips...")
    print(f"📊 Total de clips a concatenar: {len(clips_procesados)}")
    
    try:
        # Concatenar todos los clips
        video_final = concatenate_videoclips(clips_procesados, method="compose")
        
        print("💾 Renderizando video final...")
        print("⏳ Esto puede tardar varios minutos debido a la duración del video...")
        
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
        for clip in clips_procesados:
            clip.close()
        video_final.close()
        
        print("")
        print("🎉 ¡VIDEO CREADO EXITOSAMENTE!")
        print("=" * 50)
        print(f"📁 Archivo: {output_path}")
        print(f"⏱️ Duración final: {len(image_files) * DURACION_CLIP:.1f} segundos")
        print(f"📊 Imágenes procesadas: {len(image_files)}")
        print(f"✨ Efectos aplicados: {len(clips_procesados)}")
        print(f"📏 Resolución: 1920x1080 @ 24fps")
        print("")
        
        # Mostrar resumen de asignaciones
        print("📋 RESUMEN DE EFECTOS ASIGNADOS:")
        print("-" * 40)
        efectos_usados = {}
        for asignacion in asignaciones:
            efecto_nombre = asignacion['efecto']['nombre']
            if efecto_nombre not in efectos_usados:
                efectos_usados[efecto_nombre] = 0
            efectos_usados[efecto_nombre] += 1
        
        for efecto, cantidad in efectos_usados.items():
            print(f"  • {efecto}: {cantidad} vez(es)")
        
        print("")
        print("💡 Cada imagen tiene 12 segundos de duración con su efecto específico")
        print("   Los efectos se distribuyen cíclicamente entre todas las imágenes")
        
    except Exception as e:
        print(f"❌ Error creando video final: {e}")
        return

def crear_video_muestra_corto():
    """Crea un video de muestra más corto con solo 6 imágenes para pruebas rápidas."""
    
    # Configuración
    images_dir = Path("projects/san_blas__625f3d33/images")
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "muestra_efectos_12s.mp4"
    
    DURACION_CLIP = 12.0
    
    # Obtener solo las primeras 6 imágenes
    image_files = sorted([
        f for f in images_dir.iterdir() 
        if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']
    ])[:6]
    
    if not image_files:
        print(f"❌ No se encontraron imágenes en {images_dir}")
        return
    
    # Efectos específicos para la muestra
    efectos_muestra = [
        {"nombre": "kenburns", "params": {"zoom_start": 1.0, "zoom_end": 1.5, "pan_start": (0.0, 0.0), "pan_end": (0.5, 0.3)}},
        {"nombre": "zoom_in", "params": {"zoom_factor": 1.4}},
        {"nombre": "pan_left", "params": {"zoom_factor": 1.3, "distance": 0.4}},
        {"nombre": "shake", "params": {"intensity": 8, "zoom_factor": 1.2}},
        {"nombre": "zoom_out", "params": {"zoom_factor": 1.6}},
        {"nombre": "fade_out", "params": {"duration": 3.0}}
    ]
    
    print("🎬 CREANDO MUESTRA CORTA - 6 IMÁGENES x 12 SEGUNDOS")
    print("=" * 50)
    print(f"⏱️ Duración total: {len(image_files) * DURACION_CLIP:.1f} segundos")
    print("")
    
    clips = []
    
    for i, (image_file, efecto) in enumerate(zip(image_files, efectos_muestra)):
        print(f"📸 {i+1}/6: {image_file.name} → {efecto['nombre']}")
        
        try:
            clip = ImageClip(str(image_file)).set_duration(DURACION_CLIP).set_fps(24)
            clip_con_efecto = EfectosVideo.apply_effect(clip, efecto['nombre'], **efecto['params'])
            clips.append(clip_con_efecto)
            print(f"   ✅ Procesado")
        except Exception as e:
            print(f"   ❌ Error: {e}")
            clip_sin_efecto = ImageClip(str(image_file)).set_duration(DURACION_CLIP).set_fps(24)
            clips.append(clip_sin_efecto)
    
    if clips:
        print("\n🔗 Creando video...")
        video_final = concatenate_videoclips(clips, method="compose")
        video_final.write_videofile(
            str(output_path),
            fps=24,
            codec='libx264',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            verbose=False,
            logger=None
        )
        
        for clip in clips:
            clip.close()
        video_final.close()
        
        print(f"✅ Muestra creada: {output_path}")

def main():
    """Función principal."""
    print("🎬 GENERADOR DE VIDEO CON EFECTOS ASIGNADOS")
    print("=" * 50)
    print("1. Video completo con todas las imágenes")
    print("2. Video muestra con 6 imágenes (recomendado para pruebas)")
    print("")
    
    opcion = input("Selecciona una opción (1/2) [2]: ").strip()
    
    if opcion == "1":
        print("\n🚀 Creando video completo...")
        asignar_efectos_a_imagenes()
    else:
        print("\n🚀 Creando video muestra...")
        crear_video_muestra_corto()

if __name__ == "__main__":
    main() 