import asyncio
import edge_tts
import os
from pathlib import Path
import tempfile

async def _generate_audio_chunk(text: str, voice: str, rate: str = "+0%", volume: str = "+0%", pitch: str = "+0Hz", output_file: str = None) -> str:
    """Genera un archivo de audio para un chunk de texto usando Edge TTS."""
    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume, pitch=pitch)
    if not output_file:
        output_file = tempfile.mktemp(suffix=".mp3")
    await communicate.save(output_file)
    return output_file

def generate_edge_tts_audio(text: str, voice: str = "es-ES-AlvaroNeural", rate: str = "+0%", pitch: str = "+0Hz", output_dir: str = "audio") -> str:
    """
    Genera un archivo de audio a partir de texto usando Edge TTS.
    
    Args:
        text (str): Texto a convertir en audio
        voice (str): Voz a utilizar (por defecto es-ES-AlvaroNeural)
        rate (str): Velocidad de habla (formato: +X% o -X%)
        pitch (str): Tono de voz (formato: +XHz o -XHz)
        output_dir (str): Directorio donde guardar el audio
    
    Returns:
        str: Ruta al archivo de audio generado
    """
    # Crear directorio de salida si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Dividir el texto en chunks de 4000 caracteres
    chunk_size = 4000
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
    
    # Generar un nombre de archivo temporal único
    temp_files = []
    output_file = os.path.join(output_dir, f"audio_{hash(text)}.mp3")
    
    try:
        # Generar audio para cada chunk
        for i, chunk in enumerate(chunks):
            temp_file = tempfile.mktemp(suffix=f"_chunk_{i}.mp3")
            asyncio.run(_generate_audio_chunk(
                chunk,
                voice,
                rate=rate,
                pitch=pitch,
                output_file=temp_file
            ))
            temp_files.append(temp_file)
        
        # Si hay más de un chunk, concatenarlos
        if len(temp_files) > 1:
            from moviepy.editor import concatenate_audioclips, AudioFileClip
            clips = [AudioFileClip(f) for f in temp_files]
            final_clip = concatenate_audioclips(clips)
            final_clip.write_audiofile(output_file)
            final_clip.close()
            for clip in clips:
                clip.close()
        else:
            # Si solo hay un chunk, simplemente renombrar el archivo
            import shutil
            shutil.move(temp_files[0], output_file)
        
        return output_file
    
    finally:
        # Limpiar archivos temporales
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

async def list_voices():
    """Lista todas las voces disponibles en Edge TTS."""
    try:
        return await edge_tts.list_voices()
    except Exception as e:
        return [{"Name": "es-ES-AlvaroNeural", "Locale": "es-ES"}]  # Voz por defecto si falla

class AudioServices:
    def __init__(self):
        # Inicialización de servicios de audio
        pass
    
    def generate_voice(self, text):
        # Lógica para generar voz
        pass
    
    def transcribe_audio(self, audio_file):
        # Lógica para transcribir audio
        pass 