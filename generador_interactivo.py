#!/usr/bin/env python3
"""
GENERADOR INTERACTIVO DE PROMPTS HISTÓRICOS
Flujo completo: Script → Transcripción → Escenas → Prompts
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict

# Agregar la ruta de utils al path
sys.path.append(str(Path(__file__).parent))

from utils.scene_generator import SceneGenerator
from utils.ai_services import AIServices, extract_historical_context

class GeneradorInteractivo:
    def __init__(self):
        self.ai_services = AIServices()
        self.scene_generator = SceneGenerator()
        
    def mostrar_banner(self):
        print("=" * 80)
        print("🎬  GENERADOR INTERACTIVO DE PROMPTS HISTÓRICOS")
        print("=" * 80)
        print("📝 Flujo: Script → Transcripción → Escenas Narrativas → Prompts")
        print("🧠 Usa el nuevo algoritmo de segmentación inteligente")
        print("⏱️  Optimizado para imágenes de 10-12 segundos")
        print("-" * 80)
    
    def solicitar_script(self) -> str:
        print("\n📖 PASO 1: SCRIPT DE ENTRADA")
        print("-" * 40)
        print("Pega tu script histórico aquí (Enter doble para terminar):")
        print("Ejemplo: 'Santa Teresa de Ávila escribió Las Moradas en su celda...'")
        print()
        
        lines = []
        while True:
            try:
                line = input()
                if line.strip() == "" and len(lines) > 0:
                    break
                lines.append(line)
            except KeyboardInterrupt:
                print("\n❌ Cancelado por el usuario")
                sys.exit(0)
        
        script = "\n".join(lines).strip()
        
        if not script:
            print("❌ Error: No se proporcionó ningún script")
            return self.solicitar_script()
        
        print(f"\n✅ Script recibido ({len(script)} caracteres)")
        return script
    
    def simular_transcripcion(self, script: str) -> List[Dict]:
        print("\n🎙️  PASO 2: SIMULACIÓN DE TRANSCRIPCIÓN")
        print("-" * 40)
        
        # Dividir el script en frases
        sentences = re.split(r'(?<=[.!?])\s+', script)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # Estimar duración por frase (promedio 3-4 segundos por frase)
        transcription_segments = []
        current_time = 0.0
        
        for sentence in sentences:
            # Estimar duración basada en longitud (más realista)
            words = len(sentence.split())
            duration = max(2.0, min(6.0, words * 0.4))  # 2-6 segundos por frase
            
            transcription_segments.append({
                "text": sentence,
                "start": current_time,
                "end": current_time + duration
            })
            current_time += duration
        
        total_duration = current_time
        
        print(f"📊 Transcripción simulada:")
        print(f"   • {len(transcription_segments)} segmentos")
        print(f"   • Duración total: {total_duration:.1f} segundos")
        print(f"   • Promedio por segmento: {total_duration/len(transcription_segments):.1f}s")
        
        return transcription_segments
    
    def extraer_contexto_historico(self, script: str) -> Dict:
        print("\n🏛️  PASO 3: EXTRACCIÓN DE CONTEXTO HISTÓRICO")
        print("-" * 40)
        
        # Detectar título/personaje principal
        lines = script.split('\n')
        titulo = "Contenido histórico"
        
        # Buscar nombres de santos, personajes históricos, etc.
        historical_names = [
            'santa teresa', 'san ignacio', 'leonardo da vinci', 'san francisco',
            'san blas', 'napoleon', 'juana de arco', 'san juan', 'santa mónica'
        ]
        
        for name in historical_names:
            if name.lower() in script.lower():
                titulo = name.title()
                break
        
        print(f"🔍 Detectando contexto histórico para: '{titulo}'")
        print("⏳ Analizando con IA (puede tardar 10-20 segundos)...")
        print("   📡 Enviando consulta al modelo de IA...")
        
        try:
            import time
            start_time = time.time()
            
            # Mostrar progreso simulado mientras se procesa
            print("   🧠 Modelo analizando texto histórico...", end="", flush=True)
            
            contexto_historico = extract_historical_context(titulo, script)
            
            elapsed_time = time.time() - start_time
            print(f" ✅ ({elapsed_time:.1f}s)")
            
            print("\n📋 Contexto histórico extraído:")
            for key, value in contexto_historico.items():
                print(f"   • {key}: {value}")
            
            return contexto_historico
            
        except Exception as e:
            print(f"\n⚠️  Error extrayendo contexto: {e}")
            print("🔄 Usando contexto histórico de fallback...")
            return self._contexto_fallback()
    
    def _contexto_fallback(self) -> Dict:
        return {
            "periodo_historico": "Siglo XVI",
            "ubicacion": "España",
            "contexto_cultural": "Renacimiento español",
            "fecha_nacimiento": "1515",
            "fecha_muerte": "1582", 
            "edad_personaje": "45"
        }
    
    def generar_escenas_narrativas(self, transcription_segments: List[Dict]) -> List[Dict]:
        print("\n🎬 PASO 4: GENERACIÓN DE ESCENAS NARRATIVAS")
        print("-" * 40)
        print("🧠 Usando algoritmo de segmentación inteligente...")
        
        # Usar el nuevo algoritmo mejorado
        scenes = self.scene_generator._create_semantic_scenes(
            transcription_segments, 
            target_duration=11.0
        )
        
        print(f"\n📊 Escenas generadas: {len(scenes)}")
        
        # Mostrar resumen
        for i, scene in enumerate(scenes):
            status_icon = "✅" if scene['duration'] <= 12 else "⚠️" if scene['duration'] <= 15 else "❌"
            unit_info = ""
            if 'narrative_unit' in scene and 'visual_moment' in scene:
                unit_info = f" [U{scene['narrative_unit']}-M{scene['visual_moment']}]"
            
            print(f"   {status_icon} Escena {i+1}: {scene['duration']:.1f}s{unit_info}")
            print(f"      📝 {scene['text'][:60]}...")
        
        return scenes
    
    def generar_prompts_historicos(self, scenes: List[Dict], contexto_historico: Dict) -> List[Dict]:
        print("\n🎨 PASO 5: GENERACIÓN DE PROMPTS HISTÓRICOS")
        print("-" * 40)
        
        # Configuración de prompts de imagen
        project_info = {
            "titulo": "Video Histórico Interactivo",
            "descripcion": "Generado con algoritmo de segmentación inteligente",
            "contexto_historico": contexto_historico
        }
        
        image_prompt_config = {
            "provider": "gemini",
            "model": "models/gemini-2.5-flash-lite-preview-06-17",
            "style": "historical_realistic",
            "quality": "high",
            "aspect_ratio": "16:9"
        }
        
        print(f"⏳ Generando prompts para {len(scenes)} escenas...")
        print("   (Cada prompt puede tardar 3-5 segundos)")
        
        try:
            import time
            start_time = time.time()
            
            print("   🎨 Generando prompts con contexto histórico...", end="", flush=True)
            
            scenes_with_prompts = self.scene_generator.generate_prompts_for_scenes(
                scenes, project_info, image_prompt_config, self.ai_services
            )
            
            elapsed_time = time.time() - start_time
            print(f" ✅ ({elapsed_time:.1f}s)")
            
            print(f"✅ Prompts generados para {len(scenes_with_prompts)} escenas")
            return scenes_with_prompts
            
        except Exception as e:
            print(f"\n⚠️  Error generando prompts: {e}")
            print("🔄 Generando prompts básicos como fallback...")
            # Generar prompts básicos como fallback
            return self._generar_prompts_basicos(scenes, contexto_historico)
    
    def _generar_prompts_basicos(self, scenes: List[Dict], contexto: Dict) -> List[Dict]:
        """Genera prompts básicos como fallback"""
        for scene in scenes:
            scene['image_prompt'] = f"""
            Imagen histórica realista del {contexto['periodo_historico']} en {contexto['ubicacion']}.
            Escena: {scene['text'][:100]}...
            Estilo: pintura renacentista, iluminación natural, colores históricos auténticos.
            Edad del personaje: {contexto['edad_personaje']} años.
            """
        return scenes
    
    def mostrar_resultados_finales(self, scenes_with_prompts: List[Dict]):
        print("\n" + "="*80)
        print("🎯 RESULTADOS FINALES")
        print("="*80)
        
        total_duration = sum(scene['duration'] for scene in scenes_with_prompts)
        avg_duration = total_duration / len(scenes_with_prompts)
        
        ideal_count = sum(1 for s in scenes_with_prompts if s['duration'] <= 12)
        acceptable_count = sum(1 for s in scenes_with_prompts if 12 < s['duration'] <= 15)
        
        print(f"📊 ESTADÍSTICAS:")
        print(f"   • Total de escenas: {len(scenes_with_prompts)}")
        print(f"   • Duración total: {total_duration:.1f}s")
        print(f"   • Duración promedio: {avg_duration:.1f}s")
        print(f"   • Escenas ideales (≤12s): {ideal_count} ({ideal_count/len(scenes_with_prompts)*100:.1f}%)")
        print(f"   • Escenas aceptables (12-15s): {acceptable_count}")
        
        print(f"\n🎬 ESCENAS DETALLADAS:")
        print("-" * 80)
        
        for i, scene in enumerate(scenes_with_prompts):
            print(f"\n🎭 ESCENA {i+1} ({scene['duration']:.1f}s)")
            print(f"   ⏱️  Tiempo: {scene['start']:.1f}s - {scene['end']:.1f}s")
            
            if 'narrative_unit' in scene:
                print(f"   📖 Unidad Narrativa: {scene['narrative_unit']}, Momento Visual: {scene.get('visual_moment', 1)}")
            
            print(f"   📝 Texto: {scene['text']}")
            
            if 'image_prompt' in scene:
                prompt_preview = scene['image_prompt'][:150].replace('\n', ' ').strip()
                print(f"   🎨 Prompt: {prompt_preview}...")
            
            print("-" * 40)
    
    def guardar_resultados(self, scenes_with_prompts: List[Dict], contexto_historico: Dict):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"generacion_interactiva_{timestamp}.json"
        
        data = {
            "timestamp": timestamp,
            "contexto_historico": contexto_historico,
            "estadisticas": {
                "total_escenas": len(scenes_with_prompts),
                "duracion_total": sum(s['duration'] for s in scenes_with_prompts),
                "duracion_promedio": sum(s['duration'] for s in scenes_with_prompts) / len(scenes_with_prompts)
            },
            "escenas": scenes_with_prompts
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Resultados guardados en: {filename}")
            
        except Exception as e:
            print(f"⚠️  Error guardando archivo: {e}")
    
    def ejecutar_flujo_completo(self):
        try:
            # Mostrar banner
            self.mostrar_banner()
            
            # Paso 1: Obtener script
            script = self.solicitar_script()
            
            # Paso 2: Simular transcripción
            transcription_segments = self.simular_transcripcion(script)
            
            # Paso 3: Extraer contexto histórico
            contexto_historico = self.extraer_contexto_historico(script)
            
            # Paso 4: Generar escenas narrativas
            scenes = self.generar_escenas_narrativas(transcription_segments)
            
            # Paso 5: Generar prompts históricos
            scenes_with_prompts = self.generar_prompts_historicos(scenes, contexto_historico)
            
            # Paso 6: Mostrar resultados
            self.mostrar_resultados_finales(scenes_with_prompts)
            
            # Paso 7: Guardar resultados
            self.guardar_resultados(scenes_with_prompts, contexto_historico)
            
            print("\n🎉 ¡Generación completada exitosamente!")
            
        except KeyboardInterrupt:
            print("\n\n❌ Proceso cancelado por el usuario")
        except Exception as e:
            print(f"\n❌ Error durante la ejecución: {e}")
            import traceback
            traceback.print_exc()

def main():
    generador = GeneradorInteractivo()
    generador.ejecutar_flujo_completo()

if __name__ == "__main__":
    main() 