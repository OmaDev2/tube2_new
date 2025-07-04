#!/usr/bin/env python3
import json
import os

project_path = "projects/el_misterio_de_san_raimundo_y_el_milagro_de_cruzar__4990ace7"
transcription_file = os.path.join(project_path, "transcription.json")

print("=== ANÁLISIS DE TRANSCRIPCIÓN ===")

# Verificar si el archivo existe
if not os.path.exists(transcription_file):
    print(f"❌ ERROR: No se encuentra el archivo {transcription_file}")
    exit(1)

# Leer el archivo de transcripción
try:
    with open(transcription_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"✅ Archivo de transcripción cargado correctamente")
    
    # Analizar metadata
    metadata = data.get('metadata', {})
    print(f"\n📊 METADATA:")
    for key, value in metadata.items():
        print(f"  - {key}: {value}")
    
    # Analizar segmentos
    segments = data.get('segments', [])
    print(f"\n📝 SEGMENTOS:")
    print(f"  - Total de segmentos: {len(segments)}")
    
    if segments:
        first_segment = segments[0]
        last_segment = segments[-1]
        
        print(f"  - Primer segmento:")
        print(f"    * Tiempo: {first_segment.get('start', 0)} - {first_segment.get('end', 0)} segundos")
        print(f"    * Texto: '{first_segment.get('text', '')[:100]}...'")
        
        print(f"  - Último segmento:")
        print(f"    * Tiempo: {last_segment.get('start', 0)} - {last_segment.get('end', 0)} segundos")
        print(f"    * Texto: '{last_segment.get('text', '')}'")
        
        # Verificar si hay gaps en la transcripción
        total_duration = last_segment.get('end', 0)
        print(f"\n⏱️  DURACIÓN:")
        print(f"  - Duración de la transcripción: {total_duration} segundos ({total_duration/60:.1f} minutos)")
        
        # Verificar gaps
        gaps = []
        for i in range(1, len(segments)):
            prev_end = segments[i-1].get('end', 0)
            curr_start = segments[i].get('start', 0)
            gap = curr_start - prev_end
            if gap > 1.0:  # Gap mayor a 1 segundo
                gaps.append((i, prev_end, curr_start, gap))
        
        if gaps:
            print(f"\n⚠️  GAPS DETECTADOS ({len(gaps)} gaps > 1 segundo):")
            for i, prev_end, curr_start, gap in gaps[:5]:  # Mostrar solo los primeros 5
                print(f"  - Segmento {i}: gap de {gap:.2f}s entre {prev_end:.2f}s y {curr_start:.2f}s")
            if len(gaps) > 5:
                print(f"  - ... y {len(gaps) - 5} gaps más")
        else:
            print(f"✅ No se detectaron gaps significativos")
        
        # Verificar segmentos vacíos
        empty_segments = [i for i, seg in enumerate(segments) if not seg.get('text', '').strip()]
        if empty_segments:
            print(f"\n⚠️  SEGMENTOS VACÍOS: {len(empty_segments)} segmentos sin texto")
        else:
            print(f"✅ Todos los segmentos tienen texto")
            
    else:
        print("❌ ERROR: No hay segmentos en la transcripción")

except json.JSONDecodeError as e:
    print(f"❌ ERROR: El archivo JSON está corrupto: {e}")
except Exception as e:
    print(f"❌ ERROR: {e}")

# Verificar duración del audio
audio_file = os.path.join(project_path, "audio", "audio_fish_8604568204045335315.mp3")
if os.path.exists(audio_file):
    print(f"\n🎵 ARCHIVO DE AUDIO:")
    print(f"  - Archivo: {audio_file}")
    print(f"  - Tamaño: {os.path.getsize(audio_file) / 1024 / 1024:.1f} MB")
    
    # Intentar obtener duración con ffprobe si está disponible
    import subprocess
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', 
            '-of', 'default=noprint_wrappers=1:nokey=1', audio_file
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            audio_duration = float(result.stdout.strip())
            print(f"  - Duración del audio: {audio_duration:.2f} segundos ({audio_duration/60:.1f} minutos)")
            
            if segments:
                transcription_duration = last_segment.get('end', 0)
                if audio_duration > transcription_duration + 10:  # Más de 10 segundos de diferencia
                    print(f"⚠️  POSIBLE PROBLEMA: El audio es {audio_duration - transcription_duration:.1f} segundos más largo que la transcripción")
                else:
                    print(f"✅ La duración del audio y transcripción coinciden aproximadamente")
        else:
            print(f"  - No se pudo obtener la duración (ffprobe no disponible)")
    except:
        print(f"  - No se pudo obtener la duración (ffprobe no disponible)")
else:
    print(f"\n❌ ERROR: No se encuentra el archivo de audio: {audio_file}")