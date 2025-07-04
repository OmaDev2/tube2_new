#!/usr/bin/env python3
import json
import os

project_path = "projects/el_misterio_de_san_raimundo_y_el_milagro_de_cruzar__4990ace7"

# Leer el script completo
script_file = os.path.join(project_path, "script.txt")
with open(script_file, 'r', encoding='utf-8') as f:
    script_content = f.read()

# Leer la transcripción
transcription_file = os.path.join(project_path, "transcription.json")
with open(transcription_file, 'r', encoding='utf-8') as f:
    transcription_data = json.load(f)

# Extraer todo el texto transcrito
transcribed_text = ""
for segment in transcription_data.get('segments', []):
    transcribed_text += segment.get('text', '') + " "

print("=== COMPARACIÓN DE CONTENIDO ===")
print(f"📄 Script original:")
print(f"  - Caracteres: {len(script_content)}")
print(f"  - Palabras aprox: {len(script_content.split())}")

print(f"\n🎤 Texto transcrito:")
print(f"  - Caracteres: {len(transcribed_text)}")
print(f"  - Palabras aprox: {len(transcribed_text.split())}")

# Calcular porcentaje completado
completion_percentage = (len(transcribed_text) / len(script_content)) * 100
print(f"\n📊 Progreso de transcripción: {completion_percentage:.1f}%")

# Mostrar los últimos caracteres de cada uno
print(f"\n📝 Últimas palabras del script:")
print(f"  '{script_content[-200:]}'")

print(f"\n🎤 Últimas palabras transcritas:")
print(f"  '{transcribed_text[-200:]}'")

# Verificar en qué parte del script se detuvo
script_words = script_content.split()
transcribed_words = transcribed_text.split()

# Buscar dónde se detuvo la transcripción
last_transcribed_phrase = " ".join(transcribed_words[-10:]).strip()
script_position = script_content.find(last_transcribed_phrase)

if script_position != -1:
    progress_chars = script_position + len(last_transcribed_phrase)
    progress_percentage = (progress_chars / len(script_content)) * 100
    print(f"\n🎯 La transcripción se detuvo aproximadamente en el {progress_percentage:.1f}% del script")
else:
    print(f"\n❓ No se pudo determinar exactamente dónde se detuvo la transcripción")

# Verificar configuración del proyecto
project_info_file = os.path.join(project_path, "project_info.json")
with open(project_info_file, 'r', encoding='utf-8') as f:
    project_info = json.load(f)

print(f"\n⚙️ Información del proyecto:")
print(f"  - Status: {project_info.get('status', 'unknown')}")
print(f"  - Error message: {project_info.get('error_message', 'None')}")