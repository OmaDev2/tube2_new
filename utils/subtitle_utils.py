# utils/subtitle_utils.py (o añadir a utils/video_services.py)

import math
from typing import List, Dict

def split_subtitle_segments(segments: List[Dict], max_words: int = 7, max_chars: int = 40) -> List[Dict]:
    """
    Divide segmentos de subtítulos largos en otros más cortos basados en número de palabras o caracteres.
    Ajusta los timestamps de forma aproximada.

    Args:
        segments: Lista de segmentos originales [{'text': str, 'start': float, 'end': float}, ...]
        max_words: Número máximo de palabras por nuevo segmento.
        max_chars: Número máximo de caracteres por nuevo segmento (aproximado, para evitar cortes feos).

    Returns:
        Nueva lista de segmentos más cortos.
    """
    new_segments = []
    word_split_char = " " # Asumir división por espacio

    for seg in segments:
        original_text = seg['text'].strip()
        if not original_text:
            continue

        words = original_text.split(word_split_char)
        num_words = len(words)
        segment_duration = seg['end'] - seg['start']

        if num_words == 0 or segment_duration <= 0:
            continue

        # Estimar duración por palabra (aproximado)
        duration_per_word = segment_duration / num_words

        current_chunk_words = []
        current_chunk_start_time = seg['start']
        word_count_in_chunk = 0

        for i, word in enumerate(words):
            current_chunk_words.append(word)
            word_count_in_chunk += 1
            current_line_chars = len(word_split_char.join(current_chunk_words))

            # Condición para cortar: se excede el número de palabras O el número de caracteres,
            # Y no estamos justo al final del segmento original.
            should_cut = (word_count_in_chunk >= max_words or current_line_chars >= max_chars) and (i < num_words - 1)

            if should_cut:
                # Calcular tiempo de fin aproximado para este chunk
                current_chunk_end_time = seg['start'] + (i + 1) * duration_per_word
                # Asegurar que el fin no exceda el fin original del segmento
                current_chunk_end_time = min(current_chunk_end_time, seg['end'])

                new_segments.append({
                    'text': word_split_char.join(current_chunk_words),
                    'start': current_chunk_start_time,
                    'end': current_chunk_end_time
                })

                # Reiniciar para el siguiente chunk
                current_chunk_words = []
                word_count_in_chunk = 0
                # El siguiente chunk empieza donde terminó este
                current_chunk_start_time = current_chunk_end_time

        # Añadir las palabras restantes como último chunk del segmento original
        if current_chunk_words:
            new_segments.append({
                'text': word_split_char.join(current_chunk_words),
                'start': current_chunk_start_time,
                # El último chunk termina cuando termina el segmento original
                'end': seg['end']
            })

    return new_segments


def get_available_fonts() -> List[str]:
    """
    Obtiene una lista de fuentes del sistema utilizando matplotlib o falla de manera elegante.
    Especialmente mejorada para funcionar correctamente en macOS.
    """
    fallback_fonts = ["Arial", "Verdana", "Tahoma", "Trebuchet MS", "Times New Roman", 
                    "Georgia", "Garamond", "Courier New", "Brush Script MT", 
                    "DejaVu Sans", "Liberation Sans", "Helvetica", "Menlo", "Monaco", "SF Pro"]
    
    # Fuentes específicas para macOS que suelen estar disponibles
    mac_fonts = ["SF Pro", "San Francisco", "Helvetica Neue", "Avenir", "Menlo", 
                "Monaco", "Courier", "Palatino", "Times", "Helvetica"]
    
    # Añadir fuentes de Mac a las fallback
    fallback_fonts.extend([f for f in mac_fonts if f not in fallback_fonts])
    
    try:
        import matplotlib.font_manager
        import platform
        
        # Verificar si estamos en macOS para un manejo especial
        is_macos = platform.system() == 'Darwin'
        
        # En macOS, intentar un método alternativo primero
        if is_macos:
            try:
                import subprocess
                # Usar el comando fc-list para obtener fuentes disponibles en macOS
                output = subprocess.check_output(['fc-list', ':', 'family']).decode('utf-8')
                font_names = sorted(list(set([line.strip() for line in output.split('\n') if line.strip()])))
                if font_names:
                    print(f"INFO: Encontradas {len(font_names)} fuentes del sistema vía fc-list en macOS.")
                    combined_fonts = sorted(list(set(fallback_fonts + font_names)))
                    return combined_fonts
            except (subprocess.SubprocessError, FileNotFoundError):
                # Si fc-list falla, continuamos con matplotlib
                print("INFO: fc-list no disponible, intentando con matplotlib...")
                pass
        
        # Intentar método matplotlib (independiente del SO)
        font_paths = matplotlib.font_manager.findSystemFonts(fontpaths=None, fontext='ttf')
        
        # Evitar el error de tamaño de píxel inválido no intentando cargar las propiedades
        # sino simplemente extrayendo nombres de los archivos
        font_names = []
        for font_path in font_paths:
            try:
                name = matplotlib.font_manager.FontProperties(fname=font_path).get_name()
                font_names.append(name)
            except Exception:
                # Si falla al obtener el nombre, intentar extraer del nombre del archivo
                try:
                    import os
                    filename = os.path.basename(font_path)
                    # Eliminar extensión y caracteres especiales
                    simple_name = os.path.splitext(filename)[0].replace('-', ' ').replace('_', ' ')
                    font_names.append(simple_name)
                except:
                    continue
        
        font_names = sorted(list(set(font_names)))
        
        # Combinar con fallbacks y eliminar duplicados
        combined_fonts = sorted(list(set(fallback_fonts + font_names)))
        
        if not font_names:
            print("WARN: Matplotlib no encontró fuentes del sistema, usando lista fallback.")
            return fallback_fonts
            
        print(f"INFO: Encontradas {len(font_names)} fuentes del sistema vía Matplotlib.")
        return combined_fonts
        
    except ImportError:
        print("WARN: Matplotlib no encontrado. Usando lista de fuentes fallback.")
        return fallback_fonts
    except Exception as e:
        print(f"WARN: Error obteniendo fuentes del sistema: {e}. Usando lista fallback.")
        return fallback_fonts