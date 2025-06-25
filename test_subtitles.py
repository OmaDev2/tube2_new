#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de prueba para verificar la funcionalidad de los subtítulos.
Permite probar directamente la función add_hardcoded_subtitles sin generar todo el vídeo.
"""

import os
import json
import logging
from pathlib import Path
import argparse
from utils.video_services import VideoServices

# Configurar logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_test_segments():
    """Crear segmentos de prueba para subtítulos"""
    return [
        {"text": "Este es un subtítulo de prueba 1", "start": 0.0, "end": 2.0},
        {"text": "Este es un subtítulo de prueba 2", "start": 2.0, "end": 4.0},
        {"text": "Subtítulo con palabras más largas para probar", "start": 4.0, "end": 6.0},
        {"text": "Último subtítulo de prueba", "start": 6.0, "end": 8.0}
    ]

def main():
    parser = argparse.ArgumentParser(description='Prueba de subtítulos para VideoTube')
    parser.add_argument('--video', '-v', type=str, help='Ruta al vídeo de prueba (mp4)')
    parser.add_argument('--font', '-f', type=str, default="Arial", help='Fuente a usar')
    parser.add_argument('--font-size', type=int, default=40, help='Tamaño base de la fuente (40)')
    parser.add_argument('--color', '-c', type=str, default="white", help='Color del texto')
    parser.add_argument('--stroke', '-s', type=str, default="black", help='Color del borde')
    parser.add_argument('--stroke-width', '-w', type=int, default=2, help='Grosor del borde (2-15)')
    parser.add_argument('--position', '-p', type=str, default="bottom", 
                       choices=["top", "center", "bottom"], help='Posición de los subtítulos')
    parser.add_argument('--with-bg', action='store_true', help='Usar fondo semi-transparente')
    parser.add_argument('--bg-opacity', type=float, default=0.5, help='Opacidad del fondo (0.0-1.0)')
    parser.add_argument('--segments', type=str, help='Archivo JSON con segmentos de subtítulos')
    parser.add_argument('--compare', action='store_true', help='Generar varios videos con distintas configuraciones')
    parser.add_argument('--show-fonts', action='store_true', help='Mostrar fuentes disponibles')
    args = parser.parse_args()

    # Mostrar fuentes disponibles si se solicita
    if args.show_fonts:
        try:
            from utils.subtitle_utils import get_available_fonts
            fonts = get_available_fonts()
            print("\n=== Fuentes Disponibles ===")
            for i, font in enumerate(fonts):
                print(f"{i+1}. {font}")
            print("==========================\n")
            return 0
        except ImportError:
            logger.error("No se pudo importar get_available_fonts")
            return 1

    # Verificar que existe el vídeo
    video_path = args.video
    if not video_path or not os.path.exists(video_path):
        logger.error(f"Vídeo no encontrado: {video_path}")
        print("Debe proporcionar una ruta a un archivo de vídeo válido con --video")
        return 1

    # Crear directorio de salida si no existe
    output_dir = Path('test_output')
    output_dir.mkdir(exist_ok=True)
    
    # Obtener segmentos
    segments = []
    if args.segments and os.path.exists(args.segments):
        # Cargar desde archivo
        try:
            with open(args.segments, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    segments = data
                elif isinstance(data, dict) and 'segments' in data:
                    segments = data['segments']
                logger.info(f"Cargados {len(segments)} segmentos desde {args.segments}")
        except Exception as e:
            logger.error(f"Error cargando segmentos: {e}")
            segments = create_test_segments()
    else:
        # Usar segmentos de prueba
        segments = create_test_segments()
        logger.info(f"Usando {len(segments)} segmentos de prueba")

    # Modo comparación
    if args.compare:
        return generate_comparison_videos(video_path, segments, output_dir, args)
    
    # Modo estándar (un solo video)
    # Nombre del archivo de salida incluye algunos parámetros
    output_name = f"sub_{Path(video_path).stem}"
    if args.with_bg:
        output_name += f"_bg{args.bg_opacity}"
    if args.stroke_width > 0:
        output_name += f"_sw{args.stroke_width}"
    if args.font != "Arial":
        output_name += f"_{args.font.replace(' ', '')}"
    output_path = output_dir / f"{output_name}.mp4"
    
    # Mostrar configuración
    logger.info(f"VIDEO: {video_path}")
    logger.info(f"FUENTE: {args.font}")
    logger.info(f"TAMAÑO FUENTE: {args.font_size}px")
    logger.info(f"COLOR: {args.color}")
    logger.info(f"BORDE: {args.stroke}")
    logger.info(f"GROSOR BORDE: {args.stroke_width}px")
    logger.info(f"POSICIÓN: {args.position}")
    logger.info(f"FONDO: {'Sí' if args.with_bg else 'No'}")
    if args.with_bg:
        logger.info(f"OPACIDAD FONDO: {args.bg_opacity:.1f}")
    logger.info(f"SALIDA: {output_path}")
    
    # Aplicar subtítulos
    return process_video(
        video_path, segments, output_path, args.font, args.font_size,
        args.color, args.stroke, args.stroke_width, args.position,
        args.with_bg, args.bg_opacity
    )

def process_video(video_path, segments, output_path, font, font_size, 
                  color, stroke_color, stroke_width, position, 
                  with_bg=False, bg_opacity=0.5):
    """Procesa un video con los parámetros dados"""
    try:
        video_service = VideoServices()
        
        # Verificar si se actualizó la clase para incluir el fondo
        if with_bg and hasattr(video_service, 'add_hardcoded_subtitles_with_bg'):
            # Si existe la función con fondo
            result = video_service.add_hardcoded_subtitles_with_bg(
                video_path=video_path,
                segments=segments,
                output_path=str(output_path),
                font=font,
                font_size=font_size,
                color=color,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
                position=position,
                bg_opacity=bg_opacity
            )
        else:
            # Función regular
            if with_bg:
                logger.warning("La opción de fondo no está disponible en esta versión. Usando versión estándar.")
            result = video_service.add_hardcoded_subtitles(
                video_path=video_path,
                segments=segments,
                output_path=str(output_path),
                font=font,
                font_size=font_size,
                color=color,
                stroke_color=stroke_color,
                stroke_width=stroke_width,
                position=position
            )
        
        if os.path.exists(result):
            logger.info(f"✅ Vídeo con subtítulos generado correctamente: {result}")
            print(f"\n¡ÉXITO! Vídeo con subtítulos guardado en:\n{result}\n")
            return 0
        else:
            logger.error(f"❌ No se generó el archivo de salida")
            return 1
    except Exception as e:
        logger.error(f"❌ Error generando subtítulos: {e}", exc_info=True)
        return 1

def generate_comparison_videos(video_path, segments, output_dir, args):
    """Genera varios videos con distintas configuraciones para comparar"""
    logger.info("Modo comparación: generando varios videos con distintas configuraciones")
    
    # Nombre base para los videos de comparación
    base_name = f"compare_{Path(video_path).stem}"
    
    # Configuraciones a probar
    configs = [
        # Sin fondo, diferentes grosores de borde
        {"name": "nobg_stroke2", "with_bg": False, "stroke_width": 2},
        {"name": "nobg_stroke4", "with_bg": False, "stroke_width": 4},
        {"name": "nobg_stroke8", "with_bg": False, "stroke_width": 8},
        
        # Con fondo, distintas opacidades
        {"name": "bg0.3", "with_bg": True, "bg_opacity": 0.3, "stroke_width": 2},
        {"name": "bg0.5", "with_bg": True, "bg_opacity": 0.5, "stroke_width": 2},
        {"name": "bg0.7", "with_bg": True, "bg_opacity": 0.7, "stroke_width": 2},
        
        # Distintas fuentes (si están disponibles)
        {"name": "font_impact", "font": "Impact", "with_bg": False, "stroke_width": 3},
        {"name": "font_arial", "font": "Arial", "with_bg": False, "stroke_width": 3},
        {"name": "font_courier", "font": "Courier", "with_bg": False, "stroke_width": 3},
    ]
    
    results = []
    
    for i, config in enumerate(configs):
        # Combinar con los valores por defecto del usuario
        full_config = {
            "font": args.font,
            "font_size": args.font_size,
            "color": args.color,
            "stroke_color": args.stroke,
            "stroke_width": args.stroke_width,
            "position": args.position,
            "with_bg": args.with_bg,
            "bg_opacity": args.bg_opacity
        }
        
        # Actualizar con los valores específicos de esta configuración
        full_config.update(config)
        
        # Nombre del archivo de salida
        output_path = output_dir / f"{base_name}_{config['name']}.mp4"
        
        logger.info(f"\n[{i+1}/{len(configs)}] Procesando configuración: {config['name']}")
        
        # Procesar video con esta configuración
        result = process_video(
            video_path, segments, output_path,
            full_config["font"], full_config["font_size"],
            full_config["color"], full_config["stroke_color"], 
            full_config["stroke_width"], full_config["position"],
            full_config["with_bg"], full_config["bg_opacity"]
        )
        
        results.append({
            "config": config["name"],
            "success": result == 0,
            "path": str(output_path) if result == 0 else None
        })
    
    # Mostrar resumen
    print("\n=== RESUMEN DE VIDEOS GENERADOS ===")
    successful = [r for r in results if r["success"]]
    
    if successful:
        print(f"✅ {len(successful)}/{len(configs)} videos generados correctamente:")
        for r in successful:
            print(f"  - {r['config']}: {r['path']}")
    else:
        print("❌ No se generó ningún video correctamente.")
    
    print("====================================\n")
    
    return 0 if successful else 1

if __name__ == "__main__":
    exit(main()) 