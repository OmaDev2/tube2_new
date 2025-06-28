#!/usr/bin/env python3
"""
🎯 Asignación Manual de Efectos - 12 Segundos
===========================================

Permite asignar efectos específicos a imágenes específicas de forma manual.
Útil cuando quieres control total sobre qué efecto aplicar a cada imagen.

Uso:
    python asignar_efectos_manual.py
"""

import sys
from pathlib import Path
from moviepy.editor import ImageClip, concatenate_videoclips

# Añadir el directorio raíz al path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from utils.efectos import EfectosVideo

def crear_video_con_asignacion_manual():
    """Crea un video con efectos asignados manualmente a cada imagen."""
    
    # Configuración
    images_dir = Path("projects/san_blas__625f3d33/images")
    output_dir = Path("test_output")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "video_efectos_manual_12s.mp4"
    
    DURACION_CLIP = 12.0
    
    # Obtener lista de imágenes
    image_files = sorted([
        f for f in images_dir.iterdir() 
        if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']
    ])
    
    if not image_files:
        print(f"❌ No se encontraron imágenes en {images_dir}")
        return
    
    # ===== ASIGNACIÓN MANUAL DE EFECTOS =====
    # Aquí puedes especificar exactamente qué efecto quieres para cada imagen
    # Formato: "nombre_imagen": ("efecto", {parámetros})
    
    asignaciones_manuales = {
        # Primeras 10 imágenes con efectos específicos
        "scene_000.webp": ("kenburns", {"zoom_start": 1.0, "zoom_end": 1.5, "pan_start": (0.0, 0.0), "pan_end": (0.6, 0.4)}),
        "scene_001.webp": ("zoom_in", {"zoom_factor": 1.4}),
        "scene_002.webp": ("pan_left", {"zoom_factor": 1.3, "distance": 0.4}),
        "scene_003.webp": ("fade_in", {"duration": 3.0}),
        "scene_004.webp": ("shake", {"intensity": 8, "zoom_factor": 1.2}),
        "scene_005.webp": ("zoom_out", {"zoom_factor": 1.6}),
        "scene_006.webp": ("pan_right", {"zoom_factor": 1.3, "distance": 0.4}),
        "scene_007.webp": ("kenburns", {"zoom_start": 1.2, "zoom_end": 1.0, "pan_start": (0.7, 0.3), "pan_end": (0.2, 0.8)}),
        "scene_008.webp": ("pan_up", {"zoom_factor": 1.25}),
        "scene_009.webp": ("mirror_x", {}),
        "scene_010.webp": ("zoom_in", {"zoom_factor": 1.5}),
        "scene_011.webp": ("pan_down", {"zoom_factor": 1.25}),
        "scene_012.webp": ("kenburns", {"zoom_start": 1.0, "zoom_end": 1.4, "pan_start": (0.3, 0.7), "pan_end": (0.8, 0.2)}),
        "scene_013.webp": ("shake", {"intensity": 10, "zoom_factor": 1.3}),
        "scene_014.webp": ("zoom_out", {"zoom_factor": 1.7}),
        "scene_015.webp": ("pan_left", {"zoom_factor": 1.4, "distance": 0.5}),
        "scene_016.webp": ("fade_in", {"duration": 4.0}),
        "scene_017.webp": ("mirror_y", {}),
        "scene_018.webp": ("kenburns", {"zoom_start": 1.3, "zoom_end": 1.1, "pan_start": (0.1, 0.9), "pan_end": (0.9, 0.1)}),
        "scene_019.webp": ("pan_right", {"zoom_factor": 1.35, "distance": 0.3}),
        "scene_020.webp": ("zoom_in", {"zoom_factor": 1.6}),
        "scene_021.webp": ("shake_zoom_combo", {"shake_duration": 2.0, "intensity": 8, "zoom_factor_shake": 1.2, "zoom_in_factor": 1.4, "zoom_out_factor": 1.6}),
        "scene_022.webp": ("shake_kenburns_combo", {"shake_duration": 1.5, "intensity": 10, "zoom_factor_shake": 1.15, "kenburns_zoom_start": 1.0, "kenburns_zoom_end": 1.4, "kenburns_pan_start": (0.2, 0.2), "kenburns_pan_end": (0.7, 0.6)}),
        # Continúa con más asignaciones si necesitas...
        # Para las imágenes no especificadas, se usará "zoom_in" como efecto por defecto
    }
    
    # Efecto por defecto para imágenes no especificadas
    efecto_por_defecto = ("zoom_in", {"zoom_factor": 1.3})
    
    print("🎯 ASIGNACIÓN MANUAL DE EFECTOS - 12 SEGUNDOS POR IMAGEN")
    print("=" * 60)
    print(f"📁 Imágenes encontradas: {len(image_files)}")
    print(f"🎯 Asignaciones manuales: {len(asignaciones_manuales)}")
    print(f"⏱️ Duración por clip: {DURACION_CLIP} segundos")
    print(f"⏱️ Duración total estimada: {len(image_files) * DURACION_CLIP:.1f} segundos")
    print(f"💾 Guardando en: {output_path}")
    print("")
    
    clips_procesados = []
    resumen_efectos = {}
    
    for i, image_file in enumerate(image_files):
        # Obtener la asignación para esta imagen
        if image_file.name in asignaciones_manuales:
            efecto_nombre, efecto_params = asignaciones_manuales[image_file.name]
            asignacion_tipo = "📌 Manual"
        else:
            efecto_nombre, efecto_params = efecto_por_defecto
            asignacion_tipo = "🔄 Por defecto"
        
        # Contar efectos para el resumen
        if efecto_nombre not in resumen_efectos:
            resumen_efectos[efecto_nombre] = 0
        resumen_efectos[efecto_nombre] += 1
        
        print(f"📸 Imagen {i+1:2d}/{len(image_files)}: {image_file.name}")
        print(f"   ✨ Efecto: {efecto_nombre}")
        print(f"   {asignacion_tipo}")
        print(f"   ⏱️ Duración: {DURACION_CLIP}s")
        
        try:
            # Crear clip base de 12 segundos
            clip = ImageClip(str(image_file)).set_duration(DURACION_CLIP).set_fps(24)
            
            # Aplicar el efecto asignado
            clip_con_efecto = EfectosVideo.apply_effect(clip, efecto_nombre, **efecto_params)
            
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
        print("⏳ Esto puede tardar varios minutos...")
        
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
        print("🎉 ¡VIDEO CON ASIGNACIÓN MANUAL CREADO!")
        print("=" * 50)
        print(f"📁 Archivo: {output_path}")
        print(f"⏱️ Duración final: {len(image_files) * DURACION_CLIP:.1f} segundos")
        print(f"📊 Imágenes procesadas: {len(image_files)}")
        print(f"✨ Efectos aplicados: {len(clips_procesados)}")
        print(f"📏 Resolución: 1920x1080 @ 24fps")
        print("")
        
        # Mostrar resumen de efectos utilizados
        print("📋 RESUMEN DE EFECTOS UTILIZADOS:")
        print("-" * 40)
        for efecto, cantidad in sorted(resumen_efectos.items()):
            print(f"  • {efecto}: {cantidad} imagen(es)")
        
        print("")
        print("💡 CÓMO PERSONALIZAR ESTE SCRIPT:")
        print("   1. Edita el diccionario 'asignaciones_manuales' en el código")
        print("   2. Especifica qué efecto quieres para cada imagen")
        print("   3. Ajusta los parámetros de cada efecto según tus necesidades")
        print("   4. Las imágenes no especificadas usarán el efecto por defecto")
        
    except Exception as e:
        print(f"❌ Error creando video final: {e}")
        return

def mostrar_efectos_disponibles():
    """Muestra todos los efectos disponibles con sus parámetros."""
    
    efectos_info = {
        "kenburns": {
            "descripcion": "Zoom y paneo combinado (efecto Ken Burns)",
            "parametros": "zoom_start, zoom_end, pan_start, pan_end"
        },
        "zoom_in": {
            "descripcion": "Zoom hacia adelante progresivo", 
            "parametros": "zoom_factor"
        },
        "zoom_out": {
            "descripcion": "Zoom hacia atrás progresivo",
            "parametros": "zoom_factor"
        },
        "pan_left": {
            "descripcion": "Movimiento de cámara hacia la izquierda",
            "parametros": "zoom_factor, distance"
        },
        "pan_right": {
            "descripcion": "Movimiento de cámara hacia la derecha", 
            "parametros": "zoom_factor, distance"
        },
        "pan_up": {
            "descripcion": "Movimiento de cámara hacia arriba",
            "parametros": "zoom_factor"
        },
        "pan_down": {
            "descripcion": "Movimiento de cámara hacia abajo",
            "parametros": "zoom_factor"
        },
        "shake": {
            "descripcion": "Efecto de temblor/vibración",
            "parametros": "intensity, zoom_factor"
        },
        "shake_zoom_combo": {
            "descripcion": "Temblor inicial + zoom in/out combinado",
            "parametros": "shake_duration, intensity, zoom_factor_shake, zoom_in_factor, zoom_out_factor"
        },
        "shake_kenburns_combo": {
            "descripcion": "Temblor inicial + efecto Ken Burns elegante",
            "parametros": "shake_duration, intensity, zoom_factor_shake, kenburns_zoom_start, kenburns_zoom_end, kenburns_pan_start, kenburns_pan_end"
        },
        "fade_in": {
            "descripcion": "Aparición gradual desde negro",
            "parametros": "duration"
        },
        "fade_out": {
            "descripcion": "Desvanecimiento gradual a negro",
            "parametros": "duration"
        },
        "mirror_x": {
            "descripcion": "Espejo horizontal",
            "parametros": "ninguno"
        },
        "mirror_y": {
            "descripcion": "Espejo vertical", 
            "parametros": "ninguno"
        },
        "rotate_180": {
            "descripcion": "Rotación 180 grados",
            "parametros": "ninguno"
        }
    }
    
    print("✨ EFECTOS DISPONIBLES")
    print("=" * 50)
    for i, (efecto, info) in enumerate(efectos_info.items(), 1):
        print(f"{i:2d}. {efecto}")
        print(f"    📝 {info['descripcion']}")
        print(f"    ⚙️ Parámetros: {info['parametros']}")
        print("")

def main():
    """Función principal."""
    print("🎯 ASIGNACIÓN MANUAL DE EFECTOS")
    print("=" * 40)
    print("1. Ver efectos disponibles")
    print("2. Crear video con asignación manual")
    print("")
    
    opcion = input("Selecciona una opción (1/2) [2]: ").strip()
    
    if opcion == "1":
        mostrar_efectos_disponibles()
    else:
        crear_video_con_asignacion_manual()

if __name__ == "__main__":
    main() 